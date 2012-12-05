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

"""Tests for the path argument type."""

import os
from os.path import join
import tempfile

from fixtures import TempDir
from testtools.matchers import raises

from testrepository.arguments import path
from testrepository.tests import ResourcedTestCase


class TestArgument(ResourcedTestCase):

    def test_parses_as_string(self):
        existingfile = tempfile.NamedTemporaryFile()
        self.addCleanup(existingfile.close)
        arg = path.ExistingPathArgument('path')
        result = arg.parse([existingfile.name])
        self.assertEqual([existingfile.name], result)

    def test_rejects_doubledash(self):
        base = self.useFixture(TempDir()).path
        arg = path.ExistingPathArgument('path')
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(base)
        with file('--', 'wb') as f:pass
        self.assertThat(lambda: arg.parse(['--']), raises(ValueError))

    def test_rejects_missing_file(self):
        base = self.useFixture(TempDir()).path
        arg = path.ExistingPathArgument('path')
        self.assertThat(lambda: arg.parse([join(base, 'foo')]),
            raises(ValueError))
