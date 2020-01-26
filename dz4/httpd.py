import os
import socket
import signal
import logging
import asyncio
import mimetypes
import selectors
import multiprocessing as mp

from time import strftime, gmtime
from urllib.parse import unquote
from optparse import OptionParser

HEADER_END = '\r\n\r\n'
LINE_END = '\r\n'
HTTP_VERSION_STRING = 'HTTP/1.1'

HEADERS_EMPTY_CONTENT = [
    'Content-Type: text/plain; charset=utf-8',
    'Content-Length: {}'
]


class Codes:
    OK = 200
    BAD_REQUEST = 400
    FORBIDDEN = 403
    NOT_FOUND = 404
    NOT_ALLOWED = 405
    SERVER_ERROR = 500

    description = {
        OK: 'OK',
        BAD_REQUEST: 'Bad Request',
        FORBIDDEN: 'Forbidden',
        NOT_FOUND: 'Not Found',
        NOT_ALLOWED: 'Method Not Allowed',
        SERVER_ERROR: 'Internal Server Error',
    }

    def to_response_line(self, code):
        return ' '.join([HTTP_VERSION_STRING, str(code), self.description[code]])


_workers = list()


def _serve(sock):
    selector = selectors.EpollSelector()
    loop = asyncio.SelectorEventLoop(selector)
    asyncio.set_event_loop(loop)
    coro = asyncio.start_server(_handle_connection, sock=sock)
    server = loop.run_until_complete(coro)
    loop.add_signal_handler(signal.SIGTERM, loop.stop)
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    logging.info('Starting server worker at http://{}:{}'.format(address, port))
    try:
        loop.run_forever()
    finally:
        logging.info('Closing server worker...')
        server.close()
        coro.close()
        loop.run_until_complete(coro)


def _terminate(unused1, unused2):
    logging.info('Termination request received, shutting down workers.')
    for worker in _workers:
        worker.terminate()


def _socket():
    _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    _sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    _sock.bind((address, port))
    return _sock


def start():
    signal.signal(signal.SIGINT, _terminate)
    signal.signal(signal.SIGTERM, _terminate)
    for _ in range(workers_count):
        sock = _socket()
        worker = mp.Process(target=_serve, kwargs=dict(sock=sock))
        worker.daemon = True
        worker.start()
        _workers.append(worker)

    for worker in _workers:
        worker.join()


async def _handle_connection(reader, writer):
    address = writer.get_extra_info('peername')
    logging.info('Accepted connection from %s.', address)
    raw_request = None
    content = None
    headers = HEADERS_EMPTY_CONTENT
    while True:
        try:
            raw_request = await reader.readuntil(HEADER_END.encode())
            if raw_request:
                break
        except asyncio.IncompleteReadError:
            break
    try:
        method, resource, response_headers = _parse_request(raw_request)
        path = _parse_path(resource)
        if method in ['GET', 'HEAD']:
            code, headers = _prepare_response(path, response_headers)
            if method == 'GET' and code == Codes.OK:
                with open(os.path.join(root_path, path), 'rb') as fd:
                    try:
                        content = await _read_file(fd)
                    except IOError:
                        logging.error('Error on reading requested file %s contents.', path)
                        raise
        else:
            code = Codes.NOT_ALLOWED
    except Exception as e:
        logging.exception(e)
        code = Codes.SERVER_ERROR
    writer.write(_create_header_lines(code, headers))
    if content:
        writer.write(content)
    await writer.drain()
    writer.close()


def _parse_request(raw_request):
    if not raw_request:
        raise Exception('Error on reading request data, no data was read')
    decoded_request = raw_request.decode('utf-8')
    splitted_request = decoded_request.split(LINE_END)
    request_line, header_lines = splitted_request[0], splitted_request[1:]
    request_args = request_line.split()
    if len(request_args) < 2:
        raise Exception('Wrong request line: %s' % request_line)
    method, resource = request_args[:2]
    headers = _parse_headers(header_lines)
    close_connection = headers.get('Connection', 'close') == 'close'
    connection = 'close' if close_connection else 'keep-alive'
    response_headers = [
        'Date: {}'.format(strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime())),
        'Server: OTUServer',
        'Connection: {}'.format(connection)
    ]
    return method, resource, response_headers


def _parse_headers(header_lines):
    out = dict()
    for line in header_lines:
        line = line.strip()
        if line:
            header, value = line.split(': ')
            out[header] = value
    return out


def _parse_path(resource):
    unquoted_resource = unquote(resource)
    path = unquoted_resource
    if '?' in unquoted_resource:
        path, unused_query_string = unquoted_resource.split('?')
    if path.endswith('/'):
        path = path + 'index.html'
    if path.startswith('/'):
        path = path[1:]
    return path


def _prepare_response(document_path, headers):
    normpath = os.path.normpath(document_path)
    full_path = os.path.join(root_path, normpath)
    if '/..' in full_path:
        return Codes.FORBIDDEN, headers
    file_exists = os.path.exists(full_path)
    if not file_exists:
        return Codes.NOT_FOUND, headers

    path = os.path.join(root_path, document_path)
    content_length = os.path.getsize(path)
    _, ext = os.path.splitext(path)
    content_type = mimetypes.types_map[ext.lower()]
    headers.extend([
        'Content-Length: {}'.format(content_length),
        'Content-Type: {}'.format(content_type)
    ])
    return Codes.OK, headers


def _create_header_lines(http_code, headers):
    lines = [Codes().to_response_line(http_code)] + headers
    response_string = LINE_END.join(lines) + HEADER_END
    return response_string.encode()


def _read_file(file):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, file.read)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-p", "--port", action="store", type=int, default=80)
    parser.add_option("-w", "--workers", action="store", type=int, default=64)
    parser.add_option("-r", "--rootdir", action="store", type=str, default='.')
    parser.add_option("-l", "--logfile", action="store", type=str, default='/tmp/httpd.log')

    opts, args = parser.parse_args()
    logging.basicConfig(filename=opts.logfile,
                        level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')

    workers = min(mp.cpu_count(), opts.workers)
    address = '127.0.0.1'
    port = opts.port
    root_path = os.path.abspath(opts.rootdir)
    _prepare_response('root_path', root_path)
    workers_count = workers
    start()
