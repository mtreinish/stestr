#
# Copyright (c) 2010 Testrepository Contributors
#
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

"""List the tests from a project and show them."""

from io import BytesIO


from stestr import config_file
from stestr import output
from stestr import testcommand


def get_cli_help():
    help_str = ("List the tests for a project. You can use a filter just like"
                "with the run command to see exactly what tests match")
    return help_str + testcommand.testrconf_help


def set_cli_opts(parser):
    pass


def run(args):
    _args = args[0]
    ids = None
    filters = None
    if args[1]:
        filters = args[1]
    conf = config_file.TestrConf(_args.config)
    cmd = conf.get_run_command(_args, ids, filters)
    try:
        cmd.setUp()
        # List tests if the fixture has not already needed to to filter.
        if filters is None:
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
