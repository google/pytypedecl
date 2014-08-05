# Copyright 2006 Google, Inc. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

"""
Python parse tree definitions.

WARNING: This version is modified for use as a testcase for python type
checking. Do not use this for anything else!!

This is a very concrete parse tree; we need to keep every token and
even the comments and whitespace between tokens.
"""

def type_repr(type_num):
    """Map a type number to its string representation."""
    return str(type_num)

class Base(object):

    """
    Abstract base class for Node and Leaf.

    This provides some default functionality and boilerplate using the
    template pattern.

    A node may be a subnode of at most one parent.

    Each subclass of Base must provide a __str__ implementation that returns
    exactly the input that was used to create the item in the tree.

    Each subclass of Base must provide a value attribute, and the ranges of
    values must be distinct for each subclass. This isn't a strict requirement,
    but it's convenient so that instead of writing
        if isinstance(node, Leaf) and node.type == TOKEN.name:
    you can just write
        if node.type == TOKEN.name:
    """

    # Default values for instance variables
    type = None    # int: token number (< 256) or symbol number (>= 256)
    parent = None  # Parent node pointer, or None
    children = ()  # Tuple of subnodes
    was_changed = False
    was_checked = False

    def __new__(cls, *args, **kwds):
        """Constructor that prevents Base from being instantiated."""
        assert cls is not Base, "Cannot instantiate Base"
        return object.__new__(cls)

    def __eq__(self, other):
        """
        Compare two nodes for equality.

        This calls the method _eq().
        """
        if self is other:
            return True
        # We assume that it doesn't make sense to compare a class with a
        # subclass ... if that changes, then the following test needs to be
        # changed to something that uses isssubclass.
        if self.__class__ is not other.__class__:
            return NotImplemented
        return self._eq(other)  # Implemented by subclass

    __hash__ = None  # For Py3 compatibility.

    def __ne__(self, other):
        """
        Compare two nodes for inequality.

        This calls the method _eq().
        """
        if self.__class__ is not other.__class__:
            return NotImplemented
        return not self._eq(other)

    def _eq(self, other):
        """
        Compare two nodes for equality.

        This is called by __eq__ and __ne__.  It is only called if the two nodes
        have the same type.  This must be implemented by the concrete subclass.
        Nodes should be considered equal if they have the same structure,
        ignoring the prefix string and other context information.
        """
        raise NotImplementedError

    def clone(self):
        """
        Return a cloned (deep) copy of self.

        This must be implemented by the concrete subclass.
        """
        raise NotImplementedError

    def post_order(self):
        """
        Post-order iterator for the tree.

        This must be implemented by the concrete subclass.
        """
        raise NotImplementedError

    def pre_order(self):
        """
        Pre-order iterator for the tree.

        This must be implemented by the concrete subclass.
        """
        raise NotImplementedError

    def set_prefix(self, prefix):
        """
        Set the prefix for the node (see Leaf class).

        DEPRECATED; use the prefix property directly.
        """
        print("set_prefix() is deprecated; use the prefix property")
        self.prefix = prefix

    def get_prefix(self):
        """
        Return the prefix for the node (see Leaf class).

        DEPRECATED; use the prefix property directly.
        """
        print("get_prefix() is deprecated; use the prefix property")
        return self.prefix

    def replace(self, new):
        """Replace this node with a new one in the parent."""
        assert self.parent is not None, str(self)
        assert new is not None
        if not isinstance(new, list):
            new = [new]
        l_children = []
        found = False
        for ch in self.parent.children:
            if ch is self:
                assert not found, (self.parent.children, self, new)
                if new is not None:
                    l_children.extend(new)
                found = True
            else:
                l_children.append(ch)
        assert found, (self.children, self, new)
        self.parent.changed()
        self.parent.children = l_children
        for x in new:
            x.parent = self.parent
        self.parent = None

    def get_lineno(self):
        """Return the line number which generated the invocant node."""
        node = self
        while not isinstance(node, Leaf):
            if not node.children:
                return
            node = node.children[0]
        return node.lineno

    def changed(self):
        if self.parent:
            self.parent.changed()
        self.was_changed = True

    def remove(self):
        """
        Remove the node from the tree. Returns the position of the node in its
        parent's children before it was removed.
        """
        if self.parent:
            for i, node in enumerate(self.parent.children):
                if node is self:
                    self.parent.changed()
                    del self.parent.children[i]
                    self.parent = None
                    return i

    @property
    def next_sibling(self):
        """
        The node immediately following the invocant in their parent's children
        list. If the invocant does not have a next sibling, it is None
        """
        if self.parent is None:
            return None

        # Can't use index(); we need to test by identity
        for i, child in enumerate(self.parent.children):
            if child is self:
                try:
                    return self.parent.children[i+1]
                except IndexError:
                    return None

    @property
    def prev_sibling(self):
        """
        The node immediately preceding the invocant in their parent's children
        list. If the invocant does not have a previous sibling, it is None.
        """
        if self.parent is None:
            return None

        # Can't use index(); we need to test by identity
        for i, child in enumerate(self.parent.children):
            if child is self:
                if i == 0:
                    return None
                return self.parent.children[i-1]

    def leaves(self):
        for child in self.children:
            for x in child.leaves():
                yield x

    def depth(self):
        if self.parent is None:
            return 0
        return 1 + self.parent.depth()

    def get_suffix(self):
        """
        Return the string immediately following the invocant node. This is
        effectively equivalent to node.next_sibling.prefix
        """
        next_sib = self.next_sibling
        if next_sib is None:
            return u""
        return next_sib.prefix

    @property
    def type_repr(self):
        """Get the type as a human-readable string."""
        return type_repr(self.type)

    def descend_to(self, indexes):
        """Takes a sequence of integers and descends via children.

        For example,
          descend_to([]) returns self;
          descend_to([0]) returns self.children[0];
          descend_to([2,5,3]) returns self.children[2].children[5],children[3].

        In effect, this gives each node a unique number, which is the list of
        child # that is needed to get to it.
        """
        node = self
        for i in indexes:
            node = node.children[i]
        return node

    def label_nodes(self, indexes=None):
        """Create 'label' attritbute for each Node/Leaf.

        Args:
          indexes is used internally to keep track of the path to here.
        """
        indexes = indexes or []
        self.label = indexes
        try:
            for i, ch in enumerate(self.children):
                ch.label_nodes(indexes + [i])
        except AttributeError:
            pass  # Leaf has no children


