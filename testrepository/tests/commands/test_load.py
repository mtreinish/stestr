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

"""Tests for the load command."""

from testrepository.commands import load
from testrepository.ui.model import UI
from testrepository.tests import ResourcedTestCase
from testrepository.tests.test_repository import RecordingRepositoryFactory
from testrepository.repository import memory


class TestCommandLoad(ResourcedTestCase):

    def test_load_loads_subunit_stream_to_default_repository(self):
        ui = UI([('subunit', '')])
        cmd = load.load(ui)
        ui.set_command(cmd)
        calls = []
        cmd.repository_factory = RecordingRepositoryFactory(calls,
            memory.RepositoryFactory())
        repo = cmd.repository_factory.initialise(ui.here)
        del calls[:]
        cmd.execute()
        # Right repo
        self.assertEqual([('open', ui.here)], calls)
        # Stream consumed
        self.assertFalse('subunit' in ui.input_streams)
        # Results loaded
        self.assertEqual(1, repo.count())
