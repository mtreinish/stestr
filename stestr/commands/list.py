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
    """List the tests for a project.

    You can use a filter just like with the run command to see exactly what
    tests match.
    """

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "filters",
            nargs="*",
            default=None,
            help="A list of string regex filters to initially "
            "apply on the test list. Tests that match any of "
            "the regexes will be used. (assuming any other "
            "filtering specified also uses it)",
        )
        parser.add_argument(
            "--exclude-list",
            "-e",
            default=None,
            dest="exclude_list",
            help="Path to an exclusion list file, this file "
            "contains a separate regex exclude on each "
            "newline",
        )
        parser.add_argument(
            "--include-list",
            "-i",
            default=None,
            dest="include_list",
            help="Path to an inclusion list file, this file "
            "contains a separate regex on each newline.",
        )
        parser.add_argument(
            "--exclude-regex",
            "-E",
            default=None,
            dest="exclude_regex",
            help="Test rejection regex. If a test cases name "
            "matches on re.search() operation , "
            "it will be removed from the final test list. "
            "Effectively the exclusion-regexp is added to "
            "exclusion regexp list, but you do need to edit a "
            "file. The exclusion filtering happens after the "
            "initial safe list selection, which by default is "
            "everything.",
        )
        return parser

    def take_action(self, parsed_args):
        args = parsed_args
        filters = parsed_args.filters or None
        return list_command(
            config=self.app_args.config,
            repo_url=self.app_args.repo_url,
            group_regex=self.app_args.group_regex,
            test_path=self.app_args.test_path,
            top_dir=self.app_args.top_dir,
            exclude_list=args.exclude_list,
            include_list=args.include_list,
            exclude_regex=args.exclude_regex,
            filters=filters,
        )


def list_command(
    config=config_file.TestrConf.DEFAULT_CONFIG_FILENAME,
    repo_url=None,
    test_path=None,
    top_dir=None,
    group_regex=None,
    exclude_list=None,
    include_list=None,
    exclude_regex=None,
    filters=None,
    stdout=sys.stdout,
):
    """Print a list of test_ids for a project

    This function will print the test_ids for tests in a project. You can
    filter the output just like with the run command to see exactly what
    will be run.

    :param str config: The path to the stestr config file. Must be a string.
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
    :param str exclude_list: Path to an exclusion list file, this file
        contains a separate regex exclude on each newline.
    :param str include_list: Path to an inclusion list file, this file
        contains a separate regex on each newline.
    :param str exclude_regex: Test rejection regex. If a test cases name
        matches on re.search() operation, it will be removed from the final
        test list.
    :param list filters: A list of string regex filters to initially apply on
        the test list. Tests that match any of the regexes will be used.
        (assuming any other filtering specified also uses it)
    :param file stdout: The output file to write all output to. By default
        this is sys.stdout

    """
    ids = None
    conf = config_file.TestrConf.load_from_file(config)
    cmd = conf.get_run_command(
        regexes=filters,
        repo_url=repo_url,
        group_regex=group_regex,
        exclude_list=exclude_list,
        include_list=include_list,
        exclude_regex=exclude_regex,
        test_path=test_path,
        top_dir=top_dir,
    )
    not_filtered = (
        filters is None
        and include_list is None
        and exclude_list is None
        and exclude_regex is None
    )
    try:
        cmd.setUp()
        # List tests if the fixture has not already needed to to filter.
        if not_filtered:
            ids = cmd.list_tests()
        else:
            ids = cmd.test_ids
        stream = BytesIO()
        for id in ids:
            stream.write(("%s\n" % id).encode("utf8"))
        stream.seek(0)
        output.output_stream(stream, output=stdout)
        return 0
    finally:
        cmd.cleanUp()