class Node(Base):

    """Concrete implementation for interior nodes.

    The __str__ value is derived entirely from the children, and ultimately
    from the concrete realization of the Leaf nodes below this.

    The _eq method (see Base.__eq__) compares only type and recursively
    the children. Extra attributes, such as context or label, are ignored.
    """

    def __init__(self, type, children,
                 context=None,
                 prefix=None,
                 fixers_applied=None):
        """
        Initializer.

        Takes a type constant (a symbol number >= 256) and a sequence of child
        nodes.  The 'context' keyword argument is ignored -- its presence
        simplifies some callers, but in reality the information (prefix, lineno,
        column) is kept in the Leaf nodes (this information is used by the
        __str__ method, which is derived from the children of the node, and
        utlimately from the Leaf nodes.

        As a side effect, the parent pointers of the children are updated.
        """
        assert type >= 256, (type, type_repr(type))
        self.type = type
        self.children = list(children)
        for ch in self.children:
            assert ch.parent is None, repr(ch)
            ch.parent = self
        if prefix is not None:
            self.prefix = prefix
        if fixers_applied:
            self.fixers_applied = fixers_applied[:]
        else:
            self.fixers_applied = None

    def __repr__(self):
        """Return a canonical string representation."""
        return "%s(%s, %r)" % (self.__class__.__name__,
                               self.type_repr, self.children)

    def __unicode__(self):
        """
        Return a pretty string representation.

        This reproduces the input source exactly.
        """
        return u"".join(map(unicode, self.children))

    def _eq(self, other):
        """Compare two nodes for equality (using type, children) -
           see Base.__eq__
        """
        return (self.type, self.children) == (other.type, other.children)

    def clone(self):
        """Return a cloned (deep) copy of self."""
        n = Node(self.type, [ch.clone() for ch in self.children],
                 fixers_applied=self.fixers_applied)
        try:
            n.label = self.label[:]
        except AttributeError:
            pass  # if label_nodes() hasn't been done, quietly do nothing
        return n

    def post_order(self):
        """Post-order iterator for the tree."""
        for child in self.children:
            for node in child.post_order():
                yield node
        yield self

    def pre_order(self):
        """Pre-order iterator for the tree."""
        yield self
        for child in self.children:
            for node in child.pre_order():
                yield node

    def _prefix_getter(self):
        """
        The whitespace and comments preceding this node in the input.
        """
        if not self.children:
            return ""
        return self.children[0].prefix

    def _prefix_setter(self, prefix):
        if self.children:
            self.children[0].prefix = prefix

    prefix = property(_prefix_getter, _prefix_setter)

    def set_child(self, i, child):
        """
        Equivalent to 'node.children[i] = child'. This method also sets the
        child's parent attribute appropriately.
        """
        child.parent = self
        self.children[i].parent = None
        self.children[i] = child
        self.changed()

    def insert_child(self, i, child):
        """
        Equivalent to 'node.children.insert(i, child)'. This method also sets
        the child's parent attribute appropriately.
        """
        child.parent = self
        self.children.insert(i, child)
        self.changed()

    def append_child(self, child):
        """
        Equivalent to 'node.children.append(child)'. This method also sets the
        child's parent attribute appropriately.
        """
        child.parent = self
        self.children.append(child)
        self.changed()


