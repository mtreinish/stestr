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


import subunit
from testtools import (
    StreamSummary,
    StreamResult,
    )



class SummarizingResult(StreamSummary):

    def __init__(self):
        super(SummarizingResult, self).__init__()

    def startTestRun(self):
        super(SummarizingResult, self).startTestRun()
        self._first_time = None
        self._last_time = None

    def status(self, *args, **kwargs):
        if kwargs.get('timestamp') is not None:
            timestamp = kwargs['timestamp']
            if self._last_time is None:
                self._first_time = timestamp
                self._last_time = timestamp
            if timestamp < self._first_time:
                self._first_time = timestamp
            if timestamp > self._last_time:
                self._last_time = timestamp
        super(SummarizingResult, self).status(*args, **kwargs)

    def get_num_failures(self):
        return len(self.failures) + len(self.errors)

    def get_time_taken(self):
        if None in (self._last_time, self._first_time):
            return None
        return (self._last_time - self._first_time).total_seconds()


class CatFiles(StreamResult):
    """Cat file attachments received to a stream."""
        
    def __init__(self, byte_stream):
        self.stream = subunit.make_stream_binary(byte_stream)
        self.last_file = None

    def status(self, test_id=None, test_status=None, test_tags=None,
        runnable=True, file_name=None, file_bytes=None, eof=False,
        mime_type=None, route_code=None, timestamp=None):
        if file_name is None:
            return
        if self.last_file != file_name:
            self.stream.write(("--- %s ---\n" % file_name).encode('utf8'))
            self.last_file = file_name
        self.stream.write(file_bytes)
        self.stream.flush()
