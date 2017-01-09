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

from stestr.tests import base
from stestr import utils


class TestUtils(base.TestCase):
    def test_cleanup_test_name_defaults(self):
        test_id_no_attrs = 'test.TestThing.test_thing'
        test_id_with_attrs = 'test.TestThing.test_thing[attr1,attr2,att3]'
        test_id_with_scenario = 'test.TestThing.test_thing(mysql)'
        test_id_with_attrs_and_scenario = ('test.TestThing.test_thing[attr]'
                                           '(mysql)')
        result_no_attrs = utils.cleanup_test_name(test_id_no_attrs)
        self.assertEqual(test_id_no_attrs, result_no_attrs)
        result_with_attrs = utils.cleanup_test_name(test_id_with_attrs)
        self.assertEqual(test_id_no_attrs, result_with_attrs)
        result_with_scenario = utils.cleanup_test_name(test_id_with_scenario)
        self.assertEqual(test_id_with_scenario, result_with_scenario)
        result_with_attr_and_scenario = utils.cleanup_test_name(
            test_id_with_attrs_and_scenario)
        self.assertEqual(test_id_with_scenario, result_with_attr_and_scenario)

    def test_cleanup_test_name_leave_attrs(self):
        test_id_no_attrs = 'test.TestThing.test_thing'
        test_id_with_attrs = 'test.TestThing.test_thing[attr1,attr2,att3]'
        test_id_with_scenario = 'test.TestThing.test_thing(mysql)'
        test_id_with_attrs_and_scenario = ('test.TestThing.test_thing[attr]'
                                           '(mysql)')
        result_no_attrs = utils.cleanup_test_name(test_id_no_attrs,
                                                  strip_tags=False)
        self.assertEqual(test_id_no_attrs, result_no_attrs)
        result_with_attrs = utils.cleanup_test_name(test_id_with_attrs,
                                                    strip_tags=False)
        self.assertEqual(test_id_with_attrs, result_with_attrs)
        result_with_scenario = utils.cleanup_test_name(test_id_with_scenario,
                                                       strip_tags=False)
        self.assertEqual(test_id_with_scenario, result_with_scenario)
        result_with_attr_and_scenario = utils.cleanup_test_name(
            test_id_with_attrs_and_scenario, strip_tags=False)
        self.assertEqual(test_id_with_attrs_and_scenario,
                         result_with_attr_and_scenario)

    def test_cleanup_test_name_strip_scenario_and_attrs(self):
        test_id_no_attrs = 'test.TestThing.test_thing'
        test_id_with_attrs = 'test.TestThing.test_thing[attr1,attr2,att3]'
        test_id_with_scenario = 'test.TestThing.test_thing(mysql)'
        test_id_with_attrs_and_scenario = ('test.TestThing.test_thing[attr]'
                                           '(mysql)')
        result_no_attrs = utils.cleanup_test_name(test_id_no_attrs,
                                                  strip_scenarios=True)
        self.assertEqual(test_id_no_attrs, result_no_attrs)
        result_with_attrs = utils.cleanup_test_name(test_id_with_attrs,
                                                    strip_scenarios=True)
        self.assertEqual(test_id_no_attrs, result_with_attrs)
        result_with_scenario = utils.cleanup_test_name(test_id_with_scenario,
                                                       strip_scenarios=True)
        self.assertEqual(test_id_no_attrs, result_with_scenario)
        result_with_attr_and_scenario = utils.cleanup_test_name(
            test_id_with_attrs_and_scenario, strip_scenarios=True)
        self.assertEqual(test_id_no_attrs,
                         result_with_attr_and_scenario)

    def test_cleanup_test_name_strip_scenario(self):
        test_id_no_attrs = 'test.TestThing.test_thing'
        test_id_with_attrs = 'test.TestThing.test_thing[attr1,attr2,att3]'
        test_id_with_scenario = 'test.TestThing.test_thing(mysql)'
        test_id_with_attrs_and_scenario = ('test.TestThing.test_thing[attr]'
                                           '(mysql)')
        result_no_attrs = utils.cleanup_test_name(test_id_no_attrs,
                                                  strip_scenarios=True,
                                                  strip_tags=False)
        self.assertEqual(test_id_no_attrs, result_no_attrs)
        result_with_attrs = utils.cleanup_test_name(test_id_with_attrs,
                                                    strip_scenarios=True,
                                                    strip_tags=False)
        self.assertEqual(test_id_with_attrs, result_with_attrs)
        result_with_scenario = utils.cleanup_test_name(test_id_with_scenario,
                                                       strip_scenarios=True,
                                                       strip_tags=False)
        self.assertEqual(test_id_no_attrs, result_with_scenario)
        result_with_attr_and_scenario = utils.cleanup_test_name(
            test_id_with_attrs_and_scenario, strip_scenarios=True,
            strip_tags=False)
        self.assertEqual('test.TestThing.test_thing[attr]',
                         result_with_attr_and_scenario)
