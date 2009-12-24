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

"""Persistent storage of test results."""

import os.path

from testrepository.repository import AbstractRepository


class Repository(AbstractRepository):
    """Disk based storage of test results.
    
    This repository stores each stream it receives as a file in a directory.
    Indices are then built on top of this basic store.
    
    This particular disk layout is subject to change at any time, as its
    primarily a bootstrapping exercise at this point. Any changes made are
    likely to have an automatic upgrade process.
    """
    
    @classmethod
    def initialise(klass, url):
        """Create a repository at url/path."""
        base = os.path.join(url, '.testrepository')
        os.mkdir(base)
        stream = file(os.path.join(base, 'format'), 'wb')
        try:
            stream.write('1\n')
        finally:
            stream.close()
        stream = file(os.path.join(base, 'next-stream'), 'wb')
        try:
            stream.write('0\n')
        finally:
            stream.close()
        return Repository()


