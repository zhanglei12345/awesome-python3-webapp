import asyncio, os, inspect, logging, functools

from urllib import parse
from aiohttp import web
from apis import APIError

# 定义了一个装饰器
# 将一个函数映射为一个URL处理函数
def get(path):
    '''define decorator @get('/path')'''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        # 通过装饰器加上__method__属性,用于表示http method
        wrapper.__method__ = "GET"
        # 通过装饰器加上__route__属性,用于表示path
        wrapper.__route__  = path
        return wrapper
    return decorator

# 与@get类似
def post(path):
    '''define decorator @post('/path')'''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = "POST"
        wrapper.__route__  = path
        return wrapper
    return decorator

#命名的关键字参数是为了限制调用者可以传入的参数名，同时可以提供默认值。
#定义命名的关键字参数在没有可变参数的情况下不要忘了写分隔符*，否则定义的将是位置参数。
# 获取函数的值为空的命名关键字
def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

# 获取命名关键字参数名
def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:     # KEYWORD_ONLY, 表示命名关键字参数
            args.append(name)
    return tuple(args)

# 判断函数fn是否带有命名关键字参数
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

# 判断函数fn是否带有关键字参数
def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:   # VAR_KEYWORD, 表示关键字参数, 匹配**kw
            return True

# 函数fn是否有request关键字
def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):             # VAR_POSITIONAL,表示可选参数,匹配*args
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found

#浏览器首先向服务器发送HTTP请求:GET仅请求资源，POST会附带用户数据,路径，域名,如果是POST，那么请求还包括一个Body，包含用户数据。
#服务器向浏览器返回HTTP响应：响应代码（200表示成功，3xx表示重定向，4xx表示客户端发送的请求有错误，5xx表示服务器端处理时发生了错误）；
#响应类型(Content-Type)
#Body(网页的HTML源码就在Body中)
#HTTP格式:每个Header一行一个，换行符是\r\n.Header和Body通过\r\n\r\n来分隔

# 定义RequestHandler类,封装url处理函数
# RequestHandler的目的是从url函数中分析需要提取的参数,从request中获取必要的参数
# 调用url参数,将结果转换为web.response
class RequestHandler(object):
    def __init__(self, app, fn):
        self._app = app # web application
        self._func = fn # handler
        # 以下即为上面定义的一些判断函数与获取函数
        self._has_request_arg = has_request_arg(fn)         #是否有request关键字
        self._has_var_kw_arg = has_var_kw_arg(fn)           #是否带有关键字参数
        self._has_named_kw_args = has_named_kw_args(fn)     #是否带有命名关键字参数
        self._named_kw_args = get_named_kw_args(fn)         #获取命名关键字参数
        self._required_kw_args = get_required_kw_args(fn)   #获取函数的值为空的命名关键字

    # 定义了__call__,则其实例可以被视为函数
    # 此处参数为request
    async def __call__(self, request):
        kw = None # 设不存在关键字参数

        # 存在关键字参数/命名关键字参数
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            # http method 为 post的处理
            if request.method == "POST":
                # http method 为post, 但request的content type为空, 返回丢失信息
                if not request.content_type:
                    return web.HTTPBadRequest("Missing Content-Type")
                ct = request.content_type.lower() # 获得content type字段
                # 以下为检查post请求的content type字段
                # application/json表示消息主体是序列化后的json字符串
                if ct.startswith("application/json"):
                    params = await request.json() # request.json方法的作用是读取request body, 并以json格式解码
                    if not isinstance(params, dict): # 解码得到的参数不是字典类型, 返回提示信息
                        return web.HTTPBadRequest("JSON body must be object.")
                    kw = params # post, content type字段指定的消息主体是json字符串,且解码得到参数为字典类型的,将其赋给变量kw
                # 以下2种content type都表示消息主体是表单
                elif ct.startswith("application/x-www-form-urlencoded") or ct.startswith("multipart/form-data"):
                    # request.post方法从request body读取POST参数,即表单信息,并包装成字典赋给kw变量
                    params = await request.post()
                    kw = dict(**params)
                else:
                    # 此处我们只处理以上三种post 提交数据方式
                    return web.HTTPBadRequest("Unsupported Content-Type: %s" % request.content_type)
            # http method 为 get的处理
            if request.method == "GET":
                # request.query_string表示url中的查询字符串
                # 比如"https://www.google.com/#newwindow=1&q=google",其中q=google就是query_string
                qs = request.query_string
                if qs:
                    kw = dict() # 原来为None的kw变成字典
                    for k, v in parse.parse_qs(qs, True).items(): # 解析query_string,以字典的形如储存到kw变量中
                        kw[k] = v[0]
        if kw is None: # 经过以上处理, kw仍未空,即以上全部不匹配,则获取请求的abstract math info(抽象数学信息),好吧,我也不知道这是什么鬼东西,并以字典形式存入kw
            kw = dict(**request.match_info)
        else:
            # kw 不为空,且requesthandler只存在命名关键字的,则只取命名关键字参数名放入kw
            if not self._has_var_kw_arg and self._named_kw_args:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # 遍历request.match_info(abstract math info), 若其key又存在于kw中,发出重复参数警告
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning("Duplicate arg name in named arg and kw args: %s" % k)
                # 用math_info的值覆盖kw中的原值
                kw[k] = v
        # 若存在"request"关键字, 则添加
        if self._has_request_arg:
            kw["request"] = request
        # 若存在未指定值的命名关键字参数,且参数名未在kw中,返回丢失参数信息
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    #return web.HTTPBadRequest()
                     return web.HTTPBadRequest("Missing argument: %s" % name)
        logging.info("call with args: %s" % str(kw))
        # 以上过程即为从request中获得必要的参数

        # 以下调用handler处理,并返回response.
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error = e.error, data = e.data, message = e.message)

def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))

# 将url处理函数注册到app上
# 处理将针对http method 和path进行
def add_route(app, fn):
    method = getattr(fn, '__method__', None)   # 获取fn.__method__属性,若不存在将返回None
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    # 将非协程或生成器的函数变为一个协程.
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    # 注册request handler
    app.router.add_route(method, path, RequestHandler(app, fn))

# 自动注册所有请求处理函数
def add_routes(app, module_name):
    n = module_name.rfind('.')   # -1 表示未找到,即module_name表示的模块直接导入
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
        # __import__()的作用同import语句,python官网说强烈不建议这么做
        # __import__(name, globals=None, locals=None, fromlist=(), level=0)
        # name -- 模块名
        # globals, locals -- determine how to interpret the name in package context
        # fromlist -- name表示的模块的子模块或对象名列表
        # level -- 绝对导入还是相对导入,默认值为0, 即使用绝对导入,正数值表示相对导入时,导入目录的父目录的层数
    else:
        # 以下语句表示, 先用__import__表达式导入模块以及子模块
        # 再通过getattr()方法取得子模块名, 如datetime.datetime
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        # 忽略以_开头的属性与方法,_xx或__xx(前导1/2个下划线)指示方法或属性为私有的,__xx__指示为特殊变量
        # 私有的,能引用(python并不存在真正私有),但不应引用;特殊的,可以直接应用,但一般有特殊用途
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)
#callable(object)
#中文说明：检查对象object是否可调用。如果返回True，object仍然可能调用失败；但如果返回False，调用对象ojbect绝对不会成功。
#注意：类是可调用的，而类的实例实现了__call__()方法才可调用。
#dir()
#如果要获得一个对象的所有属性和方法，可以使用dir()函数，它返回一个包含字符串的list
