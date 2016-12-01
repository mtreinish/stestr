# Licensed under either the Apache License, Version 2.0 or the BSD 3-clause
# license at the users choice. A copy of both licenses are available in the
# project source as Apache-2.0 and BSD. You may not use this file except in
# compliance with one of these two licences.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under these licenses is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# license you chose for the specific language governing permissions and
# limitations under that license.

import os

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
        # Handle the results repository
        # TODO(mtreinish): Add a CLI opt to handle different repo types
        repository = file_repo.RepositoryFactory().open(os.getcwd())
        return test_listing_fixture.TestListingFixture(
            test_ids, options, command, listopt, idoption, repository,
            group_regex)

    def get_filter_tags(self):
        if self.parser.has_option('DEFAULT', 'filter_tags'):
            tags = self.parser.get('DEFAULT', 'filter_tags')
        else:
            return set()
        return set([tag.strip() for tag in tags.split()])
