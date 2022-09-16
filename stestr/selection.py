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

import contextlib
import random
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
                print("Invalid regex: %s provided in filters" % f, file=sys.stderr)
                sys.exit(5)
        else:
            _filters.append(f)

    def include(test_id):
        for pred in _filters:
            if pred.search(test_id):
                return True

    return list(filter(include, test_ids))


def exclusion_reader(exclude_list):
    with contextlib.closing(open(exclude_list)) as exclude_file:
        regex_comment_lst = []  # tuple of (regex_compiled, msg, skipped_lst)
        for line in exclude_file:
            raw_line = line.strip()
            split_line = raw_line.split("#")
            # Before the # is the regex
            line_regex = split_line[0].strip()
            if len(split_line) > 1:
                # After the # is a comment
                comment = "".join(split_line[1:]).strip()
            else:
                comment = "Skipped because of regex %s:" % line_regex
            if not line_regex:
                continue
            try:
                regex_comment_lst.append((re.compile(line_regex), comment, []))
            except re.error:
                print(
                    "Invalid regex: %s in provided exclusion list file" % line_regex,
                    file=sys.stderr,
                )
                sys.exit(5)
    return regex_comment_lst


def _get_regex_from_include_list(file_path):
    lines = []
    for line in open(file_path).read().splitlines():
        split_line = line.strip().split("#")
        # Before the # is the regex
        line_regex = split_line[0].strip()
        if line_regex:
            try:
                lines.append(re.compile(line_regex))
            except re.error:
                print(
                    "Invalid regex: %s in provided inclusion_list file" % line_regex,
                    file=sys.stderr,
                )
                sys.exit(5)
    return lines


def construct_list(
    test_ids,
    regexes=None,
    exclude_list=None,
    include_list=None,
    exclude_regex=None,
    randomize=False,
):
    """Filters the discovered test cases

    :param list test_ids: The set of test_ids to be filtered
    :param list regexes: A list of regex filters to apply to the test_ids. The
        output will contain any test_ids which have a re.search() match for any
        of the regexes in this list. If this is None all test_ids will be
        returned
    :param str exclude_list: The path to an exclusion_list file
    :param str include_list: The path to an inclusion_list file
    :param str exclude_regex: regex pattern to exclude tests
    :param str randomize: Randomize the result

    :return: iterable of strings. The strings are full
        test_ids
    :rtype: list
    """

    if not regexes:
        regexes = None  # handle the other false things

    safe_re = None
    if include_list:
        safe_re = _get_regex_from_include_list(include_list)

    if not regexes and safe_re:
        regexes = safe_re
    elif regexes and safe_re:
        regexes += safe_re

    if exclude_list:
        exclude_data = exclusion_reader(exclude_list)
    else:
        exclude_data = None

    if exclude_regex:
        msg = "Skipped because of regexp provided as a command line argument:"
        try:
            record = (re.compile(exclude_regex), msg, [])
        except re.error:
            print(
                "Invalid regex: %s used for exclude_regex" % exclude_regex,
                file=sys.stderr,
            )
            sys.exit(5)
        if exclude_data:
            exclude_data.append(record)
        else:
            exclude_data = [record]

    list_of_test_cases = filter_tests(regexes, test_ids)

    if exclude_data:
        # NOTE(afazekas): We might use a faster logic when the
        # print option is not requested
        for (rex, msg, s_list) in exclude_data:
            # NOTE(mtreinish): In the case of overlapping regex the test case
            # might have already been removed from the set of tests
            list_of_test_cases = [tc for tc in list_of_test_cases if not rex.search(tc)]
    if randomize:
        random.shuffle(list_of_test_cases)

    return list_of_test_cases
