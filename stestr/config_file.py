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
# under the License

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
        if self.parser.has_option('DEFAULT', 'test_command'):
            command = self.parser.get('DEFAULT', 'test_command')
        else:
            raise ValueError("No test_command option present in the stestr "
                             "config file")
        # If the command contains $IDOPTION read that command from config
        idoption = ''
        if '$IDOPTION' in command:
            if self.parser.has_option('DEFAULT', 'test_id_option'):
                idoption = self.parser.get('DEFAULT', 'test_id_option')
            else:
                raise ValueError("No test_id_option option present in the "
                                 "stestr config file")
        # If the command contains #LISTOPT read that command from config
        listopt = ''
        if '$LISTOPT' in command:
            if self.parser.has_option('DEFAULT', 'test_list_option'):
                listopt = self.parser.get('DEFAULT', 'test_list_option')
            else:
                raise ValueError("No test_list_option option present in the "
                                 " stestr config file")
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

    def get_filter_tags(self):
        if self.parser.has_option('DEFAULT', 'filter_tags'):
            tags = self.parser.get('DEFAULT', 'filter_tags')
        else:
            return set()
        return set([tag.strip() for tag in tags.split()])
