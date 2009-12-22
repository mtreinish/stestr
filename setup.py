#!/usr/bin/env python
#
# Copyright (c) 2009 Testrepository Contributors
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

from distutils.core import setup
import testrepository
version = '.'.join(str(component) for component in testrepository.__version__[0:3])
phase = testrepository.__version__[3]
if phase != 'final':
    import bzrlib.workingtree
    t = bzrlib.workingtree.WorkingTree.open_containing(__file__)[0]
    if phase == 'alpha':
        # No idea what the next version will be
        version = 'next-%s' % t.branch.revno()
    else:
        # Preserve the version number but give it a revno prefix
        version = version + '~%s' % t.branch.revno()

setup(name='testrepository',
      author='Robert Collins',
      author_email='robertc@robertcollins.net',
      url='https://launchpad.net/testrepository',
      description=('A repository of test results.'),
      scripts=['testr'],
      version=version,
      packages=['testrepository',
        'testrepository.commands',
        'testrepository.ui',
        'testrepository.repository',
        ])
