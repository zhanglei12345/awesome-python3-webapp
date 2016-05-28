import sys
import asyncio
import orm
from models import User, Blog, Comment

@asyncio.coroutine
def test(loop):
    yield from orm.create_pool(loop=loop,user='www-data', password='www-data', db='awesome')

    u = User(name='222222222', email='22222@example.com', passwd='123', image='about:blank')

    yield from u.save()

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()
if loop.is_closed():
    sys.exit(0)
