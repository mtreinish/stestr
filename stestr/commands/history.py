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

"""Interact with the run history in a repository."""

import functools
import sys

from cliff import command
from cliff import lister
import subunit
import testtools

from stestr import output
from stestr.repository import abstract
from stestr.repository import util
from stestr import results
from stestr import subunit_trace
from stestr import user_config


class HistoryList(lister.Lister):
    """List the the run history in a repository."""

    def get_parser(self, prog_name):
        list_parser = super().get_parser(prog_name)
        list_parser.add_argument('--show-metadata', '-m', action='store_true',
                                 help="Show metadata associated with runs in "
                                      "output table")
        return list_parser

    def take_action(self, parsed_args):
        args = parsed_args
        user_conf = user_config.get_user_config(self.app_args.user_config)
        show_metadata = args.show_metadata
        if getattr(user_conf, 'history_list', False):
            if user_conf.history_show.get('show-metadata',
                                          None) is not None:
                show_metadata = args.show_metadata
        return history_list(repo_url=self.app_args.repo_url,
                            show_metadata=show_metadata)


class HistoryShow(command.Command):
    """Show the contents of a single run in the history"""

    def get_parser(self, prog_name):
        show_parser = super().get_parser(prog_name)
        show_parser.add_argument(
            "--subunit", action="store_true",
            default=False, help="Show output as a subunit stream.")
        show_parser.add_argument("--no-subunit-trace", action='store_true',
                                 default=False,
                                 help="Disable output with the subunit-trace "
                                      "output filter")
        show_parser.add_argument('--force-subunit-trace', action='store_true',
                                 default=False,
                                 help='Force subunit-trace output regardless '
                                      'of any other options or config '
                                      'settings')
        show_parser.add_argument('--color', action='store_true', default=False,
                                 help='Enable color output in the '
                                      'subunit-trace output, if subunit-trace '
                                      'output is enabled. (this is the '
                                      'default). If subunit-trace is disabled '
                                      'this does nothing.')
        show_parser.add_argument('--suppress-attachments', action='store_true',
                                 dest='suppress_attachments',
                                 help='If set do not print stdout or stderr '
                                      'attachment contents on a successful '
                                      'test execution')
        show_parser.add_argument('--all-attachments', action='store_true',
                                 dest='all_attachments',
                                 help='If set print all text attachment '
                                      'contents on a successful test '
                                      'execution')
        show_parser.add_argument('--show-binary-attachments',
                                 action='store_true',
                                 dest='show_binary_attachments',
                                 help='If set, show non-text attachments. '
                                      'This is generally only useful for '
                                      'debug purposes.')
        show_parser.add_argument('run_id', nargs='?', default=None,
                                 help='The run id to show the results from '
                                      'if not specified the last run will be '
                                      'shown (which is equivalent to '
                                      "'stestr last')")
        return show_parser

    def take_action(self, parsed_args):
        args = parsed_args
        user_conf = user_config.get_user_config(self.app_args.user_config)
        if args.suppress_attachments and args.all_attachments:
            msg = ("The --suppress-attachments and --all-attachments "
                   "options are mutually exclusive, you can not use both "
                   "at the same time")
            print(msg)
            sys.exit(1)
        if getattr(user_conf, 'history_show', False):
            if not user_conf.history_show.get('no-subunit-trace'):
                if not args.no_subunit_trace:
                    pretty_out = True
                else:
                    pretty_out = False
            else:
                pretty_out = False
            pretty_out = args.force_subunit_trace or pretty_out
            color = args.color or user_conf.history_show.get('color',
                                                             False)
            suppress_attachments_conf = user_conf.history_show.get(
                'suppress-attachments', False)
            all_attachments_conf = user_conf.history_show.get(
                'all-attachments', False)
            if not args.suppress_attachments and not args.all_attachments:
                suppress_attachments = suppress_attachments_conf
                all_attachments = all_attachments_conf
            elif args.suppress_attachments:
                all_attachments = False
                suppress_attachments = args.suppress_attachments
            elif args.all_attachments:
                suppress_attachments = False
                all_attachments = args.all_attachments
        else:
            pretty_out = args.force_subunit_trace or not \
                args.no_subunit_trace
            color = args.color
            suppress_attachments = args.suppress_attachments
            all_attachments = args.all_attachments
        return history_show(
            args.run_id,
            repo_url=self.app_args.repo_url,
            subunit_out=args.subunit,
            pretty_out=pretty_out, color=color,
            suppress_attachments=suppress_attachments,
            all_attachments=all_attachments,
            show_binary_attachments=args.show_binary_attachments)


