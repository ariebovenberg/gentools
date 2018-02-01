import sys
import inspect
import typing as t
from functools import partial, reduce
from operator import attrgetter, itemgetter

from .types import (Generable, GeneratorCallable, ReusableGenerator, T_return,
                    T_send, T_yield)
from .utils import compose

try:
    from inspect import signature
except ImportError:
    from funcsigs import signature

__all__ = [
    'reusable',
    'oneyield',
    'return_',

    'imap_yield',
    'imap_send',
    'imap_return',
    'irelay',

    'relay',
    'map_yield',
    'map_send',
    'map_return',
    'sendreturn',

    'compose',
]

T_mapped = t.TypeVar('T_mapped')
T_yield_new = t.TypeVar('T_yield_new')
T_send_new = t.TypeVar('T_yield_new')


def return_(value):
    raise StopIteration(value)


def reusable(func):
    """create a reusable class from a generator function

    Parameters
    ----------
    func: GeneratorCallable[T_yield, T_send, T_return]
        the function to wrap

    Note
    ----
    * the callable must have an inspectable signature
    * If bound to a class, the new reusable generator is callable as a method.
      To opt out of this, add a :func:`staticmethod` decorator above.

    """
    sig = signature(func)
    origin = func
    while hasattr(origin, '__wrapped__'):
        origin = origin.__wrapped__
    return type(
        origin.__name__,
        (ReusableGenerator, ),
        dict([
            ('__doc__',       origin.__doc__),
            ('__module__',    origin.__module__),
            # ('__qualname__',  origin.__qualname__),
            ('__signature__', sig),
            ('__wrapped__',   staticmethod(func)),
        ] + [
            (name, property(compose(itemgetter(name),
                                    attrgetter('_bound_args.arguments'))))
            for name in sig.parameters
        ]))


class oneyield(GeneratorCallable[T_yield, T_send, T_send]):
    """decorate a function to turn it into a basic generator"""
    def __init__(self, func):
        self.__wrapped__ = func

    def __call__(self, *args, **kwargs):
        return_((yield self.__wrapped__(*args, **kwargs)))


def sendreturn(gen, value):
    """send an item into a generator expecting a final return value

    Parameters
    ----------
    gen: t.Generator[T_yield, T_send, T_return]
        the generator to send the value to
    value: T_send
        the value to send

    Raises
    ------
    RuntimeError
        if the generator did not return as expected

    Returns
    -------
    T_return
    """
    try:
        gen.send(value)
    except StopIteration as e:
        return e.args[0]
    else:
        raise RuntimeError('generator did not return as expected')


def imap_yield(func, gen):
    """apply a function to all ``yield`` values of a generator

    Parameters
    ----------
    func: t.Callable[[T_yield], T_mapped],
        the function to apply
    gen: Generable[T_yield, T_send, T_return]
        the generator iterable.

    Returns
    -------
    t.Generator[T_mapped, T_send, T_return]
    """
    gen = iter(gen)
    # assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    item = next(gen)
    while True:
        item = gen.send((yield func(item)))


def imap_send(func, gen):
    """apply a function to all ``send`` values of a generator

    Parameters
    ----------
    func: t.Callable[[T_send], T_mapped],
        the function to apply
    gen: Generable[T_yield, T_mapped, T_return]
        the generator iterable.

    Returns
    -------
    t.Generator[T_yield, T_send, T_return]
    """
    gen = iter(gen)
    # assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    item = next(gen)
    while True:
        item = gen.send(func((yield item)))


def imap_return(func, gen):
    """apply a function to the ``return`` value of a generator

    Parameters
    ----------
    func: t.Callable[[T_return], T_mapped],
        the function to apply
    gen: Generable[T_yield, T_send, T_return]
        the generator iterable.

    Returns
    -------
    t.Generator[T_yield, T_send, T_mapped]
    """
    gen = iter(gen)
    # assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    # this is basically:
    #     return func((yield from gen))
    # but without yield from
    # (and very rudimentary)
    try:
        r = yield next(gen)
    except StopIteration as e:
        return_(func(e.args[0]))
    while True:
        try:
            r = yield gen.send(r)
        except StopIteration as e:
            return_(func(e.args[0]))


_Relay = t.Callable[[T_yield], t.Generator[T_yield_new,
                                           T_send_new,
                                           T_send]]


def irelay(gen, thru):
    """create a new generator by relaying yield/send interactions
    through another generator

    Parameters
    ----------
    gen: Generable[T_yield, T_send, T_return],
        the original generator
    thru: _Relay
        the piping generator callable

    Returns
    -------
    t.Generator[T_yield_new, T_send_new, T_return]
    """
    gen = iter(gen)
    # assert inspect.getgeneratorstate(gen) == 'GEN_CREATED'
    item = next(gen)
    while True:
        # the following is basically:
        #     sent = yield from thru(item)
        # but without yield from
        _i = iter(thru(item))
        try:
            _y = next(_i)
        except StopIteration as _e:
            _r = _e.args[0]
        else:
            while 1:
                try:
                    _s = yield _y
                except GeneratorExit as _e:
                    try:
                        _m = _i.close
                    except AttributeError:
                        pass
                    else:
                        _m()
                    raise _e
                except BaseException as _e:
                    _x = sys.exc_info()
                    try:
                        _m = _i.throw
                    except AttributeError:
                        raise _e
                    else:
                        try:
                            _y = _m(*_x)
                        except StopIteration as _e:
                            _r = _e.args[0]
                            break
                else:
                    try:
                        if _s is None:
                            _y = next(_i)
                        else:
                            _y = _i.send(_s)
                    except StopIteration as _e:
                        _r = _e.args[0]
                        break
        sent = _r
        # --- end yield from ---
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


class relay:
    """decorate a generator callable to relay yield/send values
    through other generators

    See also
    --------
    :func:`~gentools.core.irelay`
    """
    def __init__(self, *genfuncs):
        self._genfuncs = genfuncs

    def __call__(self, func):
        return compose(partial(reduce, irelay, self._genfuncs), func)
