import pickle
import sys
import types
from functools import reduce

import pytest

import gentools
from gentools import py2_compatible, return_
from gentools.utils import compose, PY2

from . import common


def with_generator(name):
    """use a python 2/3 parametrized generator"""
    gens = [getattr(common, name)]
    if not PY2:
        from . import py3
        gens.append(getattr(py3, name))
    return pytest.mark.parametrize(name, gens)


if PY2:
    from funcsigs import signature
else:
    from inspect import signature


def unwrap(func):
    while hasattr(func, '__wrapped__'):
        func = func.__wrapped__
    return func


@gentools.reusable
def mygen(a, foo):
    yield a
    yield foo


def test_stopiter_value():
    assert gentools.stopiter_value(StopIteration()) is None
    assert gentools.stopiter_value(StopIteration('foo')) == 'foo'


class TestYieldFrom:

    @with_generator('delegator')
    def test_throw_oneway(self, delegator):

        gen = delegator(iter([1, 2, 3]))

        assert next(gen) == 1
        assert next(gen) == 2
        with pytest.raises(ValueError):
            assert gen.throw(ValueError)

    @with_generator('delegator')
    @with_generator('mymax')
    def test_throw_returns(self, delegator, mymax):

        gen = delegator(mymax(4))

        assert next(gen) == 4
        assert gen.send(7) == 7
        assert gen.send(3) == 7
        try:
            assert gen.throw(TypeError)
        except StopIteration as e:
            result = e.args[0]
        else:
            raise RuntimeError('generator did not return')

        assert result == 'mymax: type error'

    @with_generator('delegator')
    @with_generator('mymax')
    def test_throw_continues(self, delegator, mymax):

        gen = delegator(mymax(4))

        assert next(gen) == 4
        assert gen.send(7) == 7
        assert gen.send(3) == 7
        assert gen.throw(ValueError) == 'caught ValueError'
        assert gentools.sendreturn(gen, 104) == 312

    @with_generator('delegator')
    def test_close_oneway(self, delegator):

        gen = delegator(iter([1, 2, 3]))

        assert next(gen) == 1
        assert next(gen) == 2
        assert gen.close() is None

    @with_generator('delegator')
    @with_generator('mymax')
    def test_close(self, delegator, mymax):

        gen = delegator(mymax(4))

        assert next(gen) == 4
        assert gen.send(7) == 7
        assert gen.send(3) == 7
        assert gen.close() is None

    @with_generator('oneway_delegator')
    def test_oneway(self, oneway_delegator):

        gen = oneway_delegator(iter([1, 2, 3]))

        assert next(gen) == 1
        assert next(gen) == 2
        assert next(gen) == 3
        assert gentools.sendreturn(gen, None) is None

    @with_generator('delegator')
    @with_generator('emptygen')
    def test_empty(self, delegator, emptygen):

        gen = delegator(emptygen())
        assert gentools.sendreturn(gen, None) == 99

    @with_generator('delegator')
    @with_generator('mymax')
    def test_simple(self, delegator, mymax):

        gen = delegator(mymax(4))

        assert next(gen) == 4
        assert gen.send(7) == 7
        assert gen.send(3) == 7
        assert gentools.sendreturn(gen, 103) == 309


