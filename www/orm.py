
import logging, asyncio

import aiomysql     #aiomysql为MySQL数据库提供了异步IO的驱动。

#该函数用于打印执行的SQL语句
def log(sql, args=()):
    logging.info('SQL: %s' % sql)

#每个HTTP请求都可以从连接池中直接获取数据库连接。使用连接池的好处是不必频繁地打开和关闭数据库连接，而是能复用就尽量复用。
#该函数用于创建连接池
@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool     #全局变量用于保存连接池
    __pool = yield from aiomysql.create_pool(    #dict提供的get方法，如果key不存在，可以返回None，或者自己指定的value
        host=kw.get('host', 'localhost'),   # 默认定义host名字为localhost
        port=kw.get('port', 3306),          # 默认定义mysql的默认端口是3306
        user=kw['user'],                    # user是通过关键字参数传进来的
        password=kw['password'],            # 密码
        db=kw['db'],                        # 数据库名字
        charset=kw.get('charset', 'utf8'),  # 默认数据库字符集是utf8
        autocommit=kw.get('autocommit', True), # 默认自动提交事务
        maxsize=kw.get('maxsize', 10),      # 连接池最多同时处理10个请求
        minsize=kw.get('minsize', 1),       # 连接池最少1个请求
        loop=loop                           # 传递消息循环对象loop用于异步执行
    )

# =============================SQL处理函数区==========================
# select语句则对应该select方法,传入sql语句和参数
@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
    # 这里声明global,是为了区分赋值给同名的局部变量(这里其实可以省略，因为后面没赋值)
    global __pool
    # 异步等待连接池对象返回可以连接线程，with语句则封装了清理（关闭conn）和处理异常的工作
    with (yield from __pool) as conn:
        # 等待连接对象返回DictCursor可以通过dict的方式获取数据库对象，需要通过游标对象执行SQL
	#默认情况下cursor方法返回的是BaseCursor类型对象，BaseCursor类型对象在执行查询后每条记录的结果以列表(list)表示,DictCursor(字典)
        cur = yield from conn.cursor(aiomysql.DictCursor)          
        # 所有args都通过repalce方法把占位符替换成%s
        yield from cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            rs = yield from cur.fetchmany(size)  # 从数据库获取指定的行数,返回结果是一个元组,tuple中的每一个元素对应查询结果中的一条记录
        else:
            rs = yield from cur.fetchall()       # 返回所有结果集,返回结果是一个元组
        yield from cur.close()
        logging.info('rows returned: %s' % len(rs))
        return rs          # 返回结果集

#SQL语句的占位符是?，而MySQL的占位符是%s，select()函数在内部自动替换。
#yield from将调用一个子协程（也就是在一个协程中调用另一个协程）并直接获得子协程的返回结果。

# execute方法只返回结果数，不返回结果集,用于insert,update这些SQL语句
@asyncio.coroutine
def execute(sql, args, autocommit=True):
    log(sql)
    with (yield from __pool) as conn:
        if not autocommit:            
            yield from conn.begin()
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount   # 返回受影响的行数
            if not autocommit:
                yield from conn.commit()
            yield from cur.close()
        except BaseException as e:
            if not autocommit:
                yield from conn.rollback()
            raise             ######
        return affected
#返回一个整数表示影响的行数


#ORM全称“Object Relational Mapping”，即对象-关系映射，就是把关系数据库的一行映射为一个对象，也就是一个类对应一个表，这样，写代码更简单，不用直接操作SQL语句。
# =====================================属性类===============================
class Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):       # 直接print的时候定制输出信息为类名和列类型和列名
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
    # String一般不作为主键，所以默认False,DDL是数据定义语言，为了配合mysql，所以默认设定为100的长度
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

# ========================================Model基类以及具其元类=====================
# 对象和关系之间要映射起来，首先考虑创建所有Model类的一个父类，具体的Model对象（就是数据库表在你代码中对应的对象）再继承这个基类
# 该元类主要使得Model基类具备以下功能:
# 1.任何继承自Model的类（比如User），会自动通过ModelMetaclass扫描映射关系
# 并存储到自身的类属性如__table__、__mappings__中
# 2.创建了一些默认的SQL语句

