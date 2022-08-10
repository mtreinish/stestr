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
from unittest import mock

from stestr.commands import run
from stestr.tests import base


class TestRunCommand(base.TestCase):
    def test_to_int_positive_int(self):
        self.assertEqual(29, run._to_int(29))

    def test_to_int_positive_int_str(self):
        self.assertEqual(42, run._to_int('42'))

    def test_to_int_negative_int(self):
        self.assertEqual(-2, run._to_int(-2))

    def test_to_int_negative_int_str(self):
        self.assertEqual(-45, run._to_int('-45'))

    def test_to_int_invalid_str(self):
        fake_stderr = io.StringIO()
        out = run._to_int('I am not an int', out=fake_stderr)
        expected = (
            'Unable to convert "I am not an int" to an integer.  '
            'Using 0.\n')
        self.assertEqual(fake_stderr.getvalue(), expected)
        self.assertEqual(0, out)

    def test_to_int_none(self):
        fake_stderr = io.StringIO()
        out = run._to_int(None, out=fake_stderr)
        expected = (
            'Unable to convert "None" to an integer.  '
            'Using 0.\n')
        self.assertEqual(fake_stderr.getvalue(), expected)
        self.assertEqual(0, out)


class TestLoadListAndFilter(base.TestCase):
    @mock.patch('builtins.open', side_effect=FileNotFoundError)
    def test__load_list_and_filter_file_not_found(self, mock_open):
        filename = 'my_filename'
        self.assertRaises(FileNotFoundError,
                          run._load_list_and_filter, filename, None)

        mock_open.assert_called_once_with(filename, 'rb')
        mock_open.return_value.__enter__.return_value.read.assert_not_called()

    @mock.patch('builtins.open')
    def test__load_list_and_filter_empty_file(self, mock_open):
        mock_read = mock_open.return_value.__enter__.return_value.read
        mock_read.return_value = b''
        filename = 'my_filename'
        res = run._load_list_and_filter(filename, ['mytest'])
        self.assertListEqual([], res)
        mock_open.assert_called_once_with(filename, 'rb')
        mock_read.assert_called_once_with()

    @mock.patch('builtins.open')
    def test__load_list_and_filter_no_filter(self, mock_open):
        mock_read = mock_open.return_value.__enter__.return_value.read
        tests = ['test1', 'tests2', 'test3']
        mock_read.return_value = '\n'.join(tests).encode()
        filename = 'my_filename'

        res = run._load_list_and_filter(filename, None)

        self.assertListEqual(tests, res)
        mock_open.assert_called_once_with(filename, 'rb')
        mock_read.assert_called_once_with()

    @mock.patch('builtins.open')
    def test__load_list_and_filter_filter(self, mock_open):
        mock_read = mock_open.return_value.__enter__.return_value.read
        tests = ['test1', 'tests2', 'test3']
        mock_read.return_value = '\n'.join(tests).encode()
        filename = 'my_filename'

        # Failed tests in different order from list and with additional ids to
        # confirm that order from list is preserved and only elements from list
        # are returned
        failed_tests = ['test4', 'test3', 'test1']
        expected = ['test1', 'test3']
        res = run._load_list_and_filter(filename, failed_tests)

        self.assertListEqual(expected, res)
        mock_open.assert_called_once_with(filename, 'rb')
        mock_read.assert_called_once_with()
