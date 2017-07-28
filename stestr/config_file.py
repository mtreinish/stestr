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
from stestr import test_processor


class TestrConf(object):
    """Create a TestrConf object to represent a specified config file

    This class is used to represent an stestr config file. It

    :param str config_file: The path to the config file to use
    """

    def __init__(self, config_file):
        self.parser = configparser.ConfigParser()
        self.parser.read(config_file)
        self.config_file = config_file

    def get_run_command(self, test_ids=None, regexes=None,
                        test_path=None, top_dir=None, group_regex=None,
                        repo_type='file', repo_url=None,
                        serial=False, worker_path=None,
                        concurrency=0, blacklist_file=None,
                        whitelist_file=None, black_regex=None,
                        randomize=False):
        """Get a test_processor.TestProcessorFixture for this config file

        Any parameters about running tests will be used for initialize the
        output fixture so the settings are correct when that fixture is used
        to run tests. Parameters will take precedence over values in the config
        file.

        :param options: A argparse Namespace object of the cli options that
            were used in the invocation of the original CLI command that
            needs a TestProcessorFixture
        :param list test_ids: an optional list of test_ids to use when running
            tests
        :param list regexes: an optional list of regex strings to use for
            filtering the tests to run. See the test_filters parameter in
            TestProcessorFixture to see how this is used.
        :param str test_path: Set the test path to use for unittest discovery.
            If both this and the corresponding config file option are set, this
            value will be used.
        :param str top_dir: The top dir to use for unittest discovery. This
            takes precedence over the value in the config file. (if one is
            present in the config file)
        :param str group_regex: Set a group regex to use for grouping tests
            together in the stestr scheduler. If both this and the
            corresponding config file option are set this value will be used.
        :param str repo_type: This is the type of repository to use. Valid
            choices are 'file' and 'sql'.
        :param str repo_url: The url of the repository to use.
        :param bool serial: If tests are run from the returned fixture, they
            will be run serially
        :param str worker_path: Optional path of a manual worker grouping file
            to use for the run.
        :param int concurrency: How many processes to use. The default (0)
            autodetects your CPU count and uses that.
        :param str blacklist_file: Path to a blacklist file, this file contains
            a separate regex exclude on each newline.
        :param str whitelist_file: Path to a whitelist file, this file contains
            a separate regex on each newline.
        :param str black_regex: Test rejection regex. If a test cases name
            matches on re.search() operation, it will be removed from the final
            test list.
        :param bool randomize: Randomize the test order after they are
            partitioned into separate workers

        :returns: a TestProcessorFixture object for the specified config file
            and any arguments passed into this function
        :rtype: test_processor.TestProcessorFixture
        """

        if not test_path and self.parser.has_option('DEFAULT', 'test_path'):
            test_path = self.parser.get('DEFAULT', 'test_path')
        elif not test_path:
            print("No test_path can be found in either the command line "
                  "options nor in the specified config file {0}.  Please "
                  "specify a test path either in the config file or via the "
                  "--test-path argument".format(self.config_file))
            sys.exit(1)
        if not top_dir and self.parser.has_option('DEFAULT', 'top_dir'):
            top_dir = self.parser.get('DEFAULT', 'top_dir')
        elif not top_dir:
            top_dir = './'

        python = 'python' if sys.platform == 'win32' else '${PYTHON:-python}'
        command = "%s -m subunit.run discover -t" \
                  " %s %s $LISTOPT $IDOPTION" % (python, top_dir, test_path)
        listopt = "--list"
        idoption = "--load-list $IDFILE"
        # If the command contains $IDOPTION read that command from config
        # Use a group regex if one is defined
        if not group_regex and self.parser.has_option('DEFAULT',
                                                      'group_regex'):
            group_regex = self.parser.get('DEFAULT', 'group_regex')
        if group_regex:
            def group_callback(test_id, regex=re.compile(group_regex)):
                match = regex.match(test_id)
                if match:
                    return match.group(0)
        else:
            group_callback = None

        # Handle the results repository
        repository = util.get_repo_open(repo_type, repo_url)
        return test_processor.TestProcessorFixture(
            test_ids, command, listopt, idoption, repository,
            test_filters=regexes, group_callback=group_callback, serial=serial,
            worker_path=worker_path, concurrency=concurrency,
            blacklist_file=blacklist_file, black_regex=black_regex,
            whitelist_file=whitelist_file, randomize=randomize)
