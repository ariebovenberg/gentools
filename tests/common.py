"""py2/3-compatible defined generators"""
from gentools import py2_compatible, return_, yield_from


@py2_compatible
def oneway_delegator(gen):
    yielder = yield_from(gen)
    for item in yielder:
        with yielder:
            yield item
    return_(yielder._result)


@py2_compatible
def delegator(gen):
    yielder = yield_from(gen)
    for item in yielder:
        try:
            with yielder:
                yielder.send((yield item))
        except GeneratorExit:
            return_('exiting...')
    return_(yielder._result)


@py2_compatible
def try_until_positive(req):
    """an example relay"""
    response = yield req
    while response < 0:
        try:
            response = yield 'NOT POSITIVE!'
        except GeneratorExit:
            return_('positive: closed')
        except ValueError:
            yield 'caught ValueError'
    return_(response)


@py2_compatible
def try_until_even(req):
    """an example relay"""
    response = yield req
    while response % 2:
        try:
            response = yield 'NOT EVEN!'
        except GeneratorExit:
            return_('even: closed')
        except ValueError:
            yield 'caught ValueError'
    return_(response)


@py2_compatible
def mymax(val):
    """an example generator function"""
    while val < 100:
        try:
            sent = yield val
        except GeneratorExit:
            return_('mymax: closed')
        except ValueError:
            sent = yield 'caught ValueError'
        except TypeError:
            return_('mymax: type error')
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
            try:
                sent = yield val
            except GeneratorExit:
                return_('mymax: closed')
            except ValueError:
                yield 'caught ValueError'
            if sent > val:
                val = sent
        return_(val * 3)


@py2_compatible
def emptygen():
    if False:
        yield
    return_(99)
