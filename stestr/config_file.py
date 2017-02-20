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
import sys

from six.moves import configparser

from stestr.repository import util
from stestr import test_listing_fixture


class TestrConf(object):
    """Create a TestrConf object to represent a specified config file

    This class is used to represent an stestr config file. It

    :param str config_file: The path to the config file to use
    """

    def __init__(self, config_file):
        self.parser = configparser.ConfigParser()
        self.parser.read(config_file)
        self.config_file = config_file

    def get_run_command(self, options, test_ids=None, regexes=None):
        """Get a test_listing_fixture.TestListingFixture for this config file

        :param options: A argparse Namespace object of the cli options that
            were used in the invocation of the original CLI command that
            needs a TestListingFixture
        :param list test_ids: an optional list of test_ids to use when running
            tests
        :param list regexes: an optional list of regex strings to use for
            filtering the tests to run. See the test_filters parameter in
            TestListingFixture to see how this is used.
        :returns: a TestListingFixture object for the specified config file and
            any arguments passed into this function
        :rtype: test_listing_fixture.TestListingFixture
        """

        if options.test_path:
            test_path = options.test_path
        elif self.parser.has_option('DEFAULT', 'test_path'):
            test_path = self.parser.get('DEFAULT', 'test_path')
        else:
            print("no test_path can be found in either the command line "
                  "options nor in config file {0}.  Are you running stestr "
                  "from an unexpected location?".format(self.config_file))
            sys.exit(1)
        top_dir = './'
        if options.top_dir:
            top_dir = options.top_dir
        elif self.parser.has_option('DEFAULT', 'top_dir'):
            top_dir = self.parser.get('DEFAULT', 'top_dir')
        command = "${PYTHON:-python} -m subunit.run discover -t" \
                  " %s %s $LISTOPT $IDOPTION" % (top_dir, test_path)
        listopt = "--list"
        idoption = "--load-list $IDFILE"
        # If the command contains $IDOPTION read that command from config
        # Use a group regex if one is defined
        group_regex = None
        if options.group_regex:
            group_regex = options.group_regex
        elif self.parser.has_option('DEFAULT', 'group_regex'):
            group_regex = self.parser.get('DEFAULT', 'group_regex')
        if group_regex:
            def group_callback(test_id, regex=re.compile(group_regex)):
                match = regex.match(test_id)
                if match:
                    return match.group(0)
        else:
            group_callback = None

        # Handle the results repository
        repository = util.get_repo_open(options.repo_type, options.repo_url)
        return test_listing_fixture.TestListingFixture(
            test_ids, options, command, listopt, idoption, repository,
            test_filters=regexes, group_callback=group_callback)
