import inspect
import pickle
import sys
import types
from functools import reduce

import pytest

import gentools
from gentools.utils import compose


def try_until_positive(req):
    """an example Pipe"""
    response = yield req
    while response < 0:
        response = yield 'NOT POSITIVE!'
    return response


def try_until_even(req):
    """an example Pipe"""
    response = yield req
    while response % 2:
        response = yield 'NOT EVEN!'
    return response


def mymax(val):
    """an example generator function"""
    while val < 100:
        sent = yield val
        if sent > val:
            val = sent
    return val * 3


class MyMax:
    """an example generator iterable"""

    def __init__(self, start):
        self.start = start

    def __iter__(self):
        val = self.start
        while val < 100:
            sent = yield val
            if sent > val:
                val = sent
        return val * 3


def emptygen():
    if False:
        yield
    return 99


@gentools.reusable
def mygen(a: int, *, foo):
    yield a
    yield foo


class TestReusable:

    @pytest.mark.skipif(sys.version_info < (3, 5),
                        reason='requires python 3.5+')
    def test_picklable(self):
        gen = mygen(4, foo=5)
        assert pickle.loads(pickle.dumps(gen)) == gen

    def test_callable_as_method(self):

        class Parent:
            def __init__(self, foo):
                self.foo = foo

            @gentools.reusable
            def mygen(self, value):
                yield self.foo
                yield value

            # opt out with staticmethod
            @staticmethod
            @gentools.reusable
            def staticgen(foo, bar):
                yield foo
                yield bar

        p = Parent(4)

        assert list(Parent.mygen(p, 8)) == [4, 8]
        gen = p.mygen(9)
        assert list(gen) == list(gen) == [4, 9]
        assert p.mygen.__self__ is p

        assert list(Parent.staticgen(3, 9)) == [3, 9]
        assert list(p.staticgen(3, 9)) == [3, 9]

    def test_example(self):

        class mywrapper:
            def __init__(self, func):
                self.__wrapped__ = func
                self.__signature__ = inspect.signature(func).replace(
                    return_annotation=str)

            def __call__(self, *args, **kwargs):
                inner = self.__wrapped__(*args, **kwargs)
                yield str(next(inner))

        @gentools.reusable
        @mywrapper  # dummy to test combining with other decorators
        def gentype(a: int, b: float, *cs, d, e=5, **fs):
            """my docstring"""
            return (yield sum([a, b, sum(cs), d, e, a]))

        gentype.__qualname__ = 'mymodule.gentype'

        assert issubclass(gentype, gentools.Generable)
        assert isinstance(inspect.unwrap, types.FunctionType)
        gentype.__name__ == 'myfunc'
        gentype.__doc__ == 'my docstring'
        gentype.__module__ == 'test_core'
        gen = gentype(4, 5, d=6, foo=10)

        assert {'a', 'b', 'cs', 'd', 'e', 'fs'} < set(dir(gen))
        assert gen.a == 4
        assert gen.b == 5
        assert gen.cs == ()
        assert gen.e == 5
        assert gen.fs == {'foo': 10}

        assert next(iter(gen)) == '24'
        assert next(iter(gen)) == '24'  # reusable

        othergen = gentype(4, b=5, d=6, e=5, foo=10)
        assert gen == othergen
        assert not gen != othergen
        assert hash(gen) == hash(othergen)

        assert repr(gen) == ("mymodule.gentype("
                             "a=4, b=5, cs=(), d=6, e=5, fs={'foo': 10})")

        assert not gen == gentype(3, 4, 5, d=10)
        assert gen != gentype(1, 2, d=7)

        assert not gen == object()
        assert gen != object()

        changed = gen.replace(b=9)
        assert changed == gentype(4, 9, d=6, foo=10)


class TestSendReturn:

    def test_ok(self):

        def mygen(n):
            while n != 0:
                n = yield n + 1
            return 'foo'

        gen = mygen(4)
        assert next(gen) == 5
        assert gentools.sendreturn(gen, 0) == 'foo'

    def test_no_return(self):

        def mygen(n):
            while n != 0:
                n = yield n + 1
            return 'foo'

        gen = mygen(4)
        assert next(gen) == 5
        with pytest.raises(RuntimeError, match='did not return'):
            gentools.sendreturn(gen, 1)


class TestIMapYield:

    def test_empty(self):
        try:
            next(gentools.imap_yield(str, emptygen()))
        except StopIteration as e:
            assert e.value == 99

    def test_simple(self):
        mapped = gentools.imap_yield(str, mymax(4))

        assert next(mapped) == '4'
        assert mapped.send(7) == '7'
        assert mapped.send(3) == '7'
        assert gentools.sendreturn(mapped, 103) == 309


class TestIMapSend:

    def test_empty(self):
        try:
            next(gentools.imap_send(int, emptygen()))
        except StopIteration as e:
            assert e.value == 99

    def test_simple(self):
        mapped = gentools.imap_send(int, mymax(4))

        assert next(mapped) == 4
        assert mapped.send('7') == 7
        assert mapped.send(7.3) == 7
        assert gentools.sendreturn(mapped, '104') == 312

    def test_any_iterable(self):
        mapped = gentools.imap_send(int, MyMax(4))

        assert next(mapped) == 4
        assert mapped.send('7') == 7
        assert mapped.send(7.3) == 7
        assert gentools.sendreturn(mapped, '104') == 312


