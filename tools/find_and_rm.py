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

import os


def find_and_remove(suffix=".pyc"):
    for root, dirs, files in os.walk("."):
        for file in files:
            target = os.path.join(root, file)
            if os.path.isfile(target) and target.endswith(suffix):
                os.remove(target)


if __name__ == "__main__":
    find_and_remove()
