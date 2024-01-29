"""base classes and interfaces"""

import abc
import typing as t
from itertools import starmap
from types import GeneratorType

from .utils import CallableAsMethod

__all__ = [
    "Generable",
    "GeneratorCallable",
    "ReusableGenerator",
]

T_yield = t.TypeVar("T_yield")
T_send = t.TypeVar("T_send")
T_return = t.TypeVar("T_return")


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


class ReusableGenerator(
    Generable[T_yield, T_send, T_return], metaclass=ReusableGeneratorMeta
):
    """base class for reusable generator functions

    Warning
    -------
    * Do not subclass directly. Subclasses are created with
      the :func:`~gentools.core.reusable` decorator.
    """

    def __init__(self, *args, **kwargs):
        self._bound_args = self.__signature__.bind(*args, **kwargs)
        self._bound_args.apply_defaults()

    def __iter__(self):
        return self.__wrapped__(
            *self._bound_args.args, **self._bound_args.kwargs
        )

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._bound_args.arguments == other._bound_args.arguments
        return NotImplemented

    def __repr__(self):
        fields = starmap("{}={!r}".format, self._bound_args.arguments.items())
        return "{}({})".format(self.__class__.__qualname__, ", ".join(fields))

    def __hash__(self):
        return hash(
            (self._bound_args.args, tuple(self._bound_args.kwargs.items()))
        )

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
        copied = self.__signature__.bind(
            *self._bound_args.args, **self._bound_args.kwargs
        )
        copied.arguments.update(**kwargs)
        return self.__class__(*copied.args, **copied.kwargs)
