'''读取配置文件,优先从conffig_override.py读取'''

import config_default

# 自定义字典
class Dict(dict):
    '''
    Simple dict but support access as x.y style.
    '''
    def __init__(self, names=(), values=(), **kw):
        # 调用类Dict的父类(dict)的__init__方法
        super(Dict, self).__init__(**kw)
        # 建立键值对关系
        # zip()返回一个zip object，该对象的每一个元素都是一个元组
        for k, v in zip(names, values):
            self[k] = v

    # 定义描述符,方便通过点标记法取值,即a.b。__getattr__在类属性未找到时才会被调用
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    # 定义描述符,方便通过点标记法设值,即a.b=c
    def __setattr__(self, key, value):
        self[key] = value

# 融合配置文件
def merge(defaults, override):
    r = {}
    # 创建一个空的字典,用于配置文件的融合,而不对任意配置文件做修改
    # 1) 从默认配置文件取key,优先判断该key是否在自定义配置文件中有定义
    # 2) 若有,则判断value是否是字典,
    # 3) 若是字典,重复步骤1
    # 4) 不是字典的,则优先从自定义配置文件中取值,相当于覆盖默认配置文件
    for k, v in defaults.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r

# 将内建字典转换成自定义字典类型
def toDict(d):
    D = Dict()
    for k, v in d.items():
        # 字典某项value仍是字典的(比如"db"),则将value的字典也转换成自定义字典类型
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D

# 默认配置
configs = config_default.configs

try:
    # 导入自定义配置文件,并将默认配置与自定义配置进行混合
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass

# 最后将混合好的配置字典转成自定义字典类型,方便取值与设值
configs = toDict(configs)
