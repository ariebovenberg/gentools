"""itertools for generators with send() and throw()"""
import inspect
import typing as t
from functools import partial, reduce
from operator import attrgetter, itemgetter

from .types import (Generable, GeneratorCallable, ReusableGenerator, T_return,
                    T_send, T_yield)
from .utils import compose

__all__ = [
    'nest',
    'imap_yield',
    'imap_send',
    'imap_return',
    'nested',
    'yieldmapped',
    'sendmapped',
    'returnmapped',
    'reusable',
    'sendreturn',
    'oneyield',
]

T_mapped = t.TypeVar('T_mapped')


def reusable(func: GeneratorCallable[T_yield, T_send, T_return]) -> t.Type[
        ReusableGenerator[T_yield, T_send, T_return]]:
    """create a reusable class from a generator function

    Parameters
    ----------
    func
        the function to wrap

    Note
    ----
    the callable must have an inspectable signature
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


# TODO: type annotations, docstring
def imap_return(func, gen):
    gen = iter(gen)
    assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    return func((yield from gen))


# TODO: type annotations, docstring
def nest(gen, pipe):
    gen = iter(gen)
    assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    item = next(gen)
    while True:
        sent = yield from pipe(item)
        item = gen.send(sent)


# TODO: docs, types
class nested:
    def __init__(self, *genfuncs):
        self._genfuncs = genfuncs

    def __call__(self, func):
        return compose(partial(reduce, nest, self._genfuncs), func)


# TODO: docs, types
class yieldmapped:
    def __init__(self, *funcs):
        self._mapper = compose(*funcs)

    def __call__(self, func):
        return compose(partial(imap_yield, self._mapper), func)


# TODO: docs, types
class sendmapped:
    def __init__(self, *funcs):
        self._mapper = compose(*funcs)

    def __call__(self, func):
        return compose(partial(imap_send, self._mapper), func)


# TODO: docs, types
class returnmapped:
    def __init__(self, *funcs):
        self._mapper = compose(*funcs)

    def __call__(self, func):
        return compose(partial(imap_return, self._mapper), func)


# TODO: type annotations
class oneyield:
    """decorate a function to turn it into a basic generator"""
    def __init__(self, func: t.Callable):
        self.__wrapped__ = func

    def __call__(self, *args, **kwargs):
        return (yield self.__wrapped__(*args, **kwargs))
