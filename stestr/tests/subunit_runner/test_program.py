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

import unittest

from stestr.subunit_runner import program
from stestr.tests import base


class TestGetById(base.TestCase):
    class CompatibleSuite(unittest.TestSuite):
        def filter_by_ids(self, test_ids):
            return unittest.TestSuite([item for item in self if item.id() in test_ids])

    @classmethod
    def setUpClass(cls):
        cls.test_suite = unittest.TestSuite(
            [cls(name) for name in dir(cls) if name.startswith("test")]
        )

    @classmethod
    def _test_name(cls, name):
        return f"{__name__}.{cls.__name__}.{name}"

    @staticmethod
    def _test_ids(suite):
        return [item.id() for item in suite]

    def test_filter_by_ids_case_no_tests(self):
        test_case = type(self)("test_filter_by_ids_case_no_tests")
        result = program.filter_by_ids(
            test_case,
            ["stestr.tests.test_load.TestLoadCommand.test_empty_with_pretty_out"],
        )
        self.assertEqual([], self._test_ids(result))

    def test_filter_by_ids_case_simple(self):
        name = "test_filter_by_ids_case_simple"
        test_name = self._test_name(name)
        test_case = type(self)(name)
        result = program.filter_by_ids(test_case, [test_name])
        self.assertEqual([test_name], self._test_ids(result))

    def test_filter_by_ids_suite_no_tests(self):
        result = program.filter_by_ids(
            self.test_suite,
            ["stestr.tests.test_load.TestLoadCommand.test_empty_with_pretty_out"],
        )
        self.assertEqual([], self._test_ids(result))

    def test_filter_by_ids_suite_simple(self):
        test_name = self._test_name("test_filter_by_ids_suite_simple")
        result = program.filter_by_ids(self.test_suite, [test_name])
        self.assertEqual([test_name], self._test_ids(result))

    def test_filter_by_ids_suite_preserves_order(self):
        names = (
            "test_filter_by_ids_suite_simple",
            "test_filter_by_ids_suite_preserves_order",
            "test_filter_by_ids_suite_no_tests",
        )
        test_names = [self._test_name(name) for name in names]
        result = program.filter_by_ids(self.test_suite, test_names)
        self.assertEqual(test_names, self._test_ids(result))

    def test_filter_by_ids_suite_no_duplicates(self):
        names = (
            "test_filter_by_ids_suite_simple",
            "test_filter_by_ids_suite_preserves_order",
        )
        expected = [self._test_name(name) for name in names]
        # Create duplicates in reversed order
        test_names = expected + expected[::-1]
        result = program.filter_by_ids(self.test_suite, test_names)
        self.assertEqual(expected, self._test_ids(result))

    def test_filter_by_ids_compatible_no_tests(self):
        test_suite = self.CompatibleSuite(self.test_suite)
        result = program.filter_by_ids(
            test_suite,
            ["stestr.tests.test_load.TestLoadCommand.test_empty_with_pretty_out"],
        )
        self.assertEqual([], self._test_ids(result))

    def test_filter_by_ids_compatible_simple(self):
        test_suite = self.CompatibleSuite(self.test_suite)
        test_name = self._test_name("test_filter_by_ids_compatible_simple")
        result = program.filter_by_ids(test_suite, [test_name])
        self.assertEqual([test_name], self._test_ids(result))

    def test_filter_by_ids_compatible_preserves_order(self):
        test_suite = self.CompatibleSuite(self.test_suite)
        names = (
            "test_filter_by_ids_compatible_simple",
            "test_filter_by_ids_compatible_preserves_order",
            "test_filter_by_ids_compatible_no_tests",
        )
        test_names = [self._test_name(name) for name in names]
        result = program.filter_by_ids(test_suite, test_names)
        self.assertEqual(test_names, self._test_ids(result))

    def test_filter_by_ids_compatible_no_duplicates(self):
        test_suite = self.CompatibleSuite(self.test_suite)
        names = (
            "test_filter_by_ids_compatible_simple",
            "test_filter_by_ids_compatible_preserves_order",
        )
        expected = [self._test_name(name) for name in names]
        # Create duplicates in reversed order
        test_names = expected + expected[::-1]
        result = program.filter_by_ids(test_suite, test_names)
        self.assertEqual(expected, self._test_ids(result))

    def test_filter_by_ids_no_duplicates_preserve_order(self):
        test_suite = unittest.TestSuite(
            [
                self.CompatibleSuite(self.test_suite),
                self.test_suite,
                type(self)("test_filter_by_ids_no_duplicates_preserve_order"),
            ]
        )
        names = (
            "test_filter_by_ids_compatible_simple",
            "test_filter_by_ids_suite_simple",
            "test_filter_by_ids_compatible_preserves_order",
        )
        expected = [self._test_name(name) for name in names]
        # Create duplicates in reversed order
        test_names = expected + expected[::-1]
        result = program.filter_by_ids(test_suite, test_names)
        self.assertEqual(expected, self._test_ids(result))