class Leaf(Base):

    """Concrete implementation for leaf nodes.

    The __str__ value is derived from the prefix and the value. The prefix is
    any white space and comments before this item (e.g., Leaf(token.NEWLINE,
    value="\n", prefix=" # comment").

    The _eq method (see Base.__eq__) compares only type and value.
    """

    # Default values for instance variables
    _prefix = ""  # Whitespace and comments preceding this token in the input
    lineno = 0    # Line where this token starts in the input
    column = 0    # Column where this token starts in the input

    def __init__(self, type, value,
                 context=None,
                 prefix=None,
                 fixers_applied=[]):
        """
        Initializer.

        Takes a type constant (a token number < 256), a string value, and an
        optional context keyword argument (prefix, (lineno, column)). If the
        prefix keyword argument is provided, it overrides the prefix derived
        from the context. The prefix is the text that appears before the value
        (e.g., blanks and comments).

        """
        assert 0 <= type < 256, type
        if context is not None:
            self._prefix, (self.lineno, self.column) = context
        self.type = type
        self.value = value
        if prefix is not None:
            self._prefix = prefix
        self.fixers_applied = fixers_applied[:]

    def __repr__(self):
        """Return a canonical string representation."""
        return "%s(%s, %r)" % (self.__class__.__name__,
                               self.type_repr, self.value)

    def __unicode__(self):
        """
        Return a pretty string representation.

        This reproduces the input source exactly.
        """
        return self.prefix + unicode(self.value)

    def _eq(self, other):
        """Compare two nodes for equality (type and value)."""
        return (self.type, self.value) == (other.type, other.value)

    def clone(self):
        """Return a cloned (deep) copy of self."""
        l = Leaf(self.type, self.value,
                 (self.prefix, (self.lineno, self.column)),
                 fixers_applied=self.fixers_applied)
        try:
            l.label = self.label[:]
        except AttributeError:
            pass  # if label_nodes() hasn't been done, quietly do nothing
        return l

    def leaves(self):
        yield self

    def post_order(self):
        """Post-order iterator for the tree."""
        yield self

    def pre_order(self):
        """Pre-order iterator for the tree."""
        yield self

    def _prefix_getter(self):
        """
        The whitespace and comments preceding this token in the input.
        """
        return self._prefix

    def _prefix_setter(self, prefix):
        self.changed()
        self._prefix = prefix

    prefix = property(_prefix_getter, _prefix_setter)


def assertTrue(b):
    assert b
def assertFalse(b):
    assert not b
def assertEqual(a, b):
    assert a == b
def assertNotEqual(a, b):
    assert a != b

