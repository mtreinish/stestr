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


def filter_tests(filters, test_ids):
    """Filter test_ids by the test_filters.

    :return: A list of test ids.
    """
    if filters is None:
        return test_ids
    _filters = list(map(re.compile, filters))

    def include(test_id):
        for pred in _filters:
            if pred.search(test_id):
                return True

    return list(filter(include, test_ids))
