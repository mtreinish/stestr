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
    test_path=./foo/tests
    ---
    will cause 'testr run' to run 'foo' to execute tests, and
    'testr run --failing' will cause 'foo --bar failing.list ' to be run to
    execute tests. Shell variables are expanded in these commands on platforms
    that have a shell.

    The full list of options and variables for .testr.conf:
    * test_path -- the path to use for discovery of the tests
    * top_dir -- optional path to use for the top directory in discovery.
      Defaults to ./ if one is not specified
    * group_regex -- If set group tests by the matched section of the test id.

    See the stestr manual for example .stestr.conf files in different
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
                            default='.stestr.conf',
                            help="Set a stestr config file to use with this "
                                 "command. If one isn't specified then "
                                 ".stestr.conf in the directory that a command"
                                 " is running from is used")


def main():
    cli = StestrCLI()
    args = cli.parser.parse_known_args()
    if args[0].here:
        os.chdir(args[0].here)
    sys.exit(args[0].func(args))


if __name__ == '__main__':
    main()
