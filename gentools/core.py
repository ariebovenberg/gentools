import inspect
import typing as t
from functools import partial, reduce
from operator import attrgetter, itemgetter

from .types import (Generable, GeneratorCallable, ReusableGenerator, T_return,
                    T_send, T_yield)
from .utils import compose

__all__ = [
    'reusable',
    'oneyield',

    'imap_yield',
    'imap_send',
    'imap_return',
    'ipipe',

    'pipe',
    'map_yield',
    'map_send',
    'map_return',
    'sendreturn',
]

T_mapped = t.TypeVar('T_mapped')
T_yield_new = t.TypeVar('T_yield_new')
T_send_new = t.TypeVar('T_yield_new')


def reusable(func: GeneratorCallable[T_yield, T_send, T_return]) -> t.Type[
        ReusableGenerator[T_yield, T_send, T_return]]:
    """create a reusable class from a generator function

    Parameters
    ----------
    func
        the function to wrap

    Note
    ----
    * the callable must have an inspectable signature
    * If bound to a class, the new reusable generator is callable as a method.
      To opt out of this, add a :func:`staticmethod` decorator above.

    """
    sig = inspect.signature(func)
    origin = inspect.unwrap(func)
    return type(
        origin.__name__,
        (ReusableGenerator, ),
        dict([
            ('__doc__',       origin.__doc__),
            ('__module__',    origin.__module__),
            ('__qualname__',  origin.__qualname__),
            ('__signature__', sig),
            ('__wrapped__',   staticmethod(func)),
        ] + [
            (name, property(compose(itemgetter(name),
                                    attrgetter('_bound_args.arguments'))))
            for name in sig.parameters
        ]))


class oneyield(GeneratorCallable[T_yield, T_send, T_send]):
    """decorate a function to turn it into a basic generator"""
    def __init__(self, func: t.Callable[..., T_yield]):
        self.__wrapped__ = func

    def __call__(self, *args, **kwargs):
        return (yield self.__wrapped__(*args, **kwargs))


def sendreturn(gen: t.Generator[T_yield, T_send, T_return],
               value: T_send) -> T_return:
    """send an item into a generator expecting a final return value

    Parameters
    ----------
    gen
        the generator to send the value to
    value
        the value to send

    Raises
    ------
    RuntimeError
        if the generator did not return as expected
    """
    try:
        gen.send(value)
    except StopIteration as e:
        return e.value
    else:
        raise RuntimeError('generator did not return as expected')


def imap_yield(func: t.Callable[[T_yield], T_mapped],
               gen: Generable[T_yield, T_send, T_return]) -> (
                   t.Generator[T_mapped, T_send, T_return]):
    """apply a function to all ``yield`` values of a generator

    Parameters
    ----------
    func
        the function to apply
    gen
        the generator iterable.
    """
    gen = iter(gen)
    assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    item = next(gen)
    while True:
        item = gen.send((yield func(item)))


def imap_send(func: t.Callable[[T_send], T_mapped],
              gen: Generable[T_yield, T_mapped, T_return]) -> (
                  t.Generator[T_yield, T_send, T_return]):
    """apply a function to all ``send`` values of a generator

    Parameters
    ----------
    func
        the function to apply
    gen
        the generator iterable.
    """
    gen = iter(gen)
    assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    item = next(gen)
    while True:
        item = gen.send(func((yield item)))


def imap_return(func: t.Callable[[T_return], T_mapped],
                gen: Generable[T_yield, T_send, T_return]) -> (
                    t.Generator[T_yield, T_send, T_mapped]):
    """apply a function to the ``return`` value of a generator

    Parameters
    ----------
    func
        the function to apply
    gen
        the generator iterable.
    """
    gen = iter(gen)
    assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    return func((yield from gen))


_Pipe = t.Callable[[T_yield], t.Generator[T_yield_new,
                                          T_send_new,
                                          T_send]]


def ipipe(gen: Generable[T_yield, T_send, T_return],
          thru: _Pipe) -> t.Generator[T_yield_new, T_send_new, T_return]:
    """create a new generator by piping yield/send through another generator

    Parameters
    ----------
    gen
        the original generator
    thru
        the piping generator callable
    """
    gen = iter(gen)
    assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    item = next(gen)
    while True:
        sent = yield from thru(item)
        item = gen.send(sent)


class map_yield:
    """decorate a generator callable to apply function to
    each ``yield`` value

    See also
    --------
    :func:`~gentools.core.imap_yield`
    """
    def __init__(self, *funcs):
        self._mapper = compose(*funcs)

    def __call__(self, func):
        return compose(partial(imap_yield, self._mapper), func)


class map_send:
    """decorate a generator callable to apply functions to
    each ``send`` value

    See also
    --------
    :func:`~gentools.core.imap_send`
    """
    def __init__(self, *funcs):
        self._mapper = compose(*funcs)

    def __call__(self, func):
        return compose(partial(imap_send, self._mapper), func)


class map_return:
    """decorate a generator callable to apply functions to
    the ``return`` value

    See also
    --------
    :func:`~gentools.core.imap_return`
    """
    def __init__(self, *funcs):
        self._mapper = compose(*funcs)

    def __call__(self, func):
        return compose(partial(imap_return, self._mapper), func)


class pipe:
    """decorate a generator callable to pipe yield/send values
    through other generators

    See also
    --------
    :func:`~gentools.core.ipipe`
    """
    def __init__(self, *genfuncs):
        self._genfuncs = genfuncs

    def __call__(self, func):
        return compose(partial(reduce, ipipe, self._genfuncs), func)
