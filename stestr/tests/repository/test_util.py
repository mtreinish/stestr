# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
import os
import shutil
import tempfile

from stestr.repository import util
from stestr.tests import base


class TestUtil(base.TestCase):

    def setUp(self):
        super(TestUtil, self).setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        cwd = os.getcwd()
        os.chdir(self.temp_dir)
        self.temp_dir = os.getcwd()
        self.addCleanup(os.chdir, cwd)

    def test_get_default_url_sql(self):
        repo_url = util._get_default_repo_url('sql')
        self.assertEqual('sqlite:///' + os.path.join(self.temp_dir,
                                                     '.stestr.sqlite'),
                         repo_url)

    def test_get_default_url_file(self):
        repo_url = util._get_default_repo_url('file')
        self.assertEqual(self.temp_dir, repo_url)

    def test_get_default_url_invalid_type(self):
        self.assertRaises(TypeError, util._get_default_repo_url,
                          'invalid_type')

    @mock.patch('importlib.import_module', side_effect=ImportError)
    def test_sql_get_repo_init_no_deps(self, import_mock):
        self.assertRaises(SystemExit, util.get_repo_initialise, 'sql')

    @mock.patch('importlib.import_module', side_effect=ImportError)
    def test_non_sql_get_repo_init_no_deps_import_error(self, import_mock):
        self.assertRaises(ImportError, util.get_repo_initialise, 'file')

    @mock.patch('importlib.import_module', side_effect=ImportError)
    def test_sql_get_repo_open_no_deps(self, import_mock):
        self.assertRaises(SystemExit, util.get_repo_open, 'sql')

    @mock.patch('importlib.import_module', side_effect=ImportError)
    def test_non_sql_get_repo_open_no_deps_import_error(self, import_mock):
        self.assertRaises(ImportError, util.get_repo_open, 'file')
