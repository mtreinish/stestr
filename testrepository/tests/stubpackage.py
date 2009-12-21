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

"""A TestResource that provides a temporary python package."""

import os.path
import shutil
import tempfile

from testresources import TestResource

class TempDirResource(TestResource):
    """A temporary directory resource.  

    This resource is never considered dirty.
    """

    def make(self, dependency_resources):
        return tempfile.mkdtemp()

    def clean(self, resource):
        shutil.rmtree(resource, ignore_errors=True)


class StubPackage(object):
    """A temporary package for tests.
    
    :ivar base: The directory containing the package dir.
    """


class StubPackageResource(TestResource):
    
    resources = [('base', TempDirResource())]

    def __init__(self, packagename, modulelist, init=True):
        super(StubPackageResource, self).__init__()
        self.packagename = packagename
        self.modulelist = modulelist
        self.init = init

    def make(self, dependency_resources):
        result = StubPackage()
        base = dependency_resources['base']
        root = os.path.join(base, self.packagename)
        os.mkdir(root)
        init_seen = not self.init
        for modulename, contents in self.modulelist:
            stream = file(os.path.join(root, modulename), 'wb')
            try:
                stream.write(contents)
            finally:
                stream.close()
            if modulename == '__init__.py':
                init_seen = True
        if not init_seen:
            file(os.path.join(root, '__init__.py'), 'wb').close()
        return result
