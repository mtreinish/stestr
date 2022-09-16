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

import io

from stestr.commands import load
from stestr import subunit_trace
from stestr.tests import base


class TestLoadCommand(base.TestCase):
    def test_empty_with_pretty_out(self):
        # Clear results that may be there
        subunit_trace.RESULTS.clear()
        stream = io.BytesIO()
        output = io.BytesIO()
        res = load.load(
            in_streams=[("subunit", stream)], pretty_out=True, stdout=output
        )
        self.assertEqual(1, res)
