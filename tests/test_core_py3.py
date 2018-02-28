"""tests interoperability with python3 syntax and features"""
import inspect
from functools import reduce

import pytest

import gentools
from gentools.utils import compose


def try_until_positive(req):
    """an example relay"""
    response = yield req
    while response < 0:
        response = yield 'NOT POSITIVE!'
    return response


def try_until_even(req):
    """an example relay"""
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


class TestPy2Compatible:

    def test_simple(self):

        @gentools.py2_compatible
        def mymax(val):
            """an example generator function"""
            while val < 100:
                sent = yield val
                if sent > val:
                    val = sent
            gentools.return_(val * 3)

        def delegator(start):
            return (yield from mymax(start))

        gen = delegator(4)

        assert next(gen) == 4
        assert gen.send(7) == 7
        assert gen.send(3) == 7
        assert gentools.sendreturn(gen, 103) == 309


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


class TestIRelay:

    def test_empty(self):
        try:
            next(gentools.irelay(emptygen(), try_until_positive))
        except StopIteration as e:
            assert e.value == 99

    def test_simple(self):
        relayed = gentools.irelay(mymax(4), try_until_positive)

        assert next(relayed) == 4
        assert relayed.send(7) == 7
        assert relayed.send(6) == 7
        assert relayed.send(-1) == 'NOT POSITIVE!'
        assert relayed.send(-4) == 'NOT POSITIVE!'
        assert relayed.send(0) == 7
        assert gentools.sendreturn(relayed, 102) == 306

    def test_any_iterable(self):
        relayed = gentools.irelay(MyMax(4), try_until_positive)

        assert next(relayed) == 4
        assert relayed.send(7) == 7
        assert relayed.send(6) == 7
        assert relayed.send(-1) == 'NOT POSITIVE!'
        assert relayed.send(-4) == 'NOT POSITIVE!'
        assert relayed.send(0) == 7
        assert gentools.sendreturn(relayed, 102) == 306

    def test_accumulate(self):

        gen = reduce(gentools.irelay,
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
    assert inspect.unwrap(myfunc).__name__ == 'myfunc'
    assert next(gen) == 6
    assert gentools.sendreturn(gen, 9) == 9


def test_relay():
    decorated = gentools.relay(try_until_even, try_until_positive)(mymax)

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
        gentools.relay(try_until_even),
    )
    decorated = decorators(mymax)
    gen = decorated(4)
    assert next(gen) == '4'
    assert gen.send('6') == '6'
    assert gen.send('5') == 'NOT EVEN!'
    assert gentools.sendreturn(gen, '104') == 'result: 312'

    assert inspect.unwrap(decorated) is mymax
