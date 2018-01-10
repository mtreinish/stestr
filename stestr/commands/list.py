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

"""List the tests from a project and show them."""

from io import BytesIO
import sys

from cliff import command

from stestr import config_file
from stestr import output


class List(command.Command):

    def get_description(self):
        help_str = ("List the tests for a project. You can use a filter just "
                    "like with the run command to see exactly what tests "
                    "match")
        return help_str

    def get_parser(self, prog_name):
        parser = super(List, self).get_parser(prog_name)
        parser.add_argument("filters", nargs="*", default=None,
                            help="A list of string regex filters to initially "
                            "apply on the test list. Tests that match any of "
                            "the regexes will be used. (assuming any other "
                            "filtering specified also uses it)")
        parser.add_argument('--blacklist-file', '-b',
                            default=None, dest='blacklist_file',
                            help='Path to a blacklist file, this file '
                                 'contains a separate regex exclude on each '
                                 'newline')
        parser.add_argument('--whitelist-file', '-w',
                            default=None, dest='whitelist_file',
                            help='Path to a whitelist file, this file '
                                 'contains a separate regex on each newline.')
        parser.add_argument('--black-regex', '-B',
                            default=None, dest='black_regex',
                            help='Test rejection regex. If a test cases name '
                            'matches on re.search() operation , '
                            'it will be removed from the final test list. '
                            'Effectively the black-regexp is added to '
                            ' black regexp list, but you do need to edit a '
                            'file. The black filtering happens after the '
                            'initial white selection, which by default is '
                            'everything.')
        return parser

    def take_action(self, parsed_args):
        args = parsed_args
        filters = parsed_args.filters or None
        return list_command(config=self.app_args.config,
                            repo_type=self.app_args.repo_type,
                            repo_url=self.app_args.repo_url,
                            group_regex=self.app_args.group_regex,
                            test_path=self.app_args.test_path,
                            top_dir=self.app_args.top_dir,
                            blacklist_file=args.blacklist_file,
                            whitelist_file=args.whitelist_file,
                            black_regex=args.black_regex,
                            filters=filters)


def list_command(config='.stestr.conf', repo_type='file', repo_url=None,
                 test_path=None, top_dir=None, group_regex=None,
                 blacklist_file=None, whitelist_file=None, black_regex=None,
                 filters=None, stdout=sys.stdout):
    """Print a list of test_ids for a project

    This function will print the test_ids for tests in a project. You can
    filter the output just like with the run command to see exactly what
    will be run.

    :param str config: The path to the stestr config file. Must be a string.
    :param str repo_type: This is the type of repository to use. Valid choices
        are 'file' and 'sql'.
    :param str repo_url: The url of the repository to use.
    :param str test_path: Set the test path to use for unittest discovery.
        If both this and the corresponding config file option are set, this
        value will be used.
    :param str top_dir: The top dir to use for unittest discovery. This takes
        precedence over the value in the config file. (if one is present in
        the config file)
    :param str group_regex: Set a group regex to use for grouping tests
        together in the stestr scheduler. If both this and the corresponding
        config file option are set this value will be used.
    :param str blacklist_file: Path to a blacklist file, this file contains a
        separate regex exclude on each newline.
    :param str whitelist_file: Path to a whitelist file, this file contains a
        separate regex on each newline.
    :param str black_regex: Test rejection regex. If a test cases name matches
        on re.search() operation, it will be removed from the final test list.
    :param list filters: A list of string regex filters to initially apply on
        the test list. Tests that match any of the regexes will be used.
        (assuming any other filtering specified also uses it)
    :param file stdout: The output file to write all output to. By default
        this is sys.stdout

    """
    ids = None
    conf = config_file.TestrConf(config)
    cmd = conf.get_run_command(
        regexes=filters, repo_type=repo_type,
        repo_url=repo_url, group_regex=group_regex,
        blacklist_file=blacklist_file, whitelist_file=whitelist_file,
        black_regex=black_regex, test_path=test_path, top_dir=top_dir)
    not_filtered = filters is None and blacklist_file is None\
        and whitelist_file is None and black_regex is None
    try:
        cmd.setUp()
        # List tests if the fixture has not already needed to to filter.
        if not_filtered:
            ids = cmd.list_tests()
        else:
            ids = cmd.test_ids
        stream = BytesIO()
        for id in ids:
            stream.write(('%s\n' % id).encode('utf8'))
        stream.seek(0)
        output.output_stream(stream, output=stdout)
        return 0
    finally:
        cmd.cleanUp()
