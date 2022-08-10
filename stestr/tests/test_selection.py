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
import re
from unittest import mock

from stestr import selection
from stestr.tests import base


class TestSelection(base.TestCase):
    def test_filter_tests_no_filter(self):
        test_list = ['a', 'b', 'c']
        result = selection.filter_tests(None, test_list)
        self.assertEqual(test_list, result)

    def test_filter_tests(self):
        test_list = ['a', 'b', 'c']
        result = selection.filter_tests(['a'], test_list)
        self.assertEqual(['a'], result)

    def test_filter_invalid_regex(self):
        test_list = ['a', 'b', 'c']
        with mock.patch('sys.exit', side_effect=ImportError) as mock_exit:
            self.assertRaises(ImportError, selection.filter_tests,
                              ['fake_regex_with_bad_part[The-BAD-part]'],
                              test_list)
            mock_exit.assert_called_once_with(5)


class TestExclusionReader(base.TestCase):

    def test_exclusion_reader(self):
        exclude_list = io.StringIO()
        for i in range(4):
            exclude_list.write('fake_regex_%s\n' % i)
            exclude_list.write('fake_regex_with_note_%s # note\n' % i)
        exclude_list.seek(0)
        with mock.patch('builtins.open',
                        return_value=exclude_list):
            result = selection.exclusion_reader('fake_path')
        self.assertEqual(2 * 4, len(result))
        note_cnt = 0
        # not assuming ordering, mainly just testing the type
        for r in result:
            self.assertEqual(r[2], [])
            if r[1] == 'note':
                note_cnt += 1
            self.assertIn('search', dir(r[0]))  # like a compiled regexp
        self.assertEqual(note_cnt, 4)

    def test_invalid_regex(self):
        exclude_list = io.StringIO()
        exclude_list.write("fake_regex_with_bad_part[The-BAD-part]")
        exclude_list.seek(0)
        with mock.patch('builtins.open',
                        return_value=exclude_list):
            with mock.patch('sys.exit') as mock_exit:
                selection.exclusion_reader('fake_path')
                mock_exit.assert_called_once_with(5)


class TestConstructList(base.TestCase):
    def test_simple_re(self):
        test_lists = ['fake_test(scen)[tag,bar])', 'fake_test(scen)[egg,foo])',
                      'fake_test(necs)[tag,bar])', 'fake_test(necs)[egg,foo])',
                      'fake_test(nnnn)[foo,bar])', 'fake_test(nnnn)[foo,foo])']
        result = selection.construct_list(test_lists, regexes=['foo'])
        # Order must be preserved
        expected = test_lists[:]
        del expected[2]
        del expected[0]
        self.assertEqual(expected, result)

    def test_simple_re_randomized(self):
        test_lists = ['fake_test(scen)[tag,bar])', 'fake_test(scen)[egg,foo])',
                      'fake_test(necs)[tag,bar])', 'fake_test(necs)[egg,foo])',
                      'fake_test(nnnn)[foo,bar])', 'fake_test(nnnn)[foo,foo])']
        result = selection.construct_list(test_lists, regexes=['foo'],
                                          randomize=True)
        expected_names = test_lists[:]
        del expected_names[2]
        del expected_names[0]
        # Order is randomized
        self.assertNotEqual(expected_names, result)
        self.assertEqual(set(expected_names), set(result))

    def test_simple_exclusion_re(self):
        test_lists = ['fake_test(scen)[tag,bar])', 'fake_test(scen)[egg,foo])']
        result = selection.construct_list(test_lists, exclude_regex='foo')
        self.assertEqual(list(result), ['fake_test(scen)[tag,bar])'])

    def test_invalid_exclusion_re(self):
        test_lists = ['fake_test(scen)[tag,bar])', 'fake_test(scen)[egg,foo])']
        invalid_regex = "fake_regex_with_bad_part[The-BAD-part]"
        with mock.patch('sys.exit', side_effect=ImportError) as exit_mock:
            self.assertRaises(ImportError, selection.construct_list,
                              test_lists, exclude_regex=invalid_regex)
            exit_mock.assert_called_once_with(5)

    def test_exclusion_list(self):
        exclude_list = [(re.compile('foo'), 'foo not liked', [])]
        test_lists = ['fake_test(scen)[tag,bar])', 'fake_test(scen)[egg,foo])']
        with mock.patch('stestr.selection.exclusion_reader',
                        return_value=exclude_list):
            result = selection.construct_list(test_lists,
                                              exclude_list='file',
                                              regexes=['fake_test'])
        self.assertEqual(list(result), ['fake_test(scen)[tag,bar])'])

    def test_inclusion_list(self):
        include_list = [re.compile('fake_test1'), re.compile('fake_test2')]
        test_lists = ['fake_test1[tg]', 'fake_test2[tg]', 'fake_test3[tg]']
        include_getter = 'stestr.selection._get_regex_from_include_list'
        with mock.patch(include_getter,
                        return_value=include_list):
            result = selection.construct_list(test_lists,
                                              include_list='file')
        self.assertEqual(set(result),
                         {'fake_test1[tg]', 'fake_test2[tg]'})

    def test_inclusion_list_invalid_regex(self):
        include_list = io.StringIO()
        include_list.write("fake_regex_with_bad_part[The-BAD-part]")
        include_list.seek(0)
        with mock.patch('builtins.open',
                        return_value=include_list):
            with mock.patch('sys.exit') as mock_exit:
                selection._get_regex_from_include_list('fake_path')
                mock_exit.assert_called_once_with(5)

    def test_inclusion_exclusion_list_re(self):
        include_list = [re.compile('fake_test1'), re.compile('fake_test2')]
        test_lists = ['fake_test1[tg]', 'fake_test2[spam]',
                      'fake_test3[tg,foo]', 'fake_test4[spam]']
        exclude_list = [(re.compile('spam'), 'spam not liked', [])]
        include_getter = 'stestr.selection._get_regex_from_include_list'
        with mock.patch(include_getter,
                        return_value=include_list):
            with mock.patch('stestr.selection.exclusion_reader',
                            return_value=exclude_list):
                result = selection.construct_list(
                    test_lists, exclude_list='exclude_file',
                    include_list='include_file', regexes=['foo'])
        self.assertEqual(set(result),
                         {'fake_test1[tg]', 'fake_test3[tg,foo]'})

    def test_overlapping_exclude_regex(self):

        exclude_list = [(re.compile('compute.test_keypairs.KeypairsTestV210'),
                         '', []),
                        (re.compile('compute.test_keypairs.KeypairsTestV21'),
                         '', [])]
        test_lists = [
            'compute.test_keypairs.KeypairsTestV210.test_create_keypair',
            'compute.test_keypairs.KeypairsTestV21.test_create_keypair',
            'compute.test_fake.FakeTest.test_fake_test']
        with mock.patch('stestr.selection.exclusion_reader',
                        return_value=exclude_list):
            result = selection.construct_list(test_lists,
                                              exclude_list='file',
                                              regexes=['fake_test'])
        self.assertEqual(
            list(result), ['compute.test_fake.FakeTest.test_fake_test'])
