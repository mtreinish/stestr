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
from __future__ import print_function

import contextlib
import re
import sys


def filter_tests(filters, test_ids):
    """Filter test_ids by the test_filters.

    :param list filters: A list of regex filters to apply to the test_ids. The
        output will contain any test_ids which have a re.search() match for any
        of the regexes in this list. If this is None all test_ids will be
        returned
    :param list test_ids: A list of test_ids that will be filtered
    :return: A list of test ids.
    """
    if filters is None:
        return test_ids

    _filters = []
    for f in filters:
        if isinstance(f, str):
            try:
                _filters.append(re.compile(f))
            except re.error:
                print("Invalid regex: %s provided in filters" % f,
                      file=sys.stderr)
                sys.exit(5)
        else:
            _filters.append(f)

    def include(test_id):
        for pred in _filters:
            if pred.search(test_id):
                return True

    return list(filter(include, test_ids))


def exclusion_reader(exclusion_list_file):
    with contextlib.closing(open(exclusion_list_file, 'r')) as exclude_file:
        regex_comment_lst = []  # tuple of (regex_compiled, msg, skipped_lst)
        for line in exclude_file:
            raw_line = line.strip()
            split_line = raw_line.split('#')
            # Before the # is the regex
            line_regex = split_line[0].strip()
            if len(split_line) > 1:
                # After the # is a comment
                comment = ''.join(split_line[1:]).strip()
            else:
                comment = 'Skipped because of regex %s:' % line_regex
            if not line_regex:
                continue
            try:
                regex_comment_lst.append((re.compile(line_regex), comment, []))
            except re.error:
                print("Invalid regex: %s in provided exclusion list file" %
                      line_regex, file=sys.stderr)
                sys.exit(5)
    return regex_comment_lst


def _get_regex_from_inclusion_list_file(file_path):
    lines = []
    for line in open(file_path).read().splitlines():
        split_line = line.strip().split('#')
        # Before the # is the regex
        line_regex = split_line[0].strip()
        if line_regex:
            try:
                lines.append(re.compile(line_regex))
            except re.error:
                print("Invalid regex: %s in provided inclusion_list file" %
                      line_regex, file=sys.stderr)
                sys.exit(5)
    return lines


def construct_list(test_ids, blacklist_file=None, whitelist_file=None,
                   regexes=None, black_regex=None, exclusion_list_file=None,
                   inclusion_list_file=None, exclusion_regex=None):
    """Filters the discovered test cases

    :param list test_ids: The set of test_ids to be filtered
    :param str blacklist_file: DEPRECATED: Replaced by exclusion_list_file
    :param str whitelist_file: DEPRECATED: Replaced by inclusion_list_file
    :param list regexes: A list of regex filters to apply to the test_ids. The
        output will contain any test_ids which have a re.search() match for any
        of the regexes in this list. If this is None all test_ids will be
        returned
    :param str black_regex: DEPRECATED: Replaced by exclusion_regex
    :param str exclusion_list_file: The path to an exclusion_list file
    :param str inclusion_list_file: The path to an inclusion_list file
    :param str exclusion_regex: regex pattern to exclude tests

    :return: iterable of strings. The strings are full
        test_ids
    :rtype: set
    """

    if not regexes:
        regexes = None  # handle the other false things

    safe_re = None
    if inclusion_list_file:
        safe_re = _get_regex_from_inclusion_list_file(inclusion_list_file)
    elif whitelist_file:
        safe_re = _get_regex_from_inclusion_list_file(whitelist_file)

    if not regexes and safe_re:
        regexes = safe_re
    elif regexes and safe_re:
        regexes += safe_re

    if exclusion_list_file:
        exclude_data = exclusion_reader(exclusion_list_file)
    elif blacklist_file:
        exclude_data = exclusion_reader(blacklist_file)
    else:
        exclude_data = None

    if exclusion_regex:
        msg = "Skipped because of regexp provided as a command line argument:"
        try:
            record = (re.compile(exclusion_regex), msg, [])
        except re.error:
            print("Invalid regex: %s used for exclusion_regex" %
                  exclusion_regex, file=sys.stderr)
            sys.exit(5)
        if exclude_data:
            exclude_data.append(record)
        else:
            exclude_data = [record]
    elif black_regex:
        msg = "Skipped because of regexp provided as a command line argument:"
        try:
            record = (re.compile(black_regex), msg, [])
        except re.error:
            print("Invalid regex: %s used for black_regex" % black_regex,
                  file=sys.stderr)
            sys.exit(5)
        if exclude_data:
            exclude_data.append(record)
        else:
            exclude_data = [record]

    list_of_test_cases = filter_tests(regexes, test_ids)
    set_of_test_cases = set(list_of_test_cases)

    if not exclude_data:
        return set_of_test_cases

    # NOTE(afazekas): We might use a faster logic when the
    # print option is not requested
    for (rex, msg, s_list) in exclude_data:
        for test_case in list_of_test_cases:
            if rex.search(test_case):
                # NOTE(mtreinish): In the case of overlapping regex the test
                # case might have already been removed from the set of tests
                if test_case in set_of_test_cases:
                    set_of_test_cases.remove(test_case)
                    s_list.append(test_case)

    return set_of_test_cases
