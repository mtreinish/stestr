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
import sys

import configparser
import tomlkit

from stestr.repository import util
from stestr import test_processor


class TestrConf:
    """Create a TestrConf object to represent a specified config file

    This class is used to represent an stestr config file. Or in the case
    of a tox.ini file the stestr section in the tox.ini file

    :param str config_file: The path to the config file to use
    :param str section: The section to use for the stestr config. By default,
        this is DEFAULT.
    """

    DEFAULT_CONFIG_FILENAME = ".stestr.conf"
    _escape_trailing_backslash_re = re.compile(r"(?<=[^\\])\\$")
    # Set sensible config defaults here, so that override methods are kept DRY
    test_path = None
    top_dir = None
    parallel_class = False
    group_regex = None

    def __init__(self, config_file, section="DEFAULT"):
        self.config_file = str(config_file)
        self.section = section
        if self.config_file.lower().endswith(".toml"):
            self._load_from_toml()
        else:
            self._load_from_configparser()

    def _load_from_configparser(self):
        parser = configparser.ConfigParser()
        parser.read(self.config_file)
        self.test_path = parser.get(self.section, "test_path", fallback=self.test_path)
        self.top_dir = parser.get(self.section, "top_dir", fallback=self.top_dir)
        self.parallel_class = parser.getboolean(
            self.section, "parallel_class", fallback=self.parallel_class
        )
        self.group_regex = parser.get(
            self.section, "group_regex", fallback=self.group_regex
        )

    def _load_from_toml(self):
        with open(self.config_file) as f:
            doc = tomlkit.load(f)
            root = doc["tool"]["stestr"]
            self.test_path = root.get("test_path", self.test_path)
            self.top_dir = root.get("top_dir", self.top_dir)
            self.parallel_class = root.get("parallel_class", self.parallel_class)
            self.group_regex = root.get("group_regex", self.group_regex)

    @classmethod
    def load_from_file(cls, config):
        """Load user-specified values from the various config files.

        ConfigParser (.ini) and TOML are supported.
        If a config file is specified, it is used, and fails on errors.
        If no config file is specified, the order of precedence is as follows:
        - .stestr.conf
        - pyproject.toml with a valid [tool.stestr] section
        - tox.ini with a valid [stestr] section

        :param str config: The pathname of the config file to use
        """
        if os.path.isfile(config) or config != cls.DEFAULT_CONFIG_FILENAME:
            return cls(config)
        try:
            return cls("pyproject.toml")
        except (FileNotFoundError, KeyError):
            return cls("tox.ini", section="stestr")

    def _sanitize_path(self, path):
        if os.sep == "\\":
            # Trailing backslashes have to be escaped. Othwerise, the
            # command we're issuing will be incorrectly interpreted on
            # Windows.
            path = self._escape_trailing_backslash_re.sub(r"\\\\", path)
        return path

    def get_run_command(
        self,
        test_ids=None,
        regexes=None,
        test_path=None,
        top_dir=None,
        group_regex=None,
        repo_url=None,
        serial=False,
        worker_path=None,
        concurrency=0,
        exclude_list=None,
        include_list=None,
        exclude_regex=None,
        randomize=False,
        parallel_class=None,
        dynamic=False,
    ):
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
        :param str repo_url: The url of the repository to use.
        :param bool serial: If tests are run from the returned fixture, they
            will be run serially
        :param str worker_path: Optional path of a manual worker grouping file
            to use for the run.
        :param int concurrency: How many processes to use. The default (0)
            autodetects your CPU count and uses that.
        :param str exclude_list: Path to an exclusion list file, this
            file contains a separate regex exclude on each newline.
        :param str include_list: Path to an inclusion list file, this
            file contains a separate regex on each newline.
        :param str exclude_regex: Test rejection regex. If a test cases name
            matches on re.search() operation, it will be removed from the final
            test list.
        :param bool randomize: Randomize the test order after they are
            partitioned into separate workers
        :param bool parallel_class: Set the flag to group tests together in the
            stestr scheduler by class. If both this and the corresponding
            config file option which includes `group-regex` are set, this value
            will be used.
        :param bool dynamic: Enable dynamic scheduling

        :returns: a TestProcessorFixture object for the specified config file
            and any arguments passed into this function
        :rtype: test_processor.TestProcessorFixture
        """

        if not test_path and not self.test_path:
            sys.exit(
                "No test_path can be found in either the command line "
                "options nor in the specified config file {}.  Please "
                "specify a test path either in the config file or via "
                "the --test-path argument".format(self.config_file)
            )
        if not top_dir and not self.top_dir:
            top_dir = "./"

        test_path = self._sanitize_path(test_path or self.test_path)
        top_dir = self._sanitize_path(top_dir or self.top_dir)

        stestr_python = sys.executable
        # let's try to be explicit, even if it means a longer set of ifs
        if sys.platform == "win32":
            # it may happen, albeit rarely
            if not stestr_python:
                raise RuntimeError("The Python interpreter was not found")
            python = stestr_python
        else:
            if os.environ.get("PYTHON"):
                python = "${PYTHON}"
            elif stestr_python:
                python = stestr_python
            else:
                raise RuntimeError(
                    "The Python interpreter was not found and " "PYTHON is not set"
                )

        # The python binary path may contain whitespaces.
        if os.path.exists('"%s"' % python):
            python = '"%s"' % python

        command = (
            '%s -m stestr.subunit_runner.run discover -t "%s" "%s" '
            "$LISTOPT $IDOPTION" % (python, top_dir, test_path)
        )
        listopt = "--list"
        idoption = "--load-list $IDFILE"
        # If the command contains $IDOPTION read that command from config
        # Use a group regex if one is defined
        if parallel_class or self.parallel_class:
            group_regex = r"([^\.]*\.)*"
        if not group_regex and self.group_regex:
            group_regex = self.group_regex
        if group_regex:

            def group_callback(test_id, regex=re.compile(group_regex)):
                match = regex.match(test_id)
                if match:
                    return match.group(0)

        else:
            group_callback = None
        # Handle the results repository
        repository = util.get_repo_open(repo_url=repo_url)
        return test_processor.TestProcessorFixture(
            test_ids,
            command,
            listopt,
            idoption,
            repository,
            test_filters=regexes,
            group_callback=group_callback,
            serial=serial,
            worker_path=worker_path,
            concurrency=concurrency,
            exclude_list=exclude_list,
            exclude_regex=exclude_regex,
            include_list=include_list,
            randomize=randomize,
            dynamic=dynamic,
        )