if __name__ == "__main__":
    # This code is just the concatenation of all the tests for pytree. The blank
    # lines are the divisions between the original tests.
    l1 = Leaf(100, "foo")
    assertEqual(l1.type, 100)
    assertEqual(l1.value, "foo")

    l1 = Leaf(100, "foo")
    assertEqual(repr(l1), "Leaf(100, 'foo')")

    l1 = Leaf(100, "foo")
    assertEqual(str(l1), "foo")
    l2 = Leaf(100, "foo", context=(" ", (10, 1)))
    assertEqual(str(l2), " foo")

    # Make sure that the Leaf's value is stringified. Failing to
    #  do this can cause a TypeError in certain situations.
    l1 = Leaf(2, 5)
    l1.prefix = "foo_"
    assertEqual(str(l1), "foo_5")

    l1 = Leaf(100, "foo")
    l2 = Leaf(100, "foo", context=(" ", (1, 0)))
    assertEqual(l1, l2)
    l3 = Leaf(101, "foo")
    l4 = Leaf(100, "bar")
    assertNotEqual(l1, l3)
    assertNotEqual(l1, l4)

    l1 = Leaf(100, "foo")
    assertEqual(l1.prefix, "")
    assertFalse(l1.was_changed)
    l1.prefix = "  ##\n\n"
    assertEqual(l1.prefix, "  ##\n\n")
    assertTrue(l1.was_changed)

    l1 = Leaf(100, "foo")
    l2 = Leaf(200, "bar")
    n1 = Node(1000, [l1, l2])
    assertEqual(n1.type, 1000)
    assertEqual(n1.children, [l1, l2])

    l1 = Leaf(100, "foo")
    l2 = Leaf(100, "bar", context=(" ", (1, 0)))
    n1 = Node(1000, [l1, l2])
    assertEqual(repr(n1),
                     "Node(1000, [%s, %s])" % (repr(l1), repr(l2)))

    l1 = Leaf(100, "foo")
    l2 = Leaf(100, "bar", context=(" ", (1, 0)))
    n1 = Node(1000, [l1, l2])
    assertEqual(str(n1), "foo bar")

    l1 = Leaf(100, "foo")
    assertEqual(l1.prefix, "")
    n1 = Node(1000, [l1])
    assertEqual(n1.prefix, "")
    n1.prefix = " "
    assertEqual(n1.prefix, " ")
    assertEqual(l1.prefix, " ")

    l1 = Leaf(100, "foo", prefix="a")
    l2 = Leaf(100, "bar", prefix="b")
    n1 = Node(1000, [l1, l2])
    assertEqual(l1.get_suffix(), l2.prefix)
    assertEqual(l2.get_suffix(), "")
    assertEqual(n1.get_suffix(), "")

    l3 = Leaf(100, "bar", prefix="c")
    n2 = Node(1000, [n1, l3])
    assertEqual(n1.get_suffix(), l3.prefix)
    assertEqual(l3.get_suffix(), "")
    assertEqual(n2.get_suffix(), "")

    n1 = Node(1000, ())
    n2 = Node(1000, [], context=(" ", (1, 0)))
    assertEqual(n1, n2)
    n3 = Node(1001, ())
    assertNotEqual(n1, n3)

    l1 = Leaf(100, "foo")
    l2 = Leaf(100, "foo")
    n1 = Node(1000, [l1])
    n2 = Node(1000, [l2])
    assertEqual(n1, n2)
    l3 = Leaf(100, "bar")
    n3 = Node(1000, [l3])
    assertNotEqual(n1, n3)

    l1 = Leaf(100, "foo")
    l2 = Leaf(100, "+")
    l3 = Leaf(100, "bar")
    n1 = Node(1000, [l1, l2, l3])
    assertEqual(n1.children, [l1, l2, l3])
    assertTrue(isinstance(n1.children, list))
    assertFalse(n1.was_changed)
    l2new = Leaf(100, "-")
    l2.replace(l2new)
    assertEqual(n1.children, [l1, l2new, l3])
    assertTrue(isinstance(n1.children, list))
    assertTrue(n1.was_changed)

    l1 = Leaf(100, "foo")
    l2 = Leaf(100, "+")
    l3 = Leaf(100, "bar")
    n1 = Node(1000, [l1, l2, l3])
    l2.replace([Leaf(100, "*"), Leaf(100, "*")])
    assertEqual(str(n1), "foo**bar")
    assertTrue(isinstance(n1.children, list))

    l1 = Leaf(100, "foo")
    l2 = Leaf(100, "bar")
    l3 = Leaf(100, "fooey")
    n2 = Node(1000, [l1, l2])
    n3 = Node(1000, [l3])
    n1 = Node(1000, [n2, n3])
    assertEqual(list(n1.leaves()), [l1, l2, l3])

    l1 = Leaf(100, "foo")
    l2 = Leaf(100, "bar")
    n2 = Node(1000, [l1, l2])
    n3 = Node(1000, [])
    n1 = Node(1000, [n2, n3])
    assertEqual(l1.depth(), 2)
    assertEqual(n3.depth(), 1)
    assertEqual(n1.depth(), 0)

    l1 = Leaf(100, "foo")
    l2 = Leaf(100, "bar")
    l3 = Leaf(100, "fooey")
    c1 = Node(1000, [l1, l2])
    n1 = Node(1000, [c1, l3])
    assertEqual(list(n1.post_order()), [l1, l2, c1, l3, n1])

    l1 = Leaf(100, "foo")
    l2 = Leaf(100, "bar")
    l3 = Leaf(100, "fooey")
    c1 = Node(1000, [l1, l2])
    n1 = Node(1000, [c1, l3])
    assertEqual(list(n1.pre_order()), [n1, c1, l1, l2, l3])

    l1 = Leaf(100, "f")
    assertFalse(l1.was_changed)
    l1.changed()
    assertTrue(l1.was_changed)

    l1 = Leaf(100, "f")
    n1 = Node(1000, [l1])
    assertFalse(n1.was_changed)
    n1.changed()
    assertTrue(n1.was_changed)

    l1 = Leaf(100, "foo")
    l2 = Leaf(100, "+")
    l3 = Leaf(100, "bar")
    n1 = Node(1000, [l1, l2, l3])
    n2 = Node(1000, [n1])
    assertFalse(l1.was_changed)
    assertFalse(n1.was_changed)
    assertFalse(n2.was_changed)
    n1.changed()
    assertTrue(n1.was_changed)
    assertTrue(n2.was_changed)
    assertFalse(l1.was_changed)

    for prefix in ("xyz_", ""):
        l1 = Leaf(100, "self", prefix=prefix)
        assertTrue(str(l1), prefix + "self")
        assertEqual(l1.prefix, prefix)

    for prefix in ("xyz_", ""):
        l1 = Leaf(100, "self")
        l2 = Leaf(100, "foo", prefix="_")
        n1 = Node(1000, [l1, l2], prefix=prefix)
        assertTrue(str(n1), prefix + "self_foo")
        assertEqual(n1.prefix, prefix)
        assertEqual(l1.prefix, prefix)
        assertEqual(l2.prefix, "_")

    l1 = Leaf(100, "foo")
    l2 = Leaf(100, "foo")
    n1 = Node(1000, [l1, l2])
    n2 = Node(1000, [n1])
    assertEqual(n1.remove(), 0)
    assertEqual(n2.children, [])
    assertEqual(l1.parent, n1)
    assertEqual(n1.parent, None)
    assertEqual(n2.parent, None)
    assertFalse(n1.was_changed)
    assertTrue(n2.was_changed)
    assertEqual(l2.remove(), 1)
    assertEqual(l1.remove(), 0)
    assertEqual(n1.children, [])
    assertEqual(l1.parent, None)
    assertEqual(n1.parent, None)
    assertEqual(n2.parent, None)
    assertTrue(n1.was_changed)
    assertTrue(n2.was_changed)

    n1 = Node(1000, [])
    n1.remove()
    assertEqual(n1.parent, None)

    l1 = Leaf(100, "foo")
    l1.remove()
    assertEqual(l1.parent, None)

    l1 = Leaf(100, "foo")
    n1 = Node(1000, [l1])

    l2 = Leaf(100, "bar")
    n1.set_child(0, l2)
    assertEqual(l1.parent, None)
    assertEqual(l2.parent, n1)
    assertEqual(n1.children, [l2])

    n2 = Node(1000, [l1])
    n2.set_child(0, n1)
    assertEqual(l1.parent, None)
    assertEqual(n1.parent, n2)
    assertEqual(n2.parent, None)
    assertEqual(n2.children, [n1])

    l1 = Leaf(100, "foo")
    n1 = Node(1000, [l1])
    l2 = Leaf(100, "bar")
    n1.insert_child(0, l2)
    assertEqual(l2.parent, n1)
    assertEqual(n1.children, [l2, l1])
    l3 = Leaf(100, "abc")
    n1.insert_child(2, l3)
    assertEqual(n1.children, [l2, l1, l3])

    n1 = Node(1000, [])
    l1 = Leaf(100, "foo")
    n1.append_child(l1)
    assertEqual(l1.parent, n1)
    assertEqual(n1.children, [l1])
    l2 = Leaf(100, "bar")
    n1.append_child(l2)
    assertEqual(l2.parent, n1)
    assertEqual(n1.children, [l1, l2])

    n1 = Node(1000, [])
    n2 = Node(1000, [])
    p1 = Node(1000, [n1, n2])
    assertTrue(n1.next_sibling is n2)
    assertEqual(n2.next_sibling, None)
    assertEqual(p1.next_sibling, None)

    l1 = Leaf(100, "a")
    l2 = Leaf(100, "b")
    p1 = Node(1000, [l1, l2])
    assertTrue(l1.next_sibling is l2)
    assertEqual(l2.next_sibling, None)
    assertEqual(p1.next_sibling, None)

    n1 = Node(1000, [])
    n2 = Node(1000, [])
    p1 = Node(1000, [n1, n2])
    assertTrue(n2.prev_sibling is n1)
    assertEqual(n1.prev_sibling, None)
    assertEqual(p1.prev_sibling, None)

    l1 = Leaf(100, "a")
    l2 = Leaf(100, "b")
    p1 = Node(1000, [l1, l2])
    assertTrue(l2.prev_sibling is l1)
    assertEqual(l1.prev_sibling, None)
    assertEqual(p1.prev_sibling, None)
