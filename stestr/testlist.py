# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Handling of lists of tests - common code to --load-list etc."""

import io

try:
    from subunit import ByteStreamToStreamResult as bytestream_to_streamresult
except ImportError:
    bytestream_to_streamresult = None

try:
    from testtools.testresult.doubles import StreamResult as stream_result
except ImportError:
    stream_result = None


def write_list(stream, test_ids):
    """Write test_ids out to stream.

    :param stream: A file-like object.
    :param test_ids: An iterable of test ids.
    """
    # May need utf8 explicitly?
    stream.write(bytes(("\n".join(list(test_ids) + [""])).encode("utf8")))


def parse_list(list_bytes):
    """Parse list_bytes into a list of test ids."""
    return _v1(list_bytes)


def parse_enumeration(enumeration_bytes):
    """Parse enumeration_bytes into a list of test_ids."""
    # If subunit v2 is available, use it.
    if bytestream_to_streamresult is not None:
        return _v2(enumeration_bytes)
    else:
        return _v1(enumeration_bytes)


def _v1(list_bytes):
    return [id.strip() for id in list_bytes.decode("utf8").split("\n") if id.strip()]


def _v2(list_bytes):
    parser = bytestream_to_streamresult(
        io.BytesIO(list_bytes), non_subunit_name="stdout"
    )
    result = stream_result()
    parser.run(result)
    return [event[1] for event in result._events if event[2] == "exists"]
