"""tests interoperability with python3 syntax and features"""

import gentools


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
