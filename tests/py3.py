"""only python3-compatible generators"""


def try_until_positive(req):
    """an example relay"""
    response = yield req
    while response < 0:
        try:
            response = yield 'NOT POSITIVE!'
        except GeneratorExit:
            return ('positive: closed')
        except ValueError:
            yield 'caught ValueError'
    return response


def try_until_even(req):
    """an example relay"""
    response = yield req
    while response % 2:
        try:
            response = yield 'NOT EVEN!'
        except GeneratorExit:
            return ('even: closed')
        except ValueError:
            yield 'caught ValueError'
    return response


def mymax(val):
    """an example generator function"""
    while val < 100:
        try:
            sent = yield val
        except GeneratorExit:
            return ('mymax: closed')
        except ValueError:
            yield 'caught ValueError'
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
            try:
                sent = yield val
            except GeneratorExit:
                return ('mymax: closed')
            except ValueError:
                yield 'caught ValueError'
            if sent > val:
                val = sent
        return val * 3


def emptygen():
    if False:
        yield
    return 99
