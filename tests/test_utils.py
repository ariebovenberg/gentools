from inspect import signature
from operator import attrgetter

from gentools import utils


def test_identity():
    obj = object()
    assert utils.identity(obj) is obj


class TestCompose:
    def test_part_of_main_api(self):
        from gentools import compose

        assert compose is utils.compose

    def test_empty(self):
        obj = object()
        func = utils.compose()
        assert func(obj) is obj
        assert isinstance(func.funcs, tuple)
        assert func.funcs == ()
        assert signature(func) == signature(utils.identity)

    def test_called_as_method(self):
        class Foo(object):
            def __init__(self, value):
                self.value = value

            func = utils.compose(lambda x: x + 1, attrgetter("value"))

        f = Foo(4)
        assert Foo.func(f) == 5
        assert f.func() == 5

    def test_one_func_with_multiple_args(self):
        func = utils.compose(int)
        assert func("10", base=5) == 5
        assert isinstance(func.funcs, tuple)
        assert func.funcs == (int,)

    def test_multiple_funcs(self):
        func = utils.compose(str, lambda x: x + 1, int)
        assert isinstance(func.funcs, tuple)
        assert func("30", base=5) == "16"

    def test_equality(self):
        func = utils.compose(int, str)
        other = utils.compose(int, str)
        assert func == other
        assert not func != other
        assert hash(func) == hash(other)

        assert not func == utils.compose(int)
        assert func != utils.compose(int)

        assert func != object()
        assert not func == object()
