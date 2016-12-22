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

import os
import re

from six.moves import configparser

from stestr.repository import file as file_repo
from stestr import test_listing_fixture


class TestrConf(object):

    def __init__(self, config_file):
        self.parser = configparser.ConfigParser()
        self.parser.read(config_file)

    def get_run_command(self, options, test_ids=None, regexes=None):
        if self.parser.has_option('DEFAULT', 'test_path'):
            test_path = self.parser.get('DEFAULT', 'test_path')
        top_dir = './'
        if self.parser.has_option('DEFAULT', 'top_dir'):
            top_dir = self.parser.get('DEFAULT', 'top_dir')
        command = "${PYTHON:-python} -m subunit.run discover -t" \
                  " %s %s $LISTOPT $IDOPTION" % (top_dir, test_path)
        listopt = "--list"
        idoption = "--load-list $IDFILE"
        # If the command contains $IDOPTION read that command from config
        # Use a group regex if one is defined
        group_regex = None
        if self.parser.has_option('DEFAULT', 'group_regex'):
            group_regex = self.parser.get('DEFAULT', 'group_regex')
            if group_regex:
                def group_callback(test_id, regex=re.compile(group_regex)):
                    match = regex.match(test_id)
                    if match:
                        return match.group(0)
        else:
            group_callback = None

        # Handle the results repository
        # TODO(mtreinish): Add a CLI opt to handle different repo types
        repository = file_repo.RepositoryFactory().open(os.getcwd())
        return test_listing_fixture.TestListingFixture(
            test_ids, options, command, listopt, idoption, repository,
            test_filters=regexes, group_callback=group_callback)
