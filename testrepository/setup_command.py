#
# Copyright 2013 Hewlett-Packard Development Company, L.P.
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

"""
setuptools/distutils commands to run testr via setup.py
"""

from distutils import cmd
import distutils.errors
import os
import sys

from testrepository import commands


class Testr(cmd.Command):

    description = "Run unit tests using testr"

    user_options = [
        ('testr-args=', 't', "Run 'testr' with these args")
    ]
    print_slowest = True

    def _run_testr(self, *args):
        commands.run_argv([sys.argv[0]] + list(args),
                          sys.stdin, sys.stdout, sys.stderr)

    def initialize_options(self):
        self.testr_args = None

    def finalize_options(self):
        if self.testr_args is None:
            self.testr_args = []
        else:
            self.testr_args = self.testr_args.split()

    def run(self):
        """Set up testr repo, then run testr"""
        if not os.path.isdir(".testrepository"):
            self._run_testr("init")

        testr_ret = self._run_testr("run", "--parallel", *self.testr_args)
        if testr_ret:
            raise distutils.errors.DistutilsError("testr failed")
        if self.print_slowest:
            print "Slowest Tests"
            self._run_testr("slowest")


class Coverage(Testr):

    print_slowest = False
    user_options = Testr.user_options + [
        ('omit=', 'o', 'Files to omit from coverage calculations'),
    ]

    def initialize_options(self):
        Testr.initialize_options(self)
        self.omit = ""

    def finalize_options(self):
        Testr.finalize_options(self)
        if self.omit:
            self.omit = "--omit=%s" % self.omit

    def run(self):
        package = self.distribution.get_name()
        if package.startswith('python-'):
            package = package[7:]
        options = "--source %s --parallel-mode" % package
        os.environ['PYTHON'] = ("coverage run --source %s" % options)
        Testr.run(self)
        os.system("coverage combine")
        os.system("coverage html -d ./cover %s" % self.omit)