class HistoryRemove(command.Command):
    """Remove a run from the history"""

    def get_parser(self, prog_name):
        remove_parser = super().get_parser(prog_name)
        remove_parser.add_argument('run_id',
                                   help='The run id to remove from the '
                                        'repository. Also the string "all" '
                                        'can be used to remove all runs in '
                                        'the history')
        return remove_parser

    def take_action(self, parsed_args):
        args = parsed_args
        history_remove(args.run_id,
                       repo_url=self.app_args.repo_url)


start_times = None
stop_times = None


def _get_run_details(stream_file, stdout):
    stream = subunit.ByteStreamToStreamResult(stream_file,
                                              non_subunit_name='stdout')
    global start_times
    global stop_times
    start_times = []
    stop_times = []

    def collect_data(stream, test):
        global start_times
        global stop_times
        start_times.append(test['timestamps'][0])
        stop_times.append(test['timestamps'][1])

    outcomes = testtools.StreamToDict(functools.partial(collect_data, stdout))
    summary = testtools.StreamSummary()
    result = testtools.CopyStreamResult([outcomes, summary])
    result = testtools.StreamResultRouter(result)
    cat = subunit.test_results.CatFiles(stdout)
    result.add_rule(cat, 'test_id', test_id=None)
    result.startTestRun()
    try:
        stream.run(result)
    finally:
        result.stopTestRun()
    successful = results.wasSuccessful(summary)
    if start_times and stop_times:
        start_time = min(start_times)
        stop_time = max(stop_times)
        run_time = subunit_trace.get_duration([start_time, stop_time])
    else:
        run_time = '---'
        successful = '---'
        start_time = '---'
    return {'passed': successful, 'runtime': run_time, 'start': start_time}


def history_list(repo_url=None, show_metadata=False,
                 stdout=sys.stdout):
    """Show a list of runs in a repository

    Note this function depends on the cwd for the repository if `repo_url` is
    not specified it will use the repository located at CWD/.stestr

    :param str repo_url: The url of the repository to use.
    :param bool show_metadata: If set to ``True`` a column with any metadata
        for a run will be included in the output.
    :param file stdout: The output file to write all output to. By default
         this is sys.stdout

    :return return_code: The exit code for the command. 0 for success and > 0
        for failures.
    :rtype: int
    """

    field_names = ()
    if show_metadata:
        field_names = ('Run ID', 'Passed', 'Runtime', 'Date', 'Metadata')
    else:
        field_names = ('Run ID', 'Passed', 'Runtime', 'Date')
    try:
        repo = util.get_repo_open('file', repo_url)
    except abstract.RepositoryNotFound as e:
        stdout.write(str(e) + '\n')
        return 1
    try:
        run_ids = repo.get_run_ids()
    except KeyError as e:
        stdout.write(str(e) + '\n')
        return 1
    rows = []
    for run_id in run_ids:
        run = repo.get_test_run(run_id)
        stream = run.get_subunit_stream()
        data = _get_run_details(stream, stdout)
        if show_metadata:
            rows.append((run_id, data['passed'], data['runtime'],
                         data['start'], run.get_metadata()))
        else:
            rows.append((run_id, data['passed'], data['runtime'],
                         data['start']))

    return (field_names, rows)


