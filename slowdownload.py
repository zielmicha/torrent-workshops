#!/usr/bin/env python3
from aiohttp import web
import aiohttp
import asyncio
import math

data = open('kotek.jpg', 'rb').read()
speed = 50 * 1000
chunk_size = 1000
chunk_timeout = chunk_size / speed
content_type = 'image/jpeg'

class SlowResponse(web.StreamResponse):
    def __init__(self, *, status, reason, body, content_type, headers=None):
        super().__init__(headers=headers, status=status, reason=reason)
        self.body = body
        self.content_type = content_type
        self.content_length = len(body)

    @asyncio.coroutine
    def write_eof(self):
        body = self.body
        n_chunks = int(math.ceil(len(body) / chunk_size))
        for i in range(n_chunks):
            yield from asyncio.sleep(chunk_timeout)
            self.write(body[i * chunk_size:(i + 1) * chunk_size])
        yield from super().write_eof()

class HeadResponse(web.StreamResponse):
    def __init__(self, *, status, reason, body, content_type, headers=None):
        super().__init__(headers=headers, status=status, reason=reason)
        self.content_type = content_type
        self.content_length = len(body)

    @asyncio.coroutine
    def write_eof(self):
        pass

@asyncio.coroutine
def handle_head(request):
    return HeadResponse(body=data, content_type=content_type,
                        status=200, reason='OK')

@asyncio.coroutine
def handle_get(request):
    range_header = request.headers.get('RANGE')
    want_range = None
    if range_header:
        range_header = range_header.lower()
        if ',' in range_header:
            return aiohttp.web.HTTPRequestRangeNotSatisfiable()
        elif range_header.startswith('bytes='):
            split = list(range_header.split('=', 1)[1].split('-'))
            if len(split) != 2:
                return aiohttp.web.HTTPRequestRangeNotSatisfiable()
            if not split[0]:
                split[0] = 0
            if not split[1]:
                split[1] = len(data) - 1

            try:
                split = list(map(int, split))
            except ValueError:
                return aiohttp.web.HTTPBadRequest()

            want_range = split[0], split[1] + 1
        else:
            return aiohttp.web.HTTPRequestRangeNotSatisfiable()

    if want_range:
        split_data = data[want_range[0]:want_range[1]]
        content_range = 'bytes %s-%s/%s' % (want_range[0], want_range[1] - 1, len(data))
        print(content_range, range_header, want_range, len(split_data))
        return SlowResponse(body=split_data, content_type=content_type,
                            status=206, reason='Partial Content', headers={'content-range': content_range})
    else:
        return SlowResponse(body=data, content_type=content_type,
                            status=200, reason='OK')

@asyncio.coroutine
def redirect(request):
    return aiohttp.web.HTTPFound('http://warsztatywww.pl/workshop/torrent/')

@asyncio.coroutine
def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/{name}', handle_get)
    app.router.add_route('HEAD', '/{name}', handle_head)
    app.router.add_route('GET', '/', redirect)
    srv = yield from loop.create_server(app.make_handler(), '0.0.0.0', 5600)
    return srv

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop))
    loop.run_forever()
