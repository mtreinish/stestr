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

from stestr import output
from stestr.tests import base


class TestOutput(base.TestCase):

    def test_output_table(self):
        table = [['Header 1', 'Header 2', 'Header 999'],
                 [1, '0000000002', 'foo'],
                 ['bar', 6, 'This is a content.']]
        expected = \
            "Header 1  Header 2    Header 999\n" \
            "--------  ----------  ------------------\n" \
            "1         0000000002  foo\n" \
            "bar       6           This is a content.\n"
        with io.StringIO() as f:
            output.output_table(table, f)
            actual = f.getvalue()
            self.assertEqual(expected, actual)

    def test_output_tests(self):
        class Test:
            def __init__(self, i):
                self.i = i

            def id(self):
                return self.i

        tests = [Test('a'), Test('b'), Test('foo')]
        expected = "a\nb\nfoo\n"
        with io.StringIO() as f:
            output.output_tests(tests, f)
            actual = f.getvalue()
            self.assertEqual(expected, actual)

    def test_output_summary_passed(self):
        expected = 'Ran 10 (+5) tests in 1.100s (+0.100s)\n' \
            'PASSED (id=99 (+1), id=100 (+2))\n'
        with io.StringIO() as f:
            output.output_summary(
                successful=True, tests=10, tests_delta=5,
                time=1.1, time_delta=0.1,
                values=[('id', 99, 1), ('id', '100', 2)],
                output=f)
            actual = f.getvalue()
            self.assertEqual(expected, actual)

    def test_output_summary_failed(self):
        expected = 'Ran 10 (+5) tests in 1.100s (+0.100s)\n' \
            'FAILED (id=99 (+1), id=100 (+2))\n'
        with io.StringIO() as f:
            output.output_summary(
                successful=False, tests=10, tests_delta=5,
                time=1.1, time_delta=0.1,
                values=[('id', 99, 1), ('id', '100', 2)],
                output=f)
            actual = f.getvalue()
            self.assertEqual(expected, actual)