def create_args_string(num):   # 在ModelMetaclass的特殊变量中用到
 # insert插入属性时候，增加num个数量的占位符'?'
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)

#type(name, bases, dict)         type就是一个元类，并且它还是所有类的元类
#当我们使用class关键字定义好一个类，python解释器就是通过调用type函数来构造类的，它以我们写好的类定义(包括类名，父类(元组)，属性(字典)）作为参数，并返回一个类

class ModelMetaclass(type):
    # __new__方法在__init__方法之前被调用
    # 因此，当我们想要控制类的创建行为时，一般使用__new__方法
    # 定义普通类的方法时，我们用self作为第一个参数，来指向调用方法的类实例本身
    # 此处cls的意义与self类似，用于指向使用该元类创建的类本身
    def __new__(cls, name, bases, attrs):  #使用该元类创建的类本身,类的名字,父类的元组,类属性的字典
        # 排除Model类本身:
        if name=='Model':
            return type.__new__(cls, name, bases, attrs)
        # 获取table名称:
        tableName = attrs.get('__table__', None) or name      # 前面get失败了就直接赋值name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        # 获取所有的Field和主键名:
        mappings = dict()   # 保存属性和值的k,v
        fields = []
        primaryKey = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:      #为什么是v.primary_key?  v的类型?  attrs类型？
                    # 找到主键:
                    if primaryKey:   # 如果primaryKey属性已经不为空了，说明已经有主键了，则抛出错误,因为只能1个主键
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)   # 非主键全部放到fields列表中
        if not primaryKey:      # 如果遍历完还没找到主键，那抛出错误
            raise RuntimeError('Primary key not found.')
        for k in mappings.keys():     # 清除mappings，防止实例属性覆盖类的同名属性，造成运行时错误
            attrs.pop(k)
	# %s占位符全部替换成具体的属性名
	#通常情况不需要` ，但是遇到字段名字和sql关键字同名时就需要了
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings # 保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey # 主键属性名
        attrs['__fields__'] = fields # 除主键外的属性名
        # 构造默认的SELECT, INSERT, UPDATE和DELETE语句:
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)

#所有ORM映射的基类Model
#任何继承自Model的类，会自动通过ModelMetaclass扫描映射关系，并存储到自身的类属性如__table__、__mappings__中
class Model(dict, metaclass=ModelMetaclass):
# 继承dict是为了使用方便，例如对象实例user['id']即可轻松通过UserModel去数据库获取到id

    def __init__(self, **kw):
    # super(类名，类对象)
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
    # 获取某个具体的值，肯定存在的情况下使用该函数,否则会使用__getattr()__
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
     # 这个方法当value为None的时候能够返回默认值
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:  # 如果实例的域存在默认值，则使用默认值
	        # field.default是callable的话则直接调用
                value = field.default() if callable(field.default) else field.default  ######
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value
   

    # --------------------------每个Model类的子类实例应该具备的执行SQL的方法------
    @classmethod    # 类方法
    @asyncio.coroutine
    def findNumber(cls, selectField, where=None, args=None):
        #根据WHERE条件查找，但返回的是整数，适用于select count(*)类型的SQL。
        ' find number by select and where. '
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]   #_num_
        if where:
            sql.append('where')
            sql.append(where)
        rs = yield from select(' '.join(sql), args, 1)  # size = 1
        if len(rs) == 0:
            return None
        return rs[0]['_num_']  #?

    @classmethod   # 类方法
    @asyncio.coroutine
    def find(cls, pk):
        ' find object by primary key. '
        rs = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)   # 1?
        if len(rs) == 0:
            return None
        return cls(**rs[0])  #?

    # 这个是实例方法
    @asyncio.coroutine
    def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    @asyncio.coroutine
    def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = yield from execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)

    @asyncio.coroutine
    def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = yield from execute(self.__delete__, args)
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)
