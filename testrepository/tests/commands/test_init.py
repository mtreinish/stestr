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

"""Tests for the commands module."""

import os.path
import sys

from testresources import TestResource

from testrepository.commands import init
from testrepository.ui.model import UI
from testrepository.tests import ResourcedTestCase
from testrepository.tests.monkeypatch import monkeypatch
from testrepository.tests.stubpackage import TempDirResource


class CDTempDir(object):
    """A tempdir we chdirred into."""

class CDTempDirResource(TestResource):

    resources = [('base', TempDirResource())]

    def make(self, dependency_resources):
        result = CDTempDir()
        result.orig = os.getcwd()
        os.chdir(dependency_resources['base'])
        return result

    def clean(self, resource):
        os.chdir(resource.orig)


class TestCommandInit(ResourcedTestCase):

    resources = [('cwd', CDTempDirResource())]

    def test_init_no_args_no_questions_no_output(self):
        ui = UI()
        cmd = init.init(ui)
        calls = []
        self.addCleanup(monkeypatch(
            'testrepository.repository.file.initialize',
            lambda url:calls.append(('called', url))))
        cmd.execute()
        self.assertEqual([('called', self.cwd.base)], calls)
