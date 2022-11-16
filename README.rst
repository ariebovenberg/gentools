Gentools
========

.. image:: https://img.shields.io/pypi/v/gentools.svg?style=flat-square
    :target: https://pypi.python.org/pypi/gentools

.. image:: https://img.shields.io/pypi/l/gentools.svg?style=flat-square
    :target: https://pypi.python.org/pypi/gentools

.. image:: https://img.shields.io/pypi/pyversions/gentools.svg?style=flat-square
    :target: https://pypi.python.org/pypi/gentools

.. image:: https://img.shields.io/travis/ariebovenberg/gentools.svg?style=flat-square
    :target: https://travis-ci.org/ariebovenberg/gentools

.. image:: https://img.shields.io/codecov/c/github/ariebovenberg/gentools.svg?style=flat-square
    :target: https://coveralls.io/github/ariebovenberg/gentools?branch=master

.. image:: https://img.shields.io/readthedocs/gentools.svg?style=flat-square
    :target: http://gentools.readthedocs.io/en/latest/?badge=latest


Tools for generators, generator functions, and generator-based coroutines.

Key features:

* Create reusable generators
* Compose generators
* Build python 2/3-compatible generators (``gentools`` version <1.2 only)

Installation
------------

.. code-block:: bash

   pip install gentools

Examples
--------

- Make generator functions reusable:

.. code-block:: python

   >>> @reusable
   ... def countdown(value, step):
   ...     while value > 0:
   ...         yield value
   ...         value -= step

   >>> from_3 = countdown(3, step=1)
   >>> list(from_3)
   [3, 2, 1]
   >>> list(from_3)
   [3, 2, 1]
   >>> isinstance(from_3, countdown)  # generator func is wrapped in a class
   True
   >>> from_3.step  # attribute access to arguments
   1
   >>> from_3.replace(value=5)  # create new instance with replaced fields
   countdown(value=5, step=1)  # descriptive repr()

- map a generator's ``yield``, ``send``, and ``return`` values:

.. code-block:: python

   >>> @map_return('final value: {}'.format)
   ... @map_send(int)
   ... @map_yield('the current max is: {}'.format)
   ... def my_max(value):
   ...     while value < 100:
   ...         newvalue = yield value
   ...         if newvalue > value:
   ...             value = newvalue
   ...     return value

   >>> gen = my_max(5)
   >>> next(gen)
   'the current max is: 5'
   >>> gen.send(11.3)
   'the current max is: 11'
   >>> gen.send(104)
   StopIteration('final value: 104')

- relay a generator's yield/send interactions through another generator:

.. code-block:: python

   >>> def try_until_positive(outvalue):
   ...     value = yield outvalue
   ...     while value < 0:
   ...         value = yield 'not positive, try again'
   ...     return value

   >>> @relay(try_until_positive)
   ... def my_max(value):
   ...     while value < 100:
   ...         newvalue = yield value
   ...         if newvalue > value:
   ...             value = newvalue
   ...     return value

   >>> gen = my_max(5)
   >>> next(gen)
   5
   >>> gen.send(-4)
   'not positive, try again'
   >>> gen.send(-1)
   'not positive, try again'
   >>> gen.send(8)
   8
   >>> gen.send(104)
   StopIteration(104)

- make python 2/3 compatible generators with ``return``. 
  (`gentools` version <1.2 only)

.. code-block:: python

   >>> @py2_compatible
   ... def my_max(value):
   ...     while value < 100:
   ...         newvalue = yield value
   ...         if newvalue > value:
   ...             value = newvalue
   ...     return_(value)
