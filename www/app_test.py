import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web

def index(request):
    return web.Response(body=b'<h1>Awesome</h1>')

@asyncio.coroutine     #把一个generator标记为coroutine类型
def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', index)
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)   
    #yield from语法可以让我们方便地调用另一个generator,在此期间，主线程并未等待，而是去执行EventLoop中其他可以执行的coroutine了
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

# 获取EventLoop:
loop = asyncio.get_event_loop()
# 执行coroutine
loop.run_until_complete(init(loop))
loop.run_forever()

#1.异步I/O :
#当代码需要执行一个耗时的IO操作时，它只发出IO指令，并不等待IO结果，然后就去执行其他代码了。一段时间后，当IO返回结果时，再通知CPU进行处理。
#2.协程是一个线程在执行
