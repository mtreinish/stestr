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

"""Tests for the file repository implementation."""

import os.path

from testrepository.repository import file
from testrepository.tests import ResourcedTestCase
from testrepository.tests.stubpackage import TempDirResource


class TestFileRepository(ResourcedTestCase):

    resources = [('tempdir', TempDirResource())]

    def test_initialise(self):
        repo = file.Repository.initialise(self.tempdir)
        base = os.path.join(self.tempdir, '.testrepository')
        stream = open(os.path.join(base, 'format'), 'rb')
        try:
            contents = stream.read()
        finally:
            stream.close()
        self.assertEqual("1\n", contents)
        stream = open(os.path.join(base, 'next-stream'), 'rb')
        try:
            contents = stream.read()
        finally:
            stream.close()
        self.assertEqual("0\n", contents)
