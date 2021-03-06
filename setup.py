import sys
import os.path
from setuptools import setup, find_packages


def read_local_file(fname):
    path = os.path.join(os.path.dirname(__file__), fname)
    with open(path, 'r') as rfile:
        return rfile.read()


metadata = {}
exec(read_local_file('gentools/__about__.py'), metadata)

readme = read_local_file('README.rst')
history = read_local_file('HISTORY.rst')


requires = []
if sys.version_info < (3, 5):
    requires.append('typing>=3.6.2')
if sys.version_info < (3, 4):
    requires.append('funcsigs>=1.0.2')

setup(
    name='gentools',
    version=metadata['__version__'],
    description=metadata['__description__'],
    license='MIT',
    long_description=readme + '\n\n' + history,
    url='https://github.com/ariebovenberg/gentools',

    author=metadata['__author__'],
    author_email='a.c.bovenberg@gmail.com',

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    install_requires=requires,
    keywords=['generators', 'itertools', 'coroutines'],
    python_requires='>=2.7',
    packages=find_packages(exclude=('tests', 'docs'))
)
