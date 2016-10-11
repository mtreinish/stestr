# Copyright (c) 2016 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse

import pbr.version

import stestr.commands.run
import stestr.commands.load


__version__ = pbr.version.VersionInfo('stestr').version_string()

class StestrCLI(object):

    commands = ['run', 'list', 'slowest', 'failing', 'stats', 'last', 'load']
    command_module = stesttr.commands

    def __init__(self):
        self.parser = self._get_parser()

    def _get_parser(self):
        commands_dict = {}
        parser = argparse.ArgumentParser()
        for cmd in commands:
            command_dict[cmd] = getattr(command_module, cmd)
            command_parser = parser.add_subparsers(cmd)
            command_dict[cmd].set_cli_opts(command_parser)
        

def main():
    cli = StestrCLI(sys.argv)
    args = self.parser.parse(sys.argv)
    args.func(args)


if __name__ == '__main__':
    main()
    
