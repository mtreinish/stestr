#!/usr/bin/env python

import os
import sys

import six

if not os.path.isfile('.testr.conf'):
    print("Testr config file not found")
    sys.exit(1)

testr_conf_file = open('.testr.conf', 'r')
config = six.moves.configparser.ConfigParser()
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
                    test_dir = command_parts[idx + 2]

stestr_conf_file = open('.stestr.conf', 'w')
stestr_conf_file.write('[DEFAULT]\n')
stestr_conf_file.write('test_path=%s\n' % test_dir)
if top_dir:
    stestr_conf_file.write('top_dir=%s\n' % top_dir)
if group_regex:
    stestr_conf_file.write('group_regex=%s\n' % group_regex)
stestr_conf_file.close()
