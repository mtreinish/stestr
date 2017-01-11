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

from stestr import config_file
from stestr import output


def get_cli_help():
    help_str = ("List the tests for a project. You can use a filter just like"
                "with the run command to see exactly what tests match")
    return help_str


def set_cli_opts(parser):
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
                        ' black regexp list, but you do need to edit a file. '
                        'The black filtering happens after the initial '
                        ' white selection, which by default is everything.')


def run(args):
    _args = args[0]
    ids = None
    filters = None
    if args[1]:
        filters = args[1]
    conf = config_file.TestrConf(_args.config)
    cmd = conf.get_run_command(_args, ids, filters)
    not_filtered = filters is None and _args.blacklist_file is None\
        and _args.whitelist_file is None and _args.black_regex is None
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
        output.output_stream(stream)
        return 0
    finally:
        cmd.cleanUp()
