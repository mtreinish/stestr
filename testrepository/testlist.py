#
# Copyright (c) 2012 Testrepository Contributors
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

"""Handling of lists of tests - common code to --load-list etc."""

from testtools.compat import _b, _u

def write_list(stream, test_ids):
    """Write test_ids out to stream.

    :param stream: A file-like object.
    :param test_ids: An iterable of test ids.
    """
    # May need utf8 explicitly?
    stream.write(_b('\n'.join(list(test_ids) + [''])))


def parse_list(list_bytes):
    """Parse list_bytes into a list of test ids."""
    return [id.strip() for id in list_bytes.decode('utf8').split(_u('\n'))
        if id.strip()]
