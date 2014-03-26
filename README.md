## Pytypedecl - https://github.com/google/pytypedecl/

Pytypedecl consists of a type declaration language for Python and an optional
run-time type checker. This project was started by [Raoul-Gabriel
Urma](http://www.urma.com) under the supervision of Peter Ludemann and Gregory
P. Smith during a summer 2013 internship at Google.

## License
Apache 2.0

## Motivation
### Why types declarations?

Type declarations are useful to document your code. This proposal starts a
conversation with the community to reach a standard for a type declaration
language for Python.

### Why runtime type-checking?
Runtime type-checking of optional type declarations is useful for code
maintenance and debugging. Our type-checker is available as a Python package.
You therefore do not need to run external tools to benefit from the
type-checking.

## Status
This project is in its infancy -- we intend to make many updates in the next
couple of months. We currently support Python 2.7. Support for Python 3 coming
soon.

## Type declaration language

Types declarations are specified in an external file with the
extension **"pytd"**. For example if you want to provide types for
**"application.py"**, you define the type inside the file
**"application.pytd"**. Examples of type declarations files can be
found in the **/tests/** folder.

Here’s an example of a type declaration file that mixes several features:
```python
class Logger:
  def log(messages: list<str>, buffer: Readable & Writeable) raises IOException
  def log(messages: list<str>) -> None
  def setStatus(status: int | str)
```


The type declaration language currently supports the following features:

* **Function signatures**: Functions can be given a signature following the
Python 3 function annotation convention. However, we extended it in a number of
ways that would be difficult or clumsy using Python 3's annotations.

* **Exceptions**: In addition to the return type, you can specify the
exceptions that the function might raise. There is no runtime checking
for this, but exceptions can be useful documentation and an automated
type inferencer could deduce the possible exceptions that a function
might throw.

* **Overloading**: A function is allowed to have multiple different signatures.
This is not supported in the Python 3 function annotation syntax but is
supported by pytypedecl.

* **None-able types**: A none-able type can represent the range of values for
its value type plus an additional None value. We use a trailing `?` to indicate
that a type is none-able. For example, a parameter of type `int?` can accept an
`int` or a `None` value.

* **Union types**: It is sometime convenient to indicate that a type can hold
values from a number of different types. Union types allow to express this
idea. For example `int | float` indicates that a value may be an `int` or a
`float`. There is no limit to the number of types in a union. A none-able type
can be seen as the union of a type and None -- `int?` is equivalent to
`int | NoneType`.

* **Intersection types**: An intersection type describes a type that
belongs to all values of a list of types. For example, the
intersection type `Readable & Writeable` describes a type that
supports the operations `open`, `close`, `read`, and `write`. As a
consequence, the intersection type `int & float` wouldn’t make much
sense because there isn’t a value in Python that is both an `int` and a
`float`.

* **Generics**: A type can be parameterised with a set of type arguments,
similarly to Java generics. For example, `generator[str]` describes a generator
that only produces `str`s, `dict[str,int]` describes a dictionary of keys of
type `str` and values of type `int`.

### Coming soon:
* Declaration of type parameters for methods and classes.
* Bounded type parameters
* Support for tags: @classmethod, @staticmethod...

## How to get started
```
git clone https://github.com/google/pytypedecl.git
python setup.py install
```
The package is now installed. You can run an example:
```
$ python -B demo.py
```
The **-B** flag prevents the generation of **pyc** file.

You can also run the tests:
```
$ python -B all_tests.py
```

Look into the **/examples/** directory to see how the emailer example
works. You need to do two things to type-check your program:

**1. Create a type declaration file**

Create a type declaration file that has the name of the Python file you want to
type-check but with the extension .pytd (e.g. email.pytd for email.py)

**2. Import the checker package**

Include the following two imports in the Python file that you want to
type-check:
```
import sys
import checker
```
And the following line after your function and class declarations (before they
are used)
```
checker.CheckFromFile(sys.modules[__name__], __file__ + "td")
```
That’s it! You can now run your python program and it will be type-checked at
runtime using the type declarations you defined in the **pytd** file.

## How to contribute to the project

* Check out the issue tracker
* Mailing List: https://groups.google.com/forum/#!forum/pytypedecl-dev
* Send us suggestions
* Fork

