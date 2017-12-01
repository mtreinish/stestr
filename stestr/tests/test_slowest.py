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

from stestr.commands import slowest
from stestr.tests import base


class TestSlowest(base.TestCase):
    def test_format_times(self):
        times = [('test_id_a', 12.34), ('test_id_b', 1.34)]
        res = slowest.format_times(times)
        self.assertEqual([('test_id_a', '12.340'), ('test_id_b', ' 1.340')],
                         res)

    def test_format_times_with_zero(self):
        times = [('test_id_a', 0), ('test_id_b', 1.34)]
        res = slowest.format_times(times)
        self.assertEqual([('test_id_a', '0.000'), ('test_id_b', '1.340')],
                         res)

    def test_format_times_all_zero(self):
        times = [('test_id_a', 0), ('test_id_b', 0.00)]
        res = slowest.format_times(times)
        self.assertEqual([('test_id_a', '0.000'), ('test_id_b', '0.000')],
                         res)