def history_show(run_id, repo_url=None, subunit_out=False,
                 pretty_out=True, color=False, stdout=sys.stdout,
                 suppress_attachments=False, all_attachments=False,
                 show_binary_attachments=False):
    """Show a run loaded into a repository

    This function will print the results from the last run in the repository
    to STDOUT. It can optionally print the subunit stream for the last run
    to STDOUT if the ``subunit`` option is set to true.

    Note this function depends on the cwd for the repository if `repo_url` is
    not specified it will use the repository located at CWD/.stestr

    :param str run_id: The run id to show
    :param str repo_url: The url of the repository to use.
    :param bool subunit_out: Show output as a subunit stream.
    :param pretty_out: Use the subunit-trace output filter.
    :param color: Enable colorized output with the subunit-trace output filter.
    :param bool subunit: Show output as a subunit stream.
    :param file stdout: The output file to write all output to. By default
         this is sys.stdout
    :param bool suppress_attachments: When set true attachments subunit_trace
        will not print attachments on successful test execution.
    :param bool all_attachments: When set true subunit_trace will print all
        text attachments on successful test execution.
    :param bool show_binary_attachments: When set to true, subunit_trace will
        print binary attachments in addition to text attachments.

    :return return_code: The exit code for the command. 0 for success and > 0
        for failures.
    :rtype: int
    """
    try:
        repo = util.get_repo_open('file', repo_url)
    except abstract.RepositoryNotFound as e:
        stdout.write(str(e) + '\n')
        return 1
    try:
        if run_id:
            run = repo.get_test_run(run_id)
        else:
            run = repo.get_latest_run()
    except KeyError as e:
        stdout.write(str(e) + '\n')
        return 1

    if subunit_out:
        stream = run.get_subunit_stream()
        output.output_stream(stream, output=stdout)
        # Exits 0 if we successfully wrote the stream.
        return 0
    case = run.get_test()
    try:
        if run_id:
            previous_run = int(run_id) - 1
        else:
            previous_run = repo.get_test_run(repo.latest_id() - 1)
    except KeyError:
        previous_run = None
    failed = False
    if not pretty_out:
        output_result = results.CLITestResult(run.get_id, stdout,
                                              previous_run)
        summary = output_result.get_summary()
        output_result.startTestRun()
        try:
            case.run(output_result)
        finally:
            output_result.stopTestRun()
        failed = not results.wasSuccessful(summary)
    else:
        stream = run.get_subunit_stream()
        failed = subunit_trace.trace(
            stream, stdout, post_fails=True, color=color,
            suppress_attachments=suppress_attachments,
            all_attachments=all_attachments,
            show_binary_attachments=show_binary_attachments)
    if failed:
        return 1
    else:
        return 0


def history_remove(run_id, repo_url=None, stdout=sys.stdout):
    """Remove a run from a repository

    Note this function depends on the cwd for the repository if `repo_url` is
    not specified it will use the repository located at CWD/.stestr

    :param str run_id: The run id to remove from the repository. Also, can be
        set to ``all`` which will remove all runs from the repository.
    :param str repo_url: The url of the repository to use.
    :param file stdout: The output file to write all output to. By default
         this is sys.stdout

    :return return_code: The exit code for the command. 0 for success and > 0
        for failures.
    :rtype: int
    """
    try:
        repo = util.get_repo_open('file', repo_url)
    except abstract.RepositoryNotFound as e:
        stdout.write(str(e) + '\n')
        return 1
    if run_id == 'all':
        try:
            run_ids = repo.get_run_ids()
        except KeyError as e:
            stdout.write(str(e) + '\n')
            return 1
        for run_id in run_ids:
            repo.remove_run_id(run_id)
    else:
        try:
            repo.remove_run_id(run_id)
        except KeyError as e:
            stdout.write(str(e) + '\n')
            return 1
    return 0
