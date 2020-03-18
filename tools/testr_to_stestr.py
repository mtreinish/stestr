#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import configparser
import os
import sys


if not os.path.isfile('.testr.conf'):
    sys.exit("Testr config file not found")

with open('.testr.conf', 'r') as testr_conf_file:
    config = configparser.ConfigParser()
    config.readfp(testr_conf_file)

    test_command = config.get('DEFAULT', 'test_command')
    group_regex = None
    if config.has_option('DEFAULT', 'group_regex'):
        group_regex = config.get('DEFAULT', 'group_regex')

top_dir = None
test_dir = None
for line in test_command.split('\n'):
    if 'subunit.run discover' in line:
        command_parts = line.split(' ')
        top_dir_present = '-t' in line
        for idx, val in enumerate(command_parts):
            if top_dir_present:
                if val == '-t':
                    top_dir = command_parts[idx + 1]
                    test_dir = command_parts[idx + 2]
            else:
                if val == 'discover':
                    test_dir = command_parts[idx + 1]

with open('.stestr.conf', 'w') as stestr_conf_file:
    stestr_conf_file.write('[DEFAULT]\n')
    stestr_conf_file.write('test_path=%s\n' % test_dir)
    if top_dir:
        stestr_conf_file.write('top_dir=%s\n' % top_dir)
    if group_regex:
        stestr_conf_file.write('group_regex=%s\n' % group_regex)
