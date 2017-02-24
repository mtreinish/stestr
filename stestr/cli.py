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

from stestr import version

__version__ = version.version_info.version_string()


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
        parser.add_argument('--repo-type', '-r', dest='repo_type',
                            choices=['file', 'sql'], default='file',
                            help="Select the repo backend to use")
        parser.add_argument('--repo-url', '-u', dest='repo_url',
                            default=None,
                            help="Set the repo url to use. An acceptable value"
                                 " for this depends on the repository type "
                                 "used.")
        parser.add_argument('--test-path', '-t', dest='test_path',
                            default=None,
                            help="Set the test path to use for unittest "
                                 "discovery. If both this and the "
                                 "corresponding config file option are set, "
                                 "this value will be used.")
        parser.add_argument('--top-dir', dest='top_dir',
                            default=None,
                            help="Set the top dir to use for unittest "
                                 "discovery. If both this and the "
                                 "corresponding config file option are set, "
                                 "this value will be used.")
        parser.add_argument('--group_regex', '-g', dest='group_regex',
                            default=None,
                            help="Set a group regex to use for grouping tests"
                                 " together in the stestr scheduler. If "
                                 "both this and the corresponding config file "
                                 "option are set this value will be used.")


def main():
    cli = StestrCLI()
    args = cli.parser.parse_known_args()
    if args[0].here:
        os.chdir(args[0].here)
    # NOTE(mtreinish): Make sure any subprocesses launch the same version of
    # python being run here
    if 'PYTHON' not in os.environ:
        os.environ['PYTHON'] = sys.executable
    if hasattr(args[0], 'func'):
        sys.exit(args[0].func(args))
    else:
        cli.parser.print_help()
        # NOTE(andreaf) This point is reached only when using Python 3.x.
        # Python 2.x fails with return code 2 in case of no
        # command, so using 2 for consistency
        sys.exit(2)


if __name__ == '__main__':
    main()