class TestReusable:

    @pytest.mark.skipif(sys.version_info < (3, 5),
                        reason='requires python 3.5+')
    def test_picklable(self):
        gen = mygen(4, foo=5)
        assert pickle.loads(pickle.dumps(gen)) == gen

    @pytest.mark.skipif(sys.version_info < (3, ),
                        reason='requires python 3')
    def test_qualname(self):

        class Foo:

            @gentools.reusable
            def bar(bla):
                yield
                return

        assert Foo.bar.__qualname__.endswith('Foo.bar')

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

        assert list(Parent.staticgen(3, 9)) == [3, 9]
        assert list(p.staticgen(3, 9)) == [3, 9]

    def test_example(self):

        class mywrapper:
            def __init__(self, func):
                self.__wrapped__ = func
                self.__signature__ = signature(func).replace(
                    return_annotation=str)

            def __call__(self, *args, **kwargs):
                inner = self.__wrapped__(*args, **kwargs)
                yield str(next(inner))

        @gentools.reusable
        @mywrapper  # dummy to test combining with other decorators
        @py2_compatible
        def gentype(a, b, *cs, **fs):
            """my docstring"""
            return_((yield sum([a, b, sum(cs), sum(fs.values()), a])))

        gentype.__qualname__ = 'mymodule.gentype'

        assert issubclass(gentype, gentools.Generable)
        assert isinstance(unwrap, types.FunctionType)
        gentype.__name__ == 'myfunc'
        gentype.__doc__ == 'my docstring'
        gentype.__module__ == 'test_core'
        gen = gentype(4, 5, foo=10)

        assert {'a', 'b', 'cs', 'fs'} < set(dir(gen))
        assert gen.a == 4
        assert gen.b == 5
        assert gen.cs == ()
        assert gen.fs == {'foo': 10}

        assert next(iter(gen)) == '23'
        assert next(iter(gen)) == '23'  # reusable

        othergen = gentype(4, b=5, foo=10)
        assert gen == othergen
        assert not gen != othergen
        assert hash(gen) == hash(othergen)

        assert repr(gen) == ("mymodule.gentype("
                             "a=4, b=5, cs=(), fs={'foo': 10})")

        assert not gen == gentype(3, 4, 5, d=10)
        assert gen != gentype(1, 2, d=7)

        assert not gen == object()
        assert gen != object()

        changed = gen.replace(b=9)
        assert gen == gentype(4, 5, foo=10)
        assert changed == gentype(4, 9, foo=10)
        assert changed.b == 9


class TestSendReturn:

    @with_generator('mymax')
    def test_ok(self, mymax):
        gen = mymax(4)
        assert next(gen) == 4
        assert gentools.sendreturn(gen, 105) == 315

    @with_generator('mymax')
    def test_no_return(self, mymax):

        gen = mymax(4)
        assert next(gen) == 4
        with pytest.raises(RuntimeError, match='did not return'):
            gentools.sendreturn(gen, 1)


class TestIMapYield:

    @with_generator('emptygen')
    def test_empty(self, emptygen):
        try:
            next(gentools.imap_yield(str, emptygen()))
        except StopIteration as e:
            assert e.args[0] == 99

    @with_generator('mymax')
    def test_simple(self, mymax):
        mapped = gentools.imap_yield(str, mymax(4))

        assert next(mapped) == '4'
        assert mapped.send(7) == '7'
        assert mapped.send(3) == '7'
        assert gentools.sendreturn(mapped, 103) == 309


class TestIMapSend:

    @with_generator('emptygen')
    def test_empty(self, emptygen):
        try:
            next(gentools.imap_send(int, emptygen()))
        except StopIteration as e:
            assert e.args[0] == 99

    @with_generator('mymax')
    def test_simple(self, mymax):
        mapped = gentools.imap_send(int, mymax(4))

        assert next(mapped) == 4
        assert mapped.send('7') == 7
        assert mapped.send(7.3) == 7
        assert gentools.sendreturn(mapped, '104') == 312

    @with_generator('MyMax')
    def test_any_iterable(self, MyMax):
        mapped = gentools.imap_send(int, MyMax(4))

        assert next(mapped) == 4
        assert mapped.send('7') == 7
        assert mapped.send(7.3) == 7
        assert gentools.sendreturn(mapped, '104') == 312


class TestIMapReturn:

    @with_generator('emptygen')
    def test_empty(self, emptygen):
        try:
            next(gentools.imap_return(str, emptygen()))
        except StopIteration as e:
            assert e.args[0] == '99'

    @with_generator('mymax')
    def test_simple(self, mymax):
        mapped = gentools.imap_return(str, mymax(4))

        assert next(mapped) == 4
        assert mapped.send(7) == 7
        assert mapped.send(4) == 7
        assert gentools.sendreturn(mapped, 104) == '312'

    @with_generator('MyMax')
    def test_any_iterable(self, MyMax):
        mapped = gentools.imap_return(str, MyMax(4))

        assert next(mapped) == 4
        assert mapped.send(7) == 7
        assert mapped.send(4) == 7
        assert gentools.sendreturn(mapped, 104) == '312'