class TestIMapReturn:

    def test_empty(self):
        try:
            next(gentools.imap_return(str, emptygen()))
        except StopIteration as e:
            assert e.value == '99'

    def test_simple(self):
        mapped = gentools.imap_return(str, mymax(4))

        assert next(mapped) == 4
        assert mapped.send(7) == 7
        assert mapped.send(4) == 7
        assert gentools.sendreturn(mapped, 104) == '312'

    def test_any_iterable(self):
        mapped = gentools.imap_return(str, MyMax(4))

        assert next(mapped) == 4
        assert mapped.send(7) == 7
        assert mapped.send(4) == 7
        assert gentools.sendreturn(mapped, 104) == '312'


class TestIPipe:

    def test_empty(self):
        try:
            next(gentools.ipipe(emptygen(), try_until_positive))
        except StopIteration as e:
            assert e.value == 99

    def test_simple(self):
        piped = gentools.ipipe(mymax(4), try_until_positive)

        assert next(piped) == 4
        assert piped.send(7) == 7
        assert piped.send(6) == 7
        assert piped.send(-1) == 'NOT POSITIVE!'
        assert piped.send(-4) == 'NOT POSITIVE!'
        assert piped.send(0) == 7
        assert gentools.sendreturn(piped, 102) == 306

    def test_any_iterable(self):
        piped = gentools.ipipe(MyMax(4), try_until_positive)

        assert next(piped) == 4
        assert piped.send(7) == 7
        assert piped.send(6) == 7
        assert piped.send(-1) == 'NOT POSITIVE!'
        assert piped.send(-4) == 'NOT POSITIVE!'
        assert piped.send(0) == 7
        assert gentools.sendreturn(piped, 102) == 306

    def test_accumulate(self):

        gen = reduce(gentools.ipipe,
                     [try_until_even, try_until_positive],
                     mymax(4))

        assert next(gen) == 4
        assert gen.send(-4) == 'NOT POSITIVE!'
        assert gen.send(3) == 'NOT EVEN!'
        assert gen.send(90) == 90
        assert gentools.sendreturn(gen, 110) == 330


def test_combine_mappers():

    gen = gentools.imap_return(
        'result: {}'.format,
        gentools.imap_send(
            int,
            gentools.imap_yield(
                str,
                gentools.ipipe(
                    mymax(4),
                    try_until_even))))

    assert next(gen) == '4'
    assert gen.send(3) == 'NOT EVEN!'
    assert gen.send('5') == 'NOT EVEN!'
    assert gen.send(8.4) == '8'
    assert gentools.sendreturn(gen, 104) == 'result: 312'


def test_oneyield():

    @gentools.oneyield
    def myfunc(a, b, c):
        return a + b + c

    gen = myfunc(1, 2, 3)
    assert inspect.unwrap(myfunc).__name__ == 'myfunc'
    assert inspect.isgenerator(gen)
    assert next(gen) == 6
    assert gentools.sendreturn(gen, 9) == 9


def test_pipe():
    decorated = gentools.pipe(try_until_even, try_until_positive)(mymax)

    gen = decorated(4)
    assert next(gen) == 4
    assert gen.send(8) == 8
    assert gen.send(9) == 'NOT EVEN!'
    assert gen.send(2) == 8
    assert gen.send(-1) == 'NOT POSITIVE!'
    assert gentools.sendreturn(gen, 102) == 306


def test_map_yield():
    decorated = gentools.map_yield(str, lambda x: x * 2)(mymax)

    gen = decorated(5)
    assert next(gen) == '10'
    assert gen.send(2) == '10'
    assert gen.send(9) == '18'
    assert gen.send(12) == '24'
    assert gentools.sendreturn(gen, 103) == 309


def test_map_send():
    decorated = gentools.map_send(lambda x: x * 2, int)(mymax)

    gen = decorated(5)
    assert next(gen) == 5
    assert gen.send(5.3) == 10
    assert gen.send(9) == 18
    assert gentools.sendreturn(gen, '103') == 618


def test_map_return():
    decorated = gentools.map_return(lambda s: s.center(5), str)(mymax)
    gen = decorated(5)
    assert next(gen) == 5
    assert gen.send(9) == 9
    assert gentools.sendreturn(gen, 103) == ' 309 '


def test_combining_decorators():
    decorators = compose(
        gentools.map_return('result: {}'.format),
        gentools.map_send(int),
        gentools.map_yield(str),
        gentools.pipe(try_until_even),
    )
    decorated = decorators(mymax)
    gen = decorated(4)
    assert next(gen) == '4'
    assert gen.send('6') == '6'
    assert gen.send('5') == 'NOT EVEN!'
    assert gentools.sendreturn(gen, '104') == 'result: 312'

    assert inspect.unwrap(decorated) is mymax
