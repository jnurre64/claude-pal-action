"""Unprivileged fixture MCP shim: forwards data to an external edit broker.

No editing authority lives in this process. The broker applies the phase policy
and framing limits independently. The channel is absent from build/test mounts.
"""
import json
import socket
import sys

LIMIT = 2 * 1024 * 1024


def main():
    with socket.socket(socket.AF_UNIX) as channel:
        channel.settimeout(20)
        channel.connect('/fixture/broker.sock')
        with channel.makefile('rwb') as stream:
            sequence = 0
            while True:
                line = sys.stdin.buffer.readline(LIMIT + 1)
                if not line:
                    return
                if len(line) > LIMIT or not line.endswith(b'\n'):
                    return
                message = json.loads(line)
                if 'id' not in message:
                    continue
                method = message.get('method')
                if method == 'initialize':
                    result = {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}},
                              'serverInfo': {'name': 'fixture-broker', 'version': '0'}}
                elif method == 'tools/list':
                    result = {'tools': [{'name': 'request', 'description': 'Send an edit/read request to the harness broker.',
                        'inputSchema': {'type': 'object', 'properties': {'request': {'type': 'object'}},
                                        'required': ['request'], 'additionalProperties': False}}]}
                elif method == 'tools/call' and message.get('params', {}).get('name') == 'request':
                    arguments = message['params'].get('arguments', {})
                    # Raw worker access to the socket would still meet the same
                    # broker policy. This convenience shim is not an auth boundary.
                    request = {'id': sequence, 'request': arguments.get('request')}
                    sequence += 1
                    wire = (json.dumps(request) + '\n').encode()
                    if len(wire) > LIMIT:
                        return
                    stream.write(wire)
                    stream.flush()
                    reply = stream.readline(LIMIT + 1)
                    if len(reply) > LIMIT or not reply.endswith(b'\n'):
                        return
                    decoded = json.loads(reply)
                    result = {'content': [{'type': 'text', 'text': reply.decode().strip()}],
                              'isError': not decoded.get('ok', False)}
                elif method == 'ping':
                    result = {}
                else:
                    print(json.dumps({'jsonrpc': '2.0', 'id': message['id'],
                                      'error': {'code': -32601, 'message': 'unsupported method'}}), flush=True)
                    continue
                print(json.dumps({'jsonrpc': '2.0', 'id': message['id'], 'result': result}), flush=True)


if __name__ == '__main__':
    main()
