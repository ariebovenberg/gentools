"""base classes and interfaces"""
import abc
import inspect
import sys
import typing as t
from collections import OrderedDict
from itertools import starmap

from .utils import PY2, CallableAsMethod

__all__ = [
    'Generable',
    'GeneratorCallable',
    'ReusableGenerator',
]

T_yield = t.TypeVar('T_yield')
T_send = t.TypeVar('T_send')
T_return = t.TypeVar('T_return')

if PY2:  # pragma: no cover
    from funcsigs import _empty, _VAR_POSITIONAL, _VAR_KEYWORD

    def __():
        yield
    GeneratorType = type(__())
    del __
else:
    from inspect import _empty, _VAR_POSITIONAL, _VAR_KEYWORD
    from types import GeneratorType


# adapted from BoundArguments.apply_defaults from python3.5
if sys.version_info < (3, 5):  # pragma: no cover
    def _apply_defaults(bound_sig):
        arguments = bound_sig.arguments
        new_arguments = []
        for name, param in bound_sig._signature.parameters.items():
            try:
                new_arguments.append((name, arguments[name]))
            except KeyError:
                if param.default is not _empty:
                    val = param.default
                elif param.kind is _VAR_POSITIONAL:
                    val = ()
                elif param.kind is _VAR_KEYWORD:
                    val = {}
                else:
                    # This BoundArguments was likely produced by
                    # Signature.bind_partial().
                    continue
                new_arguments.append((name, val))
        bound_sig.arguments = OrderedDict(new_arguments)
else:  # pragma: no cover
    _apply_defaults = inspect.BoundArguments.apply_defaults


class Generable(t.Generic[T_yield, T_send, T_return], t.Iterable[T_yield]):
    """ABC for generable objects.
    Any object where :meth:`~object.__iter__`
    returns a generator implements it.
    """

    @abc.abstractmethod
    def __iter__(self):
        """

        Returns
        -------
        ~typing.Generator[T_yield, T_send, T_return]
            the generator iterator
        """
        raise NotImplementedError()


Generable.register(GeneratorType)


class GeneratorCallable(t.Generic[T_yield, T_send, T_return]):
    """ABC for callables which return a generator.
    Note that :term:`generator functions <generator>` already implement this.
    """
    def __call__(self, *args, **kwargs):
        """

        Returns
        -------
        ~typing.Generator[T_yield, T_send, T_return]
            the resulting generator
        """
        raise NotImplementedError()


class ReusableGeneratorMeta(CallableAsMethod, type(Generable)):
    pass


# from ``six.add_metaclass``
def _add_metaclass(metaclass):  # pragma: no cover
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


@_add_metaclass(ReusableGeneratorMeta)
class ReusableGenerator(Generable[T_yield, T_send, T_return]):
    """base class for reusable generator functions

    Warning
    -------
    * Do not subclass directly. Subclasses are created with
      the :func:`~gentools.core.reusable` decorator.
    * Instances if this class are only picklable on python 3.5+
    """
    def __init__(self, *args, **kwargs):
        self._bound_args = self.__signature__.bind(*args, **kwargs)
        _apply_defaults(self._bound_args)

    def __iter__(self):
        return self.__wrapped__(*self._bound_args.args,
                                **self._bound_args.kwargs)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._bound_args.arguments == other._bound_args.arguments
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self == other
        return NotImplemented

    def __repr__(self):
        fields = starmap('{}={!r}'.format, self._bound_args.arguments.items())
        return '{}({})'.format(self.__class__.__qualname__, ', '.join(fields))

    def __hash__(self):
        return hash((self._bound_args.args,
                     tuple(self._bound_args.kwargs.items())))

    def replace(self, **kwargs):
        """create a new instance with certain fields replaced

        Parameters
        ----------
        **kwargs
            fields to replace

        Returns
        -------
        ReusableGenerator
            a copy with replaced fields
        """
        copied = self.__signature__.bind(*self._bound_args.args,
                                         **self._bound_args.kwargs)
        copied.arguments.update(**kwargs)
        return self.__class__(*copied.args, **copied.kwargs)
