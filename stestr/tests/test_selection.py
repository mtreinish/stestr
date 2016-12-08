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

from stestr import selection
from stestr.tests import base


class TestSelection(base.TestCase):
    def test_filter_tests_no_filter(self):
        test_list = ['a', 'b', 'c']
        result = selection.filter_tests(None, test_list)
        self.assertEqual(test_list, result)
