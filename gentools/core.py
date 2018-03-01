import sys
from functools import partial, reduce
from operator import attrgetter, itemgetter

from .types import (GeneratorCallable, GeneratorProxy, GeneratorReturn,
                    ReusableGenerator, T_send, T_yield)
from .utils import PY2, compose

__all__ = [
    'reusable',
    'oneyield',
    'sendreturn',

    'imap_yield',
    'imap_send',
    'imap_return',
    'irelay',

    'relay',
    'map_yield',
    'map_send',
    'map_return',

    'compose',

    'py2_compatible',
    'return_',
    'yield_from',
]


if PY2:  # pragma: no cover
    from funcsigs import signature
else:
    from inspect import signature


def _is_just_started(gen):
    return gen.gi_frame.f_lasti == -1


def py2_compatible(func):
    """Decorate a generator function to make it Python 2/3 compatible.
    Use together with :func:`return_`.

    Example
    -------

    >>> @py2_compatible
    ... def my_max(value):
    ...     while value < 100:
    ...         newvalue = yield value
    ...         if newvalue > value:
    ...             value = newvalue
    ...     return_(value)

    is equivalent to:

    >>> def my_max(value):
    ...     while value < 100:
    ...         newvalue = yield value
    ...         if newvalue > value:
    ...             value = newvalue
    ...     return value

    Note
    ----
    This is necessary because PEP479 makes it impossible to replace
    ``return`` with ``raise StopIteration`` in newer python 3 versions.

    Warning
    -------
    Although the wrapped generator acts like a generator,
    it is not an strict generator instance.
    For most purposes (e.g. ``yield from``) it works fine,
    but :func:`~inspect.isgenerator` will return ``False``.
    """
    return compose(GeneratorProxy, func)


def return_(value):
    """Python 2/3 compatible way to return a value from a generator

    Use only with the :func:`py2_compatible` decorator"""
    raise GeneratorReturn(value)


