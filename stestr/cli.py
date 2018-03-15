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

import sys

from cliff import app
from cliff import commandmanager
from stestr import version

__version__ = version.version_info.version_string_with_vcs()


class StestrCLI(app.App):

    def __init__(self):
        super(StestrCLI, self).__init__(
            description="A parallel Python test runner built around subunit",
            version=__version__,
            command_manager=commandmanager.CommandManager('stestr.cm'),
            deferred_help=True,
            )

    def initialize_app(self, argv):
        self.LOG.debug('initialize_app')

    def prepare_to_run_command(self, cmd):
        self.LOG.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.LOG.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.LOG.debug('got an error: %s', err)

    def build_option_parser(self, description, version, argparse_kwargs=None):
        parser = super(StestrCLI,
                       self).build_option_parser(description, version,
                                                 argparse_kwargs)
        parser = self._set_common_opts(parser)
        return parser

    def _set_common_opts(self, parser):
        parser.add_argument('--user-config', dest='user_config', default=None,
                            help='An optional path to a default user config '
                                 'file if one is not specified ~/.stestr.yaml '
                                 'and ~/.config/stestr.yaml will be tried in '
                                 'that order')
        parser.add_argument('-d', '--here', dest='here',
                            help="Set the directory or url that a command "
                                 "should run from. This affects all default "
                                 "path lookups but does not affect paths "
                                 "supplied to the command.",
                            default=None, type=str)
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
        parser.add_argument('--group-regex', '--group_regex', '-g',
                            dest='group_regex',
                            default=None,
                            help="Set a group regex to use for grouping tests"
                                 " together in the stestr scheduler. If "
                                 "both this and the corresponding config file "
                                 "option are set this value will be used.")

        return parser


def main(argv=sys.argv[1:]):
    cli = StestrCLI()
    return cli.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
