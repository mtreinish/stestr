import sys

import six
import subunit


class CallWhenProcFinishes(object):
    """Convert a process object to trigger a callback when returncode is set.

    This just wraps the entire object and when the returncode attribute access
    finds a set value, calls the callback.
    """

    def __init__(self, process, callback):
        """Adapt process

        :param process: A subprocess.Popen object.
        :param callback: The process to call when the process completes.
        """
        self._proc = process
        self._callback = callback
        self._done = False

    @property
    def stdin(self):
        return self._proc.stdin

    @property
    def stdout(self):
        return self._proc.stdout

    @property
    def stderr(self):
        return self._proc.stderr

    @property
    def returncode(self):
        result = self._proc.returncode
        if not self._done and result is not None:
            self._done = True
            self._callback()
        return result

    def wait(self):
        return self._proc.wait()


def _iter_streams(input_streams, stream_type, stdin=sys.stdin):
        # Only the first stream declared in a command can be accepted at the
        # moment - as there is only one stdin and alternate streams are not yet
        # configurable in the CLI.
        first_stream_type = input_streams[0]
        if (stream_type != first_stream_type and
            stream_type != first_stream_type[:-1]):
            return
        yield subunit.make_stream_binary(stdin)


def _iter_internal_streams(input_streams, stream_type):
    streams = []
    for in_stream in input_streams:
        if in_stream[0] == stream_type:
            streams.append(in_stream[1])
    for stream_value in streams:
        if getattr(stream_value, 'read', None):
            # NOTE(mtreinish): This is wrong it breaks real streaming. but
            # right now this is needed to workaround the lack of buffers
            yield six.BytesIO(stream_value.read())
        else:
            yield six.BytesIO(stream_value)


def iter_streams(input_streams, stream_type, internal=False):
    """Iterate over all the streams of type stream_type.

    :param stream_type: A simple string such as 'subunit' which matches
        one of the stream types defined for the cmd object this UI is
        being used with.
    :return: A generator of stream objects. stream objects have a read
        method and a close method which behave as for file objects.
    """
    for stream_spec in input_streams:
        if internal:
            _stream_spec = stream_spec[0]
        else:
            _stream_spec = stream_spec

        if '*' in _stream_spec or '?' in _stream_spec or '+' in _stream_spec:
            found = stream_type == _stream_spec[:-1]
        else:
            found = stream_type == _stream_spec
        if found:
            if internal:
                return _iter_internal_streams(input_streams, stream_type)
            return _iter_streams(input_streams, stream_type)
    raise KeyError(stream_type)