def reusable(func):
    """Create a reusable class from a generator function

    Parameters
    ----------
    func: GeneratorCallable[T_yield, T_send, T_return]
        the function to wrap

    Note
    ----
    * the callable must have an inspectable signature
    * If bound to a class, the new reusable generator is callable as a method.
      To opt out of this, add a :func:`staticmethod` decorator above
      this decorator.

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
            ('__signature__', sig),
            ('__wrapped__',   staticmethod(func)),
        ] + [
            (name, property(compose(itemgetter(name),
                                    attrgetter('_bound_args.arguments'))))
            for name in sig.parameters
        ] + ([
            ('__qualname__',  origin.__qualname__),
        ] if sys.version_info > (3, ) else [])))


class oneyield(GeneratorCallable[T_yield, T_send, T_send]):
    """Decorate a function to turn it into a basic generator

    The resulting generator yields the function's return value once,
    and then returns the value it is sent (with ``send()``).
    """
    def __init__(self, func):
        self.__wrapped__ = func

    @py2_compatible
    def __call__(self, *args, **kwargs):
        return_((yield self.__wrapped__(*args, **kwargs)))


def stopiteration_value(exc):
    try:
        return exc.args[0]
    except IndexError:
        return


class yield_from(object):

    def __init__(self, gen):
        self._finished = False
        self._gen = iter(gen)
        try:
            self._next = next(self._gen)
        except StopIteration as e:
            self._result = stopiteration_value(e)
            self._finished = True

    def __iter__(self):
        return self

    def __next__(self):
        if self._finished:
            raise StopIteration()
        self._sent = None
        return self._next

    if PY2:  # pragma: no cover
        next = __next__

    def send(self, value):
        self._sent = value

    def __enter__(self):
        return self

    def __exit__(self, exc_cls, exc, tb):
        if exc_cls is None:
            try:
                if self._sent is None:
                    self._next = next(self._gen)
                else:
                    self._next = self._gen.send(self._sent)
            except StopIteration as _e:
                self._finished = True
                self._result = stopiteration_value(_e)
        elif issubclass(exc_cls, GeneratorExit):
            try:
                close = self._gen.close
            except AttributeError:
                pass
            else:
                close()
            raise exc
        else:
            _x = (exc_cls, exc, tb)
            try:
                throw = self._gen.throw
            except AttributeError:
                raise exc
            else:
                try:
                    self._next = throw(*_x)
                except StopIteration as _e:
                    self._finished = True
                    self._result = stopiteration_value(_e)
                return True


def sendreturn(gen, value):
    """Send an item into a generator expecting a final return value

    Parameters
    ----------
    gen: ~typing.Generator[T_yield, T_send, T_return]
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
        the generator's return value
    """
    try:
        gen.send(value)
    except StopIteration as e:
        return stopiteration_value(e)
    else:
        raise RuntimeError('generator did not return as expected')


def imap_yield(func, gen):
    """Apply a function to all ``yield`` values of a generator

    Parameters
    ----------
    func: ~typing.Callable[[T_yield], T_mapped]
        the function to apply
    gen: Generable[T_yield, T_send, T_return]
        the generator iterable.

    Returns
    -------
    ~typing.Generator[T_mapped, T_send, T_return]
        the mapped generator
    """
    gen = iter(gen)
    assert _is_just_started(gen)
    item = next(gen)
    while True:
        item = gen.send((yield func(item)))


def imap_send(func, gen):
    """Apply a function to all ``send`` values of a generator

    Parameters
    ----------
    func: ~typing.Callable[[T_send], T_mapped]
        the function to apply
    gen: Generable[T_yield, T_mapped, T_return]
        the generator iterable.

    Returns
    -------
    ~typing.Generator[T_yield, T_send, T_return]
        the mapped generator
    """
    gen = iter(gen)
    assert _is_just_started(gen)
    item = next(gen)
    while True:
        item = gen.send(func((yield item)))


@py2_compatible
def imap_return(func, gen):
    """Apply a function to the ``return`` value of a generator

    Parameters
    ----------
    func: ~typing.Callable[[T_return], T_mapped]
        the function to apply
    gen: Generable[T_yield, T_send, T_return]
        the generator iterable.

    Returns
    -------
    ~typing.Generator[T_yield, T_send, T_mapped]
    """
    gen = iter(gen)
    assert _is_just_started(gen)
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


def irelay(gen, thru):
    """Create a new generator by relaying yield/send interactions
    through another generator

    Parameters
    ----------
    gen: Generable[T_yield, T_send, T_return]
        the original generator
    thru: ~typing.Callable[[T_yield], ~typing.Generator]
        the generator callable through which each interaction is relayed

    Returns
    -------
    ~typing.Generator
        the relayed generator
    """
    gen = iter(gen)
    assert _is_just_started(gen)
    item = next(gen)
    while True:
        # the following is basically:
        #     sent = yield from thru(item)
        # but without yield from
        _i = iter(thru(item))
        try:
            _y = next(_i)
        except StopIteration as _e:  # pragma: no cover
            _r = _e.args[0]
        else:  # pragma: no cover
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
    """Decorate a generator callable to apply a function to
    each ``yield`` value

    Example
    -------

    >>> @map_yield('the current max is: {}'.format)
    ... def my_max(value):
    ...     while value < 100:
    ...         newvalue = yield value
    ...         if newvalue > value:
    ...             value = newvalue
    ...     return value
    ...
    >>> gen = my_max(5)
    >>> next(gen)
    'the current max is: 5'
    >>> gen.send(11)
    'the current max is: 11'
    >>> gen.send(104)
    StopIteration(104)

    See also
    --------
    :func:`~gentools.core.imap_yield`
    """
    def __init__(self, *funcs):
        self._mapper = compose(*funcs)

    def __call__(self, func):
        return compose(partial(imap_yield, self._mapper), func)


class map_send:
    """Decorate a generator callable to apply functions to
    each ``send`` value

    Example
    -------

    >>> @map_send(int)
    ... def my_max(value):
    ...     while value < 100:
    ...         newvalue = yield value
    ...         if newvalue > value:
    ...             value = newvalue
    ...     return value
    ...
    >>> gen = my_max(5)
    >>> next(gen)
    5
    >>> gen.send(11.3)
    11
    >>> gen.send('104')
    104

    See also
    --------
    :func:`~gentools.core.imap_send`
    """
    def __init__(self, *funcs):
        self._mapper = compose(*funcs)

    def __call__(self, func):
        return compose(partial(imap_send, self._mapper), func)


class map_return:
    """Decorate a generator callable to apply functions to
    the ``return`` value

    Example
    -------

    >>> @map_return('final value: {}'.format)
    ... def my_max(value):
    ...     while value < 100:
    ...         newvalue = yield value
    ...         if newvalue > value:
    ...             value = newvalue
    ...     return value
    ...
    >>> gen = my_max(5)
    >>> next(gen)
    5
    >>> gen.send(11.3)
    11.3
    >>> gen.send(104)
    StopIteration('final value: 104')

    See also
    --------
    :func:`~gentools.core.imap_return`
    """
    def __init__(self, *funcs):
        self._mapper = compose(*funcs)

    def __call__(self, func):
        return compose(partial(imap_return, self._mapper), func)


class relay:
    """Decorate a generator callable to relay yield/send values
    through another generator

    Example
    -------

    >>> def try_until_positive(outvalue):
    ...     value = yield outvalue
    ...     while value < 0:
    ...         value = yield 'not positive, try again'
    ...     return value
    ...
    >>> @relay(try_until_positive)
    ... def my_max(value):
    ...     while value < 100:
    ...         newvalue = yield value
    ...         if newvalue > value:
    ...             value = newvalue
    ...     return value
    ...
    >>> gen = my_max(5)
    >>> next(gen)
    5
    >>> gen.send(-4)
    'not positive, try again'
    >>> gen.send(-1)
    'not positive, try again'
    >>> gen.send(8)
    8
    >>> gen.send(104)
    StopIteration(104)

    See also
    --------
    :func:`~gentools.core.irelay`
    """
    def __init__(self, *genfuncs):
        self._genfuncs = genfuncs

    def __call__(self, func):
        return compose(partial(reduce, irelay, self._genfuncs), func)
