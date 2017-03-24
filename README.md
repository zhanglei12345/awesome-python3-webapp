## 准备工作：
1. 确认系统安装的Python版本是3.5.x
2. aiohttp：异步框架
3. jinja2：前端模板引擎
4. MySQL 5.x数据库
5. aiomysql：MySQL的Python异步驱动程序

## 代码结构：

```
- www  
	- app_test.py : 测试 Web App 骨架
	- orm_test.py : 测试 ORM 框架
	- orm.py : ORM 框架（对象-关系映射）
			     1. 创建连接池
			     2. sql 处理函数
			     3. 创建属性类
			     4. 创建 Model 基类以及其元类
	- models.py : 创建3个表对应的类
	- coroweb.py : Web 框架
				 1. 定义装饰器，get、post
				 2. 封装url处理函数
				 3. 添加静态页面的路径
				 4. 将url处理函数自动注册到app上
	- app.py : Web App 骨架
				 1. 初始化jinja2环境
				 2. 实现middleware(中间件)
				 3. 创建app对象，系统初始化
	- config_default.py ： 开发环境的标准配置
	- config_override.py ： 生产环境的标准配置
	- config.py ： 读取合并配置
	- handlers.py : url处理函数
	- apis.py : 页面管理与api错误提示
	- markdown2.py : 支持markdown的插件
```

## 处理流程：
1. 建立model：即建立python中的类与数据库中的表的映射关系    
INFO:root:found model: User (table: users)  
INFO:root:found model: Blog (table: blogs)  
INFO:root:found model: Comment (table: comments)  
2. 创建连接池：  
INFO:root:create database connection pool...  
3. 初始化jinja2：  
INFO:root:init jinja2...
4. 注册url处理函数（handler）：  
INFO:root:globals = coroweb  
INFO:root:add route GET /api/blogs => api_blogs(page)  
...
5. 添加静态资源  
INFO:root:add static /static/ => ...
6. 创建服务器对象  
INFO:root:server started at http://127.0.0.1:9000


#### 请求首页：
  
1. 在处理请求之前,先记录日志(logger_factory、中间件起作用）：  
INFO:root:Request: GET /  
2. 解析cookie，绑定登录用户（auth_factory、中间件起作用）：  
INFO:root:check user: GET /
3. 将request handler的返回值转换为web.Response对象（response_factory、中间件起作用）：  
INFO:root:response handler...
4. 处理url函数（RequestHandler中的`__call__`起作用）：  
INFO:root:query_string:  
INFO:root:call with args: {}    
执行url函数：（index）：  
调用Blog.findNumber：    
调用select():  
INFO:root:SQL: select count(id) `_num_` from `blogs`   
INFO:root:rows returned: 1   
返回至findNumber()：  
INFO:root:findNumber rs: `[{'_num_': 4}]`  
调用Blog.findAll：  
调用select():  
INFO:root:SQL: select `id`, `user_id`, `user_name`, `user_image`, `name`, `summary`, `content`, `created_at` from `blogs` order by created_at desc limit ?, ?    
INFO:root:rows returned: 2   
返回至findAll()  
返回至index（） 
5. 返回至response_factory,将返回值转换为web.Response：  
INFO:root: request handler end...
 
 ## 参考教程：
 
 [廖雪峰官网教程](http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000)