from gentools import py2_compatible, return_


@py2_compatible
def try_until_positive(req):
    """an example relay"""
    response = yield req
    while response < 0:
        response = yield 'NOT POSITIVE!'
    return_(response)


@py2_compatible
def try_until_even(req):
    """an example relay"""
    response = yield req
    while response % 2:
        response = yield 'NOT EVEN!'
    return_(response)


@py2_compatible
def mymax(val):
    """an example generator function"""
    while val < 100:
        sent = yield val
        if sent > val:
            val = sent
    return_(val * 3)


class MyMax:
    """an example generator iterable"""

    def __init__(self, start):
        self.start = start

    @py2_compatible
    def __iter__(self):
        val = self.start
        while val < 100:
            sent = yield val
            if sent > val:
                val = sent
        return_(val * 3)


@py2_compatible
def emptygen():
    if False:
        yield
    return_(99)
