"""Miscellaneous tools, boilerplate, and shortcuts"""
import sys
from functools import partial

PY2 = sys.version_info < (3, )


def identity(obj):
    return obj


class CallableAsMethod(object):
    """mixin for callables to be callable as methods when bound to a class"""
    def __get__(self, obj, objtype=None):
        return self if obj is None else partial(self, obj)


class compose(CallableAsMethod):
    """compose a function from a chain of functions

    Parameters
    ----------
    *funcs
        callables to compose

    Note
    ----
    * if given no functions, acts as an identity function
    """
    def __init__(self, *funcs):
        self.funcs = funcs
        self.__wrapped__ = funcs[-1] if funcs else identity

    def __hash__(self):
        return hash(self.funcs)

    def __eq__(self, other):
        if isinstance(other, compose):
            return self.funcs == other.funcs
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, compose):
            return self.funcs != other.funcs
        return NotImplemented

    def __call__(self, *args, **kwargs):
        if not self.funcs:
            return identity(*args, **kwargs)
        tail, head = self.funcs[:-1], self.funcs[-1]
        value = head(*args, **kwargs)
        for func in reversed(tail):
            value = func(value)
        return value
