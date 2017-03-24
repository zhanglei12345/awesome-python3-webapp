import time, uuid

# 导入属性类
from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

# 当用户定义一个class User(Model)时，Python解释器首先在当前类User的定义中查找metaclass，如果没有找到，就继续在父类Model中查找metaclass，
# 找到了，就使用Model中定义的metaclass的ModelMetaclass来创建User类，也就是说，metaclass可以隐式地继承到子类，但子类自己却感觉不到。

#创建3个表,一个类对应一个表,表中一行映射为一个对象
class User(Model):
    __table__ = 'users'

    id = StringField(name='id', primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(name='email', ddl='varchar(50)')
    passwd = StringField(name='passwd', ddl='varchar(50)')
    admin = BooleanField(name='admin')
    name = StringField(name='name', ddl='varchar(50)')
    image = StringField(name='image', ddl='varchar(500)')
    created_at = FloatField(name='created_at', default=time.time)

class Blog(Model):
    __table__ = 'blogs'

    id = StringField(name='id', primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(name='user_id', ddl='varchar(50)')
    user_name = StringField(name='user_name', ddl='varchar(50)')
    user_image = StringField(name='user_image', ddl='varchar(500)')
    name = StringField(name='name', ddl='varchar(50)')
    summary = StringField(name='summary', ddl='varchar(200)')
    content = TextField(name='content')
    created_at = FloatField(name='created_at', default=time.time)
    #主键id的缺省值是函数next_id，创建时间created_at的缺省值是函数time.time，可以自动设置当前日期和时间。

class Comment(Model):
    __table__ = 'comments'

    id = StringField(name='id', primary_key=True, default=next_id, ddl='varchar(50)')
    blog_id = StringField(name='blog_id', ddl='varchar(50)')
    user_id = StringField(name='user_id', ddl='varchar(50)')
    user_name = StringField(name='user_name', ddl='varchar(50)')
    user_image = StringField(name='user_image', ddl='varchar(500)')
    content = TextField(name='content')
    created_at = FloatField(name='created_at', default=time.time)
    #日期和时间用float类型存储在数据库中，而不是datetime类型，这么做的好处是不必关心数据库的时区以及时区转换问题，排序非常简单，显示的时候，只需要做一个float到str的转换，也非常容易。
