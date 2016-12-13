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

import argparse
import importlib
import os
import sys
import textwrap

import pbr.version


__version__ = pbr.version.VersionInfo('stestr').version_string()

testrconf_help = textwrap.dedent("""
    Configuring via .testr.conf:
    ---
    [DEFAULT]
    test_command=foo $IDOPTION
    test_id_option=--bar $IDFILE
    ---
    will cause 'testr run' to run 'foo' to execute tests, and
    'testr run --failing' will cause 'foo --bar failing.list ' to be run to
    execute tests. Shell variables are expanded in these commands on platforms
    that have a shell.

    The full list of options and variables for .testr.conf:
    * filter_tags -- a list of tags which should be used to filter test counts.
      This is useful for stripping out non-test results from the subunit stream
      such as Zope test layers. These filtered items are still considered for
      test failures.
    * test_command -- command line to run to execute tests.
    * test_id_option -- the value to substitute into test_command when specific
      test ids should be run.
    * test_id_list_default -- the value to use for $IDLIST when no specific
      test ids are being run.
    * test_list_option -- the option to use to cause the test runner to report
      on the tests it would run, rather than running them. When supplied the
      test_command should output on stdout all the test ids that would have
      been run if every other option and argument was honoured, one per line.
      This is required for parallel testing, and is substituted into $LISTOPT.
    * test_run_concurrency -- Optional call out to establish concurrency.
      Should return one line containing the number of concurrent test runner
      processes to run.
    * instance_provision -- provision one or more test run environments.
      Accepts $INSTANCE_COUNT for the number of instances desired.
    * instance_execute -- execute a test runner process in a given environment.
      Accepts $INSTANCE_ID, $FILES and $COMMAND. Paths in $FILES should be
      synchronised into the test runner environment filesystem. $COMMAND can
      be adjusted if the paths are synched with different names.
    * instance_dispose -- dispose of one or more test running environments.
      Accepts $INSTANCE_IDS.
    * group_regex -- If set group tests by the matched section of the test id.
    * $IDOPTION -- the variable to use to trigger running some specific tests.
    * $IDFILE -- A file created before the test command is run and deleted
      afterwards which contains a list of test ids, one per line. This can
      handle test ids with emedded whitespace.
    * $IDLIST -- A list of the test ids to run, separated by spaces. IDLIST
      defaults to an empty string when no test ids are known and no explicit
      default is provided. This will not handle test ids with spaces.

    See the stestr manual for example .testr.conf files in different
    programming languages.
    """)


class StestrCLI(object):

    commands = ['run', 'list', 'slowest', 'failing', 'stats', 'last', 'init',
                'load']
    command_module = 'stestr.commands.'

    def __init__(self):
        self.parser = self._get_parser()

    def _get_parser(self):
        self.command_dict = {}
        parser = argparse.ArgumentParser()
        self._set_common_opts(parser)
        subparsers = parser.add_subparsers(help='command help')
        for cmd in self.commands:
            self.command_dict[cmd] = importlib.import_module(
                self.command_module + cmd)
            help_str = self.command_dict[cmd].get_cli_help()
            command_parser = subparsers.add_parser(cmd, help=help_str)
            self.command_dict[cmd].set_cli_opts(command_parser)
            command_parser.set_defaults(func=self.command_dict[cmd].run)
        return parser

    def _set_common_opts(self, parser):
        parser.add_argument('-d', '--here', dest='here',
                            help="Set the directory or url that a command "
                                 "should run from. This affects all default "
                                 "path lookups but does not affect paths "
                                 "supplied to the command.",
                            default=None, type=str)
        parser.add_argument("-q", "--quiet", action="store_true",
                            default=False,
                            help="Turn off output other than the primary "
                                 "output for a command and any errors.")
        parser.add_argument('--version', action='version',
                            version=__version__)
        parser.add_argument('--config', '-c', dest='config',
                            default='.testr.conf',
                            help="Set a testr config file to use with this "
                                 "command. If one isn't specified then "
                                 ".testr.conf in the directory that a command "
                                 "is running from is used")


def main():
    cli = StestrCLI()
    args = cli.parser.parse_known_args()
    if args[0].here:
        os.chdir(args[0].here)
    sys.exit(args[0].func(args))


if __name__ == '__main__':
    main()
