#asyncio是Python 3.4版本引入的标准库，直接内置了对异步IO的支持。
import logging; logging.basicConfig(level=logging.INFO)   # 默认级别设置为INFO
import asyncio
from aiohttp import web

async def index(request):
    await asyncio.sleep(0.5)
    return web.Response(body=b'<h1>Index</h1>')

async def hello(request):
    await asyncio.sleep(0.5)
    text = '<h1>hello, %s!</h1>' % request.match_info['name']
    return web.Response(body=text.encode('utf-8'))

async def init(loop):
    app = web.Application(loop=loop)
    # 用于测试：
    if not asyncio.iscoroutinefunction(index) and not inspect.isgeneratorfunction(index):
        # 用于测试：
        logging.info(' index is not a coroutinefunction ')
        fn = asyncio.coroutine(index)
    else:
        logging.info(' index is a coroutinefunction ')

    app.router.add_route('GET', '/', index)
    app.router.add_route('GET', '/hello/{name}', hello)
    # 调用子协程:创建一个TCP服务器,绑定到"127.0.0.1:9000"socket,并返回一个服务器对象
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    print('Server started at http://127.0.0.1:9000...')
    return srv

#我们从asyncio模块中直接获取一个EventLoop的引用，然后把需要执行的协程扔到EventLoop中执行，就实现了异步IO。

# 获取EventLoop:
loop = asyncio.get_event_loop()

# 执行coroutine
loop.run_until_complete(init(loop))
loop.run_forever()

#1.异步I/O :
#当代码需要执行一个耗时的IO操作时，它只发出IO指令，并不等待IO结果，然后就去执行其他代码了。一段时间后，当IO返回结果时，再通知CPU进行处理。
#在异步IO模型下，一个线程就可以同时处理多个IO请求，并且没有切换线程的操作.

#2.协程是一个线程在执行(没有线程切换的开销,不需要多线程的锁机制)
#子程序(函数)调用是通过栈实现的，一个线程就是执行一个子程序。
#子程序调用总是一个入口，一次返回，调用顺序是明确的。而协程的调用和子程序不同。
#协程看上去也是子程序，但执行过程中，在子程序内部可中断，然后转而执行别的子程序，不是函数调用,有点类似CPU的中断,在适当的时候再返回来接着执行。
#Python对协程的支持是通过generator实现的。Python的yield不但可以返回一个值，它还可以接收调用者发出的参数。

#3.为了简化并更好地标识异步IO，从Python 3.5开始引入了新的语法async和await,可以让coroutine的代码更简洁易读。
#把@asyncio.coroutine替换为async；
#把yield from替换为await。
