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

import pbr.version


__version__ = pbr.version.VersionInfo('stestr').version_string()


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
