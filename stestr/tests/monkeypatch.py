#
# Copyright (c) 2009 Testrepository Contributors
# 
# Licensed under either the Apache License, Version 2.0 or the BSD 3-clause
# license at the users choice. A copy of both licenses are available in the
# project source as Apache-2.0 and BSD. You may not use this file except in
# compliance with one of these two licences.
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under these licenses is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# license you chose for the specific language governing permissions and
# limitations under that license.

"""Monkeypatch helper function for tests.

This has been moved to fixtures, and should be removed from here.
"""

def monkeypatch(name, new_value):
    """Replace name with new_value.

    :return: A callable which will restore the original value.
    """
    location, attribute = name.rsplit('.', 1)
    # Import, swallowing all errors as any element of location may be
    # a class or some such thing.
    try:
        __import__(location, {}, {})
    except ImportError:
        pass
    components = location.split('.')
    current = __import__(components[0], {}, {})
    for component in components[1:]:
        current = getattr(current, component)
    old_value = getattr(current, attribute)
    setattr(current, attribute, new_value)
    def restore():
        setattr(current, attribute, old_value)
    return restore
