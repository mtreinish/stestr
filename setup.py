#!/usr/bin/env python
#
# Copyright (c) 2009, 2010 Testrepository Contributors
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

from setuptools import setup
import email
import os

import testrepository


def get_revno():
    import bzrlib.workingtree
    t = bzrlib.workingtree.WorkingTree.open_containing(__file__)[0]
    return t.branch.revno()


def get_version_from_pkg_info():
    """Get the version from PKG-INFO file if we can."""
    pkg_info_path = os.path.join(os.path.dirname(__file__), 'PKG-INFO')
    try:
        pkg_info_file = open(pkg_info_path, 'r')
    except (IOError, OSError):
        return None
    try:
        pkg_info = email.message_from_file(pkg_info_file)
    except email.MessageError:
        return None
    return pkg_info.get('Version', None)


def get_version():
    """Return the version of testtools that we are building."""
    version = '.'.join(
        str(component) for component in testrepository.__version__[0:3])
    phase = testrepository.__version__[3]
    if phase == 'final':
        return version
    pkg_info_version = get_version_from_pkg_info()
    if pkg_info_version:
        return pkg_info_version
    revno = get_revno()
    if phase == 'alpha':
        # No idea what the next version will be
        return 'next-r%s' % revno
    else:
        # Preserve the version number but give it a revno prefix
        return version + '-r%s' % revno


description = file(os.path.join(os.path.dirname(__file__), 'README.txt'), 'rb').read()


setup(name='testrepository',
      author='Robert Collins',
      author_email='robertc@robertcollins.net',
      url='https://launchpad.net/testrepository',
      description='A repository of test results.',
      long_description=description,
      keywords="subunit unittest testrunner",
      classifiers = [
          'Development Status :: 6 - Mature',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'License :: OSI Approved :: Apache Software License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Topic :: Software Development :: Quality Assurance',
          'Topic :: Software Development :: Testing',
          ],
      scripts=['testr'],
      version=get_version(),
      packages=['testrepository',
        'testrepository.arguments',
        'testrepository.commands',
        'testrepository.repository',
        'testrepository.tests',
        'testrepository.tests.arguments',
        'testrepository.tests.commands',
        'testrepository.tests.repository',
        'testrepository.tests.ui',
        'testrepository.ui',
        ],
      install_requires=[
        'fixtures',
        'python-subunit',
        'testtools',
        ],
      extras_require = dict(
        test=[
            'bzr',
            'pytz',
            'testresources',
            'testscenarios',
            ]
        ),
      )
