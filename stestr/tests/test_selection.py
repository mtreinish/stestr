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

import re

import mock
import six

from stestr import selection
from stestr.tests import base


class TestSelection(base.TestCase):
    def test_filter_tests_no_filter(self):
        test_list = ['a', 'b', 'c']
        result = selection.filter_tests(None, test_list)
        self.assertEqual(test_list, result)


class TestBlackReader(base.TestCase):
    def test_black_reader(self):
        blacklist_file = six.StringIO()
        for i in range(4):
            blacklist_file.write('fake_regex_%s\n' % i)
            blacklist_file.write('fake_regex_with_note_%s # note\n' % i)
        blacklist_file.seek(0)
        with mock.patch('six.moves.builtins.open',
                        return_value=blacklist_file):
            result = selection.black_reader('fake_path')
        self.assertEqual(2 * 4, len(result))
        note_cnt = 0
        # not assuming ordering, mainly just testing the type
        for r in result:
            self.assertEqual(r[2], [])
            if r[1] == 'note':
                note_cnt += 1
            self.assertIn('search', dir(r[0]))  # like a compiled regexp
        self.assertEqual(note_cnt, 4)


class TestConstructList(base.TestCase):
    def test_simple_re(self):
        test_lists = ['fake_test(scen)[tag,bar])', 'fake_test(scen)[egg,foo])']
        result = selection.construct_list(test_lists, regexes=['foo'])
        self.assertEqual(list(result), ['fake_test(scen)[egg,foo])'])

    def test_simple_black_re(self):
        test_lists = ['fake_test(scen)[tag,bar])', 'fake_test(scen)[egg,foo])']
        result = selection.construct_list(test_lists, black_regex='foo')
        self.assertEqual(list(result), ['fake_test(scen)[tag,bar])'])

    def test_blacklist(self):
        black_list = [(re.compile('foo'), 'foo not liked', [])]
        test_lists = ['fake_test(scen)[tag,bar])', 'fake_test(scen)[egg,foo])']
        with mock.patch('stestr.selection.black_reader',
                        return_value=black_list):
            result = selection.construct_list(test_lists,
                                              blacklist_file='file',
                                              regexes=['fake_test'])
        self.assertEqual(list(result), ['fake_test(scen)[tag,bar])'])

    def test_whitelist(self):
        white_list = 'fake_test1|fake_test2'
        test_lists = ['fake_test1[tg]', 'fake_test2[tg]', 'fake_test3[tg]']
        white_getter = 'stestr.selection._get_regex_from_whitelist_file'
        with mock.patch(white_getter,
                        return_value=white_list):
            result = selection.construct_list(test_lists,
                                              whitelist_file='file')
        self.assertEqual(set(result),
                         set(('fake_test1[tg]', 'fake_test2[tg]')))

    def test_whitelist_blacklist_re(self):
        white_list = 'fake_test1|fake_test2'
        test_lists = ['fake_test1[tg]', 'fake_test2[spam]',
                      'fake_test3[tg,foo]', 'fake_test4[spam]']
        black_list = [(re.compile('spam'), 'spam not liked', [])]
        white_getter = 'stestr.selection._get_regex_from_whitelist_file'
        with mock.patch(white_getter,
                        return_value=white_list):
            with mock.patch('stestr.selection.black_reader',
                            return_value=black_list):
                result = selection.construct_list(test_lists, 'black_file',
                                                  'white_file', ['foo'])
        self.assertEqual(set(result),
                         set(('fake_test1[tg]', 'fake_test3[tg,foo]')))

    def test_overlapping_black_regex(self):

        black_list = [(re.compile('compute.test_keypairs.KeypairsTestV210'),
                       '', []),
                      (re.compile('compute.test_keypairs.KeypairsTestV21'),
                       '', [])]
        test_lists = [
            'compute.test_keypairs.KeypairsTestV210.test_create_keypair',
            'compute.test_keypairs.KeypairsTestV21.test_create_keypair',
            'compute.test_fake.FakeTest.test_fake_test']
        with mock.patch('stestr.selection.black_reader',
                        return_value=black_list):
            result = selection.construct_list(test_lists,
                                              blacklist_file='file',
                                              regexes=['fake_test'])
        self.assertEqual(
            list(result), ['compute.test_fake.FakeTest.test_fake_test'])
