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

"""Run a projects tests and load them into stestr."""

import configparser
import errno
import functools
import io
import os
import subprocess
import sys

from cliff import command
import subunit
import testtools

from stestr import bisect_tests
from stestr.commands import load
from stestr.commands import slowest
from stestr import config_file
from stestr import output
from stestr.repository import abstract as repository
from stestr.repository import util
from stestr import results
from stestr.subunit_runner import program
from stestr.subunit_runner import run as subunit_run
from stestr.testlist import parse_list
from stestr import user_config


def _to_int(possible, default=0, out=sys.stderr):
    try:
        i = int(possible)
    except (ValueError, TypeError):
        i = default
        msg = 'Unable to convert "%s" to an integer.  Using %d.\n' % (possible, default)
        out.write(str(msg))
    return i


class Run(command.Command):
    """Run the tests for a project and store them into the repository.

    Without --subunit, the process exit code will be non-zero if the test
    run was not successful. However, with --subunit, the process exit code
    is non-zero only if the subunit stream could not be generated
    successfully. The test results and run status are included in the
    subunit stream, so the stream should be used to determining the result
    of the run instead of the exit code when using the --subunit flag.
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
            "--failing",
            action="store_true",
            default=False,
            help="Run only tests known to be failing.",
        )
        parser.add_argument(
            "--serial",
            action="store_true",
            default=False,
            help="Run tests in a serial process.",
        )
        parser.add_argument(
            "--concurrency",
            action="store",
            default=None,
            type=int,
            help="How many processes to use. The default (0) "
            "autodetects your CPU count.",
        )
        parser.add_argument(
            "--load-list", default=None, help="Only run tests listed in the named file."
        ),
        parser.add_argument(
            "--subunit",
            action="store_true",
            default=False,
            help="Display results in subunit format.",
        )
        parser.add_argument(
            "--until-failure",
            action="store_true",
            default=False,
            help="Repeat the run again and again until " "failure occurs.",
        )
        parser.add_argument(
            "--analyze-isolation",
            action="store_true",
            default=False,
            help="Search the last test run for 2-test test " "isolation interactions.",
        )
        parser.add_argument(
            "--isolated",
            action="store_true",
            default=False,
            help="Run each test id in a separate test runner.",
        )
        parser.add_argument(
            "--worker-file",
            action="store",
            default=None,
            dest="worker_path",
            help="Optional path of a manual worker grouping " "file to use for the run",
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
        parser.add_argument(
            "--no-discover",
            "-n",
            default=None,
            metavar="TEST_ID",
            help="Takes in a single test to bypasses test "
            "discover and just execute the test specified. A "
            "file may be used in place of a test name.",
        )
        parser.add_argument(
            "--pdb",
            default=None,
            metavar="TEST_ID",
            help="Run a single test id with the intent of "
            "using pdb. This does not launch any separate "
            "processes to ensure pdb works as expected. It "
            "will bypass test discovery and just execute the "
            "test specified. A file may be used in place of a "
            "test name.",
        )
        parser.add_argument(
            "--random",
            action="store_true",
            default=False,
            help="Randomize the test order after they are "
            "partitioned into separate workers",
        )
        parser.add_argument(
            "--combine",
            action="store_true",
            default=False,
            help="Combine the results from the test run with "
            "the last run in the repository",
        )
        parser.add_argument(
            "--no-subunit-trace",
            action="store_true",
            default=False,
            help="Disable the default subunit-trace output " "filter",
        )
        parser.add_argument(
            "--force-subunit-trace",
            action="store_true",
            default=False,
            help="Force subunit-trace output regardless of any"
            "other options or config settings",
        )
        parser.add_argument(
            "--color",
            action="store_true",
            default=False,
            help="Enable color output in the subunit-trace "
            "output, if subunit-trace output is enabled. "
            "(this is the default). If subunit-trace is "
            "disable this does nothing.",
        )
        parser.add_argument(
            "--slowest",
            action="store_true",
            default=False,
            help="After the test run, print the slowest " "tests.",
        )
        parser.add_argument(
            "--abbreviate",
            action="store_true",
            dest="abbreviate",
            help="Print one character status for each test",
        )
        parser.add_argument(
            "--suppress-attachments",
            action="store_true",
            dest="suppress_attachments",
            help="If set do not print stdout or stderr "
            "attachment contents on a successful test "
            "execution",
        )
        parser.add_argument(
            "--all-attachments",
            action="store_true",
            dest="all_attachments",
            help="If set print all text attachment contents on"
            " a successful test execution",
        )
        parser.add_argument(
            "--show-binary-attachments",
            action="store_true",
            dest="show_binary_attachments",
            help="If set, show non-text attachments. This is "
            "generally only useful for debug purposes.",
        )
        return parser

    def take_action(self, parsed_args):
        user_conf = user_config.get_user_config(self.app_args.user_config)
        filters = parsed_args.filters
        args = parsed_args
        if args.suppress_attachments and args.all_attachments:
            msg = (
                "The --suppress-attachments and --all-attachments "
                "options are mutually exclusive, you can not use both "
                "at the same time"
            )
            print(msg)
            sys.exit(1)
        if getattr(user_conf, "run", False):
            if not user_conf.run.get("no-subunit-trace"):
                if not args.no_subunit_trace:
                    pretty_out = True
                else:
                    pretty_out = False
            else:
                pretty_out = False

            pretty_out = args.force_subunit_trace or pretty_out
            if args.concurrency is None:
                concurrency = user_conf.run.get("concurrency", 0)
            else:
                concurrency = args.concurrency
            random = args.random or user_conf.run.get("random", False)
            color = args.color or user_conf.run.get("color", False)
            abbreviate = args.abbreviate or user_conf.run.get("abbreviate", False)
            suppress_attachments_conf = user_conf.run.get("suppress-attachments", False)
            all_attachments_conf = user_conf.run.get("all-attachments", False)
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
            pretty_out = args.force_subunit_trace or not args.no_subunit_trace
            concurrency = args.concurrency or 0
            random = args.random
            color = args.color
            abbreviate = args.abbreviate
            suppress_attachments = args.suppress_attachments
            all_attachments = args.all_attachments
        verbose_level = self.app.options.verbose_level
        stdout = open(os.devnull, "w") if verbose_level == 0 else sys.stdout
        # Make sure all (python) callers have provided an int()
        concurrency = _to_int(concurrency)
        if concurrency and concurrency < 0:
            msg = (
                "The provided concurrency value: %s is not valid. An "
                "integer >= 0 must be used.\n" % concurrency
            )
            stdout.write(msg)
            return 2
        result = run_command(
            config=self.app_args.config,
            repo_url=self.app_args.repo_url,
            test_path=self.app_args.test_path,
            top_dir=self.app_args.top_dir,
            group_regex=self.app_args.group_regex,
            failing=args.failing,
            serial=args.serial,
            concurrency=concurrency,
            load_list=args.load_list,
            subunit_out=args.subunit,
            until_failure=args.until_failure,
            analyze_isolation=args.analyze_isolation,
            isolated=args.isolated,
            worker_path=args.worker_path,
            exclude_list=args.exclude_list,
            include_list=args.include_list,
            exclude_regex=args.exclude_regex,
            no_discover=args.no_discover,
            random=random,
            combine=args.combine,
            filters=filters,
            pretty_out=pretty_out,
            color=color,
            stdout=stdout,
            abbreviate=abbreviate,
            suppress_attachments=suppress_attachments,
            all_attachments=all_attachments,
            show_binary_attachments=args.show_binary_attachments,
            pdb=args.pdb,
        )

        # Always output slowest test info if requested, regardless of other
        # test run options
        user_slowest = False
        if getattr(user_conf, "run", False):
            user_slowest = user_conf.run.get("slowest", False)
        if args.slowest or user_slowest:
            slowest.slowest(repo_url=self.app_args.repo_url)

        return result


def _find_failing(repo):
    run = repo.get_failing()
    case = run.get_test()
    ids = []

    def gather_errors(test_dict):
        if test_dict["status"] == "fail":
            ids.append(test_dict["id"])

    result = testtools.StreamToDict(gather_errors)
    result.startTestRun()
    try:
        case.run(result)
    finally:
        result.stopTestRun()
    return ids


def run_command(
    config=config_file.TestrConf.DEFAULT_CONFIG_FILENAME,
    repo_url=None,
    test_path=None,
    top_dir=None,
    group_regex=None,
    failing=False,
    serial=False,
    concurrency=0,
    load_list=None,
    subunit_out=False,
    until_failure=False,
    analyze_isolation=False,
    isolated=False,
    worker_path=None,
    exclude_list=None,
    include_list=None,
    exclude_regex=None,
    no_discover=False,
    random=False,
    combine=False,
    filters=None,
    pretty_out=True,
    color=False,
    stdout=sys.stdout,
    abbreviate=False,
    suppress_attachments=False,
    all_attachments=False,
    show_binary_attachments=True,
    pdb=False,
):
    """Function to execute the run command

    This function implements the run command. It will run the tests specified
    in the parameters based on the provided config file and/or arguments
    specified in the way specified by the arguments. The results will be
    printed to STDOUT and loaded into the repository.

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
    :param bool failing: Run only tests known to be failing.
    :param bool serial: Run tests serially
    :param int concurrency: "How many processes to use. The default (0)
        autodetects your CPU count and uses that.
    :param str load_list: The path to a list of test_ids. If specified only
        tests listed in the named file will be run.
    :param bool subunit_out: Display results in subunit format.
    :param bool until_failure: Repeat the run again and again until failure
        occurs.
    :param bool analyze_isolation: Search the last test run for 2-test test
        isolation interactions.
    :param bool isolated: Run each test id in a separate test runner.
    :param str worker_path: Optional path of a manual worker grouping file
        to use for the run.
    :param str exclude_list: Path to an exclusion list file, this file
        contains a separate regex exclude on each newline.
    :param str include_list: Path to a inclusion list file, this file
        contains a separate regex on each newline.
    :param str exclude_regex: Test rejection regex. If a test cases name
        matches on re.search() operation, it will be removed from the final
        test list.
    :param str no_discover: Takes in a single test_id to bypasses test
        discover and just execute the test specified. A file name may be used
        in place of a test name.
    :param bool random: Randomize the test order after they are partitioned
        into separate workers
    :param bool combine: Combine the results from the test run with the
        last run in the repository
    :param list filters: A list of string regex filters to initially apply on
        the test list. Tests that match any of the regexes will be used.
        (assuming any other filtering specified also uses it)
    :param bool pretty_out: Use the subunit-trace output filter
    :param bool color: Enable colorized output in subunit-trace
    :param file stdout: The file object to write all output to. By default this
        is sys.stdout
    :param bool abbreviate: Use abbreviated output if set true
    :param bool suppress_attachments: When set true attachments subunit_trace
        will not print attachments on successful test execution.
    :param bool all_attachments: When set true subunit_trace will print all
        text attachments on successful test execution.
    :param bool show_binary_attachments: When set to true, subunit_trace will
        print binary attachments in addition to text attachments.
    :param str pdb: Takes in a single test_id to bypasses test
        discover and just execute the test specified without launching any
        additional processes. A file name may be used in place of a test name.

    :return return_code: The exit code for the command. 0 for success and > 0
        for failures.
    :rtype: int
    """
    try:
        repo = util.get_repo_open(repo_url=repo_url)
    # If a repo is not found, and there a stestr config exists just create it
    except repository.RepositoryNotFound:
        if not os.path.isfile(config) and not test_path:
            # If there is no config and no test-path
            if os.path.isfile("tox.ini"):
                tox_conf = configparser.SafeConfigParser()
                tox_conf.read("tox.ini")
                if not tox_conf.has_section("stestr"):
                    msg = (
                        "No file found, --test-path not specified, and "
                        "stestr section not found in tox.ini. Either "
                        "create or specify a .stestr.conf, use "
                        "--test-path, or add an stestr section to the "
                        "tox.ini"
                    )
                    stdout.write(msg)
                    exit(1)
            else:
                msg = (
                    "No config file found and --test-path not specified. "
                    "Either create or specify a .stestr.conf or use "
                    "--test-path "
                )
                stdout.write(msg)
                exit(1)
        try:
            repo = util.get_repo_initialise(repo_url=repo_url)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            repo_path = repo_url or "./stestr"
            stdout.write(
                "The specified repository directory %s already "
                "exists. Please check if the repository already "
                "exists or select a different path\n" % repo_path
            )
            return 1

    combine_id = None
    concurrency = _to_int(concurrency)

    if concurrency and concurrency < 0:
        msg = (
            "The provided concurrency value: %s is not valid. An integer "
            ">= 0 must be used.\n" % concurrency
        )
        stdout.write(msg)
        return 2
    if combine:
        latest_id = repo.latest_id()
        combine_id = str(latest_id)
    if no_discover and pdb:
        msg = (
            "--no-discover and --pdb are mutually exclusive options, "
            "only specify one at a time"
        )
        stdout.write(msg)
        return 2
    if pdb and until_failure:
        msg = (
            "pdb mode does not function with the --until-failure flag, "
            "only specify one at a time"
        )
        stdout.write(msg)
        return 2

    if no_discover:
        ids = no_discover
        if "::" in ids:
            ids = ids.replace("::", ".")
        if ids.find("/") != -1:
            root = ids.replace(".py", "")
            ids = root.replace("/", ".")
        stestr_python = sys.executable
        if os.environ.get("PYTHON"):
            python_bin = os.environ.get("PYTHON")
        elif stestr_python:
            python_bin = stestr_python
        else:
            raise RuntimeError(
                "The Python interpreter was not found and " "PYTHON is not set"
            )
        run_cmd = python_bin + " -m stestr.subunit_runner.run " + ids

        def run_tests():
            run_proc = [
                (
                    "subunit",
                    output.ReturnCodeToSubunit(
                        subprocess.Popen(run_cmd, shell=True, stdout=subprocess.PIPE)
                    ),
                )
            ]
            return load.load(
                in_streams=run_proc,
                subunit_out=subunit_out,
                repo_url=repo_url,
                run_id=combine_id,
                pretty_out=pretty_out,
                color=color,
                stdout=stdout,
                abbreviate=abbreviate,
                suppress_attachments=suppress_attachments,
                all_attachments=all_attachments,
                show_binary_attachments=show_binary_attachments,
            )

        if not until_failure:
            return run_tests()
        else:
            while True:
                result = run_tests()
                # If we're using subunit output we want to make sure to check
                # the result from the repository because load() returns 0
                # always on subunit output
                if subunit:
                    summary = testtools.StreamSummary()
                    last_run = repo.get_latest_run().get_subunit_stream()
                    stream = subunit.ByteStreamToStreamResult(last_run)
                    summary.startTestRun()
                    try:
                        stream.run(summary)
                    finally:
                        summary.stopTestRun()
                    if not results.wasSuccessful(summary):
                        result = 1
                if result:
                    return result

    if pdb:
        ids = pdb
        if "::" in ids:
            ids = ids.replace("::", ".")
        if ids.find("/") != -1:
            root = ids.replace(".py", "")
            ids = root.replace("/", ".")
        runner = subunit_run.SubunitTestRunner
        stream = io.BytesIO()
        program.TestProgram(
            module=None,
            argv=["stestr", ids],
            testRunner=functools.partial(runner, stdout=stream),
        )
        stream.seek(0)
        run_proc = [("subunit", stream)]
        return load.load(
            in_streams=run_proc,
            subunit_out=subunit_out,
            repo_url=repo_url,
            run_id=combine_id,
            pretty_out=pretty_out,
            color=color,
            stdout=stdout,
            abbreviate=abbreviate,
            suppress_attachments=suppress_attachments,
            all_attachments=all_attachments,
            show_binary_attachments=show_binary_attachments,
        )

    if failing or analyze_isolation:
        ids = _find_failing(repo)
    else:
        ids = None
    if load_list:
        list_ids = set()
        # Should perhaps be text.. currently does its own decode.
        with open(load_list, "rb") as list_file:
            list_ids = set(parse_list(list_file.read()))
        if ids is None:
            # Use the supplied list verbatim
            ids = list_ids
        else:
            # We have some already limited set of ids, just reduce to ids
            # that are both failing and listed.
            ids = list_ids.intersection(ids)

    conf = config_file.TestrConf.load_from_file(config)
    if not analyze_isolation:
        cmd = conf.get_run_command(
            ids,
            regexes=filters,
            group_regex=group_regex,
            repo_url=repo_url,
            serial=serial,
            worker_path=worker_path,
            concurrency=concurrency,
            exclude_list=exclude_list,
            include_list=include_list,
            exclude_regex=exclude_regex,
            top_dir=top_dir,
            test_path=test_path,
            randomize=random,
        )
        if isolated:
            result = 0
            cmd.setUp()
            try:
                ids = cmd.list_tests()
            finally:
                cmd.cleanUp()
            for test_id in ids:
                # TODO(mtreinish): add regex
                cmd = conf.get_run_command(
                    [test_id],
                    filters,
                    group_regex=group_regex,
                    repo_url=repo_url,
                    serial=serial,
                    worker_path=worker_path,
                    concurrency=concurrency,
                    exclude_list=exclude_list,
                    include_list=include_list,
                    exclude_regex=exclude_regex,
                    randomize=random,
                    test_path=test_path,
                    top_dir=top_dir,
                )

                run_result = _run_tests(
                    cmd,
                    until_failure,
                    subunit_out=subunit_out,
                    combine_id=combine_id,
                    repo_url=repo_url,
                    pretty_out=pretty_out,
                    color=color,
                    abbreviate=abbreviate,
                    stdout=stdout,
                    suppress_attachments=suppress_attachments,
                    all_attachments=all_attachments,
                    show_binary_attachments=show_binary_attachments,
                )
                if run_result > result:
                    result = run_result
            return result
        else:
            return _run_tests(
                cmd,
                until_failure,
                subunit_out=subunit_out,
                combine_id=combine_id,
                repo_url=repo_url,
                pretty_out=pretty_out,
                color=color,
                stdout=stdout,
                abbreviate=abbreviate,
                suppress_attachments=suppress_attachments,
                all_attachments=all_attachments,
                show_binary_attachments=show_binary_attachments,
            )
    else:
        # Where do we source data about the cause of conflicts.
        latest_run = repo.get_latest_run()
        # Stage one: reduce the list of failing tests (possibly further
        # reduced by testfilters) to eliminate fails-on-own tests.
        spurious_failures = set()
        for test_id in ids:
            # TODO(mtrienish): Add regex
            cmd = conf.get_run_command(
                [test_id],
                group_regex=group_regex,
                repo_url=repo_url,
                serial=serial,
                worker_path=worker_path,
                concurrency=concurrency,
                exclude_list=exclude_list,
                include_list=include_list,
                exclude_regex=exclude_regex,
                randomize=random,
                test_path=test_path,
                top_dir=top_dir,
            )
            if not _run_tests(cmd, until_failure):
                # If the test was filtered, it won't have been run.
                if test_id in repo.get_test_ids(repo.latest_id()):
                    spurious_failures.add(test_id)
                # This is arguably ugly, why not just tell the system that
                # a pass here isn't a real pass? [so that when we find a
                # test that is spuriously failing, we don't forget
                # that it is actually failing.
                # Alternatively, perhaps this is a case for data mining:
                # when a test starts passing, keep a journal, and allow
                # digging back in time to see that it was a failure,
                # what it failed with etc...
                # The current solution is to just let it get marked as
                # a pass temporarily.
        if not spurious_failures:
            # All done.
            return 0
        bisect_runner = bisect_tests.IsolationAnalyzer(
            latest_run,
            conf,
            _run_tests,
            repo,
            test_path=test_path,
            top_dir=top_dir,
            group_regex=group_regex,
            repo_url=repo_url,
            serial=serial,
            concurrency=concurrency,
        )
        # spurious-failure -> cause.
        return bisect_runner.bisect_tests(spurious_failures)


def _run_tests(
    cmd,
    until_failure,
    subunit_out=False,
    combine_id=None,
    repo_url=None,
    pretty_out=True,
    color=False,
    stdout=sys.stdout,
    abbreviate=False,
    suppress_attachments=False,
    all_attachments=False,
    show_binary_attachments=False,
):
    """Run the tests cmd was parameterised with."""
    cmd.setUp()
    try:

        def run_tests():
            run_procs = [
                ("subunit", output.ReturnCodeToSubunit(proc))
                for proc in cmd.run_tests()
            ]
            if not run_procs:
                stdout.write("The specified regex doesn't match with anything")
                return 1
            return load.load(
                (None, None),
                in_streams=run_procs,
                subunit_out=subunit_out,
                repo_url=repo_url,
                run_id=combine_id,
                pretty_out=pretty_out,
                color=color,
                stdout=stdout,
                abbreviate=abbreviate,
                suppress_attachments=suppress_attachments,
                all_attachments=all_attachments,
                show_binary_attachments=show_binary_attachments,
            )

        if not until_failure:
            return run_tests()
        else:
            while True:
                result = run_tests()
                # If we're using subunit output we want to make sure to check
                # the result from the repository because load() returns 0
                # always on subunit output
                if subunit_out:
                    repo = util.get_repo_open(repo_url=repo_url)
                    summary = testtools.StreamSummary()
                    last_run = repo.get_latest_run().get_subunit_stream()
                    stream = subunit.ByteStreamToStreamResult(last_run)
                    summary.startTestRun()
                    try:
                        stream.run(summary)
                    finally:
                        summary.stopTestRun()
                    if not results.wasSuccessful(summary):
                        result = 1
                if result:
                    return result
    finally:
        cmd.cleanUp()
