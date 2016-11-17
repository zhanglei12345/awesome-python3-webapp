import sys
import asyncio
import orm
from models import User, Blog, Comment

async def test(loop):
    await orm.create_pool(loop=loop,user='www-data', password='www-data', db='awesome')
    u = User(name='222222222', email='111111@example.com', passwd='123456', image='about:blank')
    await u.save()

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()
if loop.is_closed():
    sys.exit(0)

#调用时需要特别注意：user.save()没有任何效果，因为调用save()仅仅是创建了一个协程，并没有执行它。一定要用：yield from user.save()才真正执行了INSERT操作。
