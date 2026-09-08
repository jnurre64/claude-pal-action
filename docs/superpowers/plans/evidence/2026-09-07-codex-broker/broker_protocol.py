"""Bounded serial JSON-lines transport for the experimental edit broker.

Harness-owned streams only. No socket, launcher or worker-controlled root/phase.
The caller must supervise idle time and process lifetime; framing alone cannot
stop a peer that sends no bytes. Oversized/truncated frames close the session.
"""
import json

from prototype import Denied

MAX_FRAME = 2 * 1024 * 1024
MAX_REQUESTS = 32
MAX_SESSION_INPUT = 8 * 1024 * 1024
MAX_SESSION_OUTPUT = 8 * 1024 * 1024
CONTROL_RESERVE = 256


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Denied('duplicate JSON key')
        result[key] = value
    return result


def invalid_constant(value):
    raise Denied('nonfinite JSON value')


def decode(frame):
    try:
        value = json.loads(frame.decode('utf-8'), object_pairs_hook=unique_object,
                           parse_constant=invalid_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise Denied('invalid JSON frame') from None
    if not isinstance(value, dict) or set(value) != {'id', 'request'}:
        raise Denied('id and request required')
    identifier = value['id']
    if type(identifier) is not int or not 0 <= identifier < 2**31:
        raise Denied('id must be a nonnegative 31-bit integer')
    return identifier, value['request']


def serve(reader, writer, broker):
    """Return a terminal reason; denied requests never contain host exceptions."""
    input_bytes = output_bytes = 0
    seen = set()

    def emit(response):
        nonlocal output_bytes
        wire = (json.dumps(response, ensure_ascii=True, allow_nan=False,
                           separators=(',', ':')) + '\n').encode('utf-8')
        if len(wire) > MAX_FRAME:
            wire = b'{"id":null,"ok":false,"error":"response too large"}\n'
        writer.write(wire)
        writer.flush()
        output_bytes += len(wire)

    for _ in range(MAX_REQUESTS):
        # Reserve a full response before allowing any side effect.
        if output_bytes + MAX_FRAME + CONTROL_RESERVE > MAX_SESSION_OUTPUT:
            emit({'id': None, 'ok': False, 'error': 'output budget exhausted'})
            return 'output_limit'
        frame = reader.readline(MAX_FRAME + 1)
        if not frame:
            return 'eof'
        input_bytes += len(frame)
        if len(frame) > MAX_FRAME or not frame.endswith(b'\n'):
            emit({'id': None, 'ok': False, 'error': 'oversized or incomplete frame'})
            return 'frame_limit'
        if input_bytes > MAX_SESSION_INPUT:
            emit({'id': None, 'ok': False, 'error': 'input budget exhausted'})
            return 'input_limit'
        identifier = None
        try:
            identifier, request = decode(frame)
            if identifier in seen:
                raise Denied('replayed request id')
            seen.add(identifier)
            response = broker.request(request)
            emit({'id': identifier, 'ok': True, 'result': response})
        except Denied as error:
            emit({'id': identifier, 'ok': False, 'error': str(error)})
    emit({'id': None, 'ok': False, 'error': 'request budget exhausted'})
    return 'request_limit'