class TestIRelay:

    @with_generator('emptygen')
    @with_generator('try_until_positive')
    def test_empty(self, emptygen, try_until_positive):
        try:
            next(gentools.irelay(emptygen(), try_until_positive))
        except StopIteration as e:
            assert e.args[0] == 99

    @with_generator('mymax')
    @with_generator('try_until_positive')
    def test_simple(self, mymax, try_until_positive):
        relayed = gentools.irelay(mymax(4), try_until_positive)

        assert next(relayed) == 4
        assert relayed.send(7) == 7
        assert relayed.send(6) == 7
        assert relayed.send(-1) == 'NOT POSITIVE!'
        assert relayed.send(-4) == 'NOT POSITIVE!'
        assert relayed.send(0) == 7
        assert gentools.sendreturn(relayed, 102) == 306

    @with_generator('MyMax')
    @with_generator('try_until_positive')
    def test_any_iterable(self, MyMax, try_until_positive):
        relayed = gentools.irelay(MyMax(4), try_until_positive)

        assert next(relayed) == 4
        assert relayed.send(7) == 7
        assert relayed.send(6) == 7
        assert relayed.send(-1) == 'NOT POSITIVE!'
        assert relayed.send(-4) == 'NOT POSITIVE!'
        assert relayed.send(0) == 7
        assert gentools.sendreturn(relayed, 102) == 306

    @with_generator('mymax')
    @with_generator('try_until_positive')
    @with_generator('try_until_even')
    def test_accumulate(self, try_until_even, try_until_positive, mymax):

        gen = reduce(gentools.irelay,
                     [try_until_even, try_until_positive],
                     mymax(4))

        assert next(gen) == 4
        assert gen.send(-4) == 'NOT POSITIVE!'
        assert gen.send(3) == 'NOT EVEN!'
        assert gen.send(90) == 90
        assert gentools.sendreturn(gen, 110) == 330


@with_generator('mymax')
@with_generator('try_until_even')
def test_combine_mappers(mymax, try_until_even):

    gen = gentools.imap_return(
        'result: {}'.format,
        gentools.imap_send(
            int,
            gentools.imap_yield(
                str,
                gentools.irelay(
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
    assert unwrap(myfunc).__name__ == 'myfunc'
    assert next(gen) == 6
    assert gentools.sendreturn(gen, 9) == 9


@with_generator('mymax')
@with_generator('try_until_even')
@with_generator('try_until_positive')
def test_relay(mymax, try_until_even, try_until_positive):
    decorated = gentools.relay(try_until_even, try_until_positive)(mymax)

    gen = decorated(4)
    assert next(gen) == 4
    assert gen.send(8) == 8
    assert gen.send(9) == 'NOT EVEN!'
    assert gen.send(2) == 8
    assert gen.send(-1) == 'NOT POSITIVE!'
    assert gentools.sendreturn(gen, 102) == 306


@with_generator('mymax')
def test_map_yield(mymax):
    decorated = gentools.map_yield(str, lambda x: x * 2)(mymax)

    gen = decorated(5)
    assert next(gen) == '10'
    assert gen.send(2) == '10'
    assert gen.send(9) == '18'
    assert gen.send(12) == '24'
    assert gentools.sendreturn(gen, 103) == 309


@with_generator('mymax')
def test_map_send(mymax):
    decorated = gentools.map_send(lambda x: x * 2, int)(mymax)

    gen = decorated(5)
    assert next(gen) == 5
    assert gen.send(5.3) == 10
    assert gen.send(9) == 18
    assert gentools.sendreturn(gen, '103') == 618


@with_generator('mymax')
def test_map_return(mymax):
    decorated = gentools.map_return(lambda s: s.center(5), str)(mymax)
    gen = decorated(5)
    assert next(gen) == 5
    assert gen.send(9) == 9
    assert gentools.sendreturn(gen, 103) == ' 309 '


@with_generator('mymax')
@with_generator('try_until_even')
def test_combining_decorators(mymax, try_until_even):
    decorators = compose(
        gentools.map_return('result: {}'.format),
        gentools.map_send(int),
        gentools.map_yield(str),
        gentools.relay(try_until_even),
    )
    decorated = decorators(mymax)
    gen = decorated(4)
    assert next(gen) == '4'
    assert gen.send('6') == '6'
    assert gen.send('5') == 'NOT EVEN!'
    assert gentools.sendreturn(gen, '104') == 'result: 312'

    assert unwrap(decorated) is unwrap(mymax)
