# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""A `traverse` visitor for processing documentation."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import inspect


class DocGeneratorVisitor(object):
  """A visitor that generates docs for a python object when __call__ed."""

  def __init__(self):
    self._index = {}
    self._tree = {}

  @property
  def index(self):
    """A map from fully qualified names to objects to be documented.

    The index is filled when the visitor is passed to `traverse`.

    Returns:
      The index filled by traversal.
    """
    return self._index

  @property
  def tree(self):
    """A map from fully qualified names to all its child names for traversal.

    The full name to member names map is filled when the visitor is passed to
    `traverse`.

    Returns:
      The full name to member name map filled by traversal.
    """
    return self._tree

  def __call__(self, parent_name, parent, children):
    """Visitor interface, see `tensorflow/tools/common:traverse` for details.

    This method is called for each symbol found in a traversal using
    `tensorflow/tools/common:traverse`. It should not be called directly in
    user code.

    Args:
      parent_name: The fully qualified name of a symbol found during traversal.
      parent: The Python object referenced by `parent_name`.
      children: A list of `(name, py_object)` pairs enumerating, in alphabetical
        order, the children (as determined by `inspect.getmembers`) of `parent`.
        `name` is the local name of `py_object` in `parent`.

    Raises:
      RuntimeError: If this visitor is called with a `parent` that is not a
        class or module.
    """
    self._index[parent_name] = parent
    self._tree[parent_name] = []

    if inspect.ismodule(parent):
      print('module %s: %r' % (parent_name, parent))
    elif inspect.isclass(parent):
      print('class %s: %r' % (parent_name, parent))
    else:
      raise RuntimeError('Unexpected type in visitor -- %s: %r' %
                         (parent_name, parent))

    for name, child in children:
      full_name = '.'.join([parent_name, name]) if parent_name else name
      self._index[full_name] = child
      self._tree[parent_name].append(name)

  def find_duplicates(self):
    """Compute data structures containing information about duplicates.

    Find duplicates in `index` and decide on one to be the "master" name.

    Returns a map `duplicate_of` from aliases to their master name (the master
    name itself has no entry in this map), and a map `duplicates` from master
    names to a lexicographically sorted list of all aliases for that name (incl.
    the master name).

    Returns:
      A tuple `(duplicate_of, duplicates)` as described above.
    """
    # Maps the id of a symbol to its fully qualified name. For symbols that have
    # several aliases, this map contains the first one found.
    # We use id(py_object) to get a hashable value for py_object. Note all
    # objects in _index are in memory at the same time so this is safe.
    reverse_index = {}

    # Make a preliminary duplicates map. For all sets of duplicate names, it
    # maps the first name found to a list of all duplicate names.
    raw_duplicates = {}
    for full_name, py_object in self._index.iteritems():
      # We cannot use the duplicate mechanism for constants, since e.g.,
      # id(c1) == id(c2) with c1=1, c2=1. This is unproblematic since constants
      # have no usable docstring and won't be documented automatically.
      if (inspect.ismodule(py_object) or
          inspect.isclass(py_object) or
          inspect.isfunction(py_object) or
          inspect.isroutine(py_object) or
          inspect.ismethod(py_object) or
          isinstance(py_object, property)):
        object_id = id(py_object)
        if object_id in reverse_index:
          master_name = reverse_index[object_id]
          if master_name in raw_duplicates:
            raw_duplicates[master_name].append(full_name)
          else:
            raw_duplicates[master_name] = [master_name, full_name]
        else:
          reverse_index[object_id] = full_name

    # Decide on master names, rewire duplicates and make a duplicate_of map
    # mapping all non-master duplicates to the master name. The master symbol
    # does not have an entry in this map.
    duplicate_of = {}
    # Duplicates maps the main symbols to the set of all duplicates of that
    # symbol (incl. itself).
    duplicates = {}
    for names in raw_duplicates.values():
      names = sorted(names)

      # Choose the lexicographically first name with the minimum number of
      # submodules. This will prefer highest level namespace for any symbol.
      master_name = min(names, key=lambda name: name.count('.'))

      duplicates[master_name] = names
      for name in names:
        if name != master_name:
          duplicate_of[name] = master_name

    return duplicate_of, duplicates