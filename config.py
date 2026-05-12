# coding=u8

import logging
import os
import os.path as osp
import sys
from pathlib import Path

import yaml

APP_NAME = 'tiger'

# 暂时屏蔽登录要求!!!!!!
# LOGIN_IGNORE = True

# 项目根目录
PROJECT_ROOT = osp.dirname(osp.abspath(__file__))
STATIC_FOLDER = 'static'

# 需要加入到sys.path的目录列表
EXTENTIONS_DIRECTORIES = [
    '../pycomm',
    '../zhijian_server_pyutils',
]

# 额外的Mako模板位置
TEMPLATE_CONFIG = dict(
    template_additional_paths=[
    ],
)

# WEB服务配置
SVR_CONFIG = dict(
    host='0.0.0.0',
    port=5005,
    debug=True,
)

# Flask的额外配置
# 参考：http://flask.pocoo.org/docs/0.12/config/#builtin-configuration-values
SVR_FLASK_CONFIG = dict()

# session信息配置
SESSION = dict(
    name='zjsess',  # 客户端cookie名
    key_pairs='helloworld',  # cookie校验密钥
    prefix='session_',  # redis保存前缀
    tmp_age=3600,  # 默认cookie保存时间
    max_age=3600 * 24 * 7,  # 默认cookie最大保存时间
    redis=None,
)

# redis配置
REDIS = None
AIE_HOST = None
ZJ_BASE_DIR = None
# 数据库配dir置
SYNC_MODELS = False
DATABASES = dict(
    zj3setting=dict(
        engine='mysql',
        database='test_zhijian2_setting',
        params=dict(
            host='127.0.0.1', port=3306, user='zj_test', password='test_PLLhnSDF2KdJFzVQ'),
        pool=dict(),
    ),
    zj3=dict(
        engine='mysql',
        database='test_zhijian2',
        params=dict(
            host='127.0.0.1', port=3306, user='zj_test', password='test_PLLhnSDF2KdJFzVQ'),
        pool=dict(),
    ),
    zj3user=dict(
        engine='mysql',
        database='test_zhijian2_apisvr',
        params=dict(
            host='127.0.0.1', port=3306, user='zj_test', password='test_PLLhnSDF2KdJFzVQ'),
    ),
    zj3element=dict(
        engine='mysql',
        database='test_zhijian2_bim',
        params=dict(
            host='127.0.0.1', port=3306, user='zj_test', password='test_PLLhnSDF2KdJFzVQ'),
    ),
    zj3bim=dict(
        engine='mysql',
        database='test_ue4model',
        params=dict(
            host='127.0.0.1', port=3306, user='zj_test', password='test_PLLhnSDF2KdJFzVQ'),
    )
)

# 日志配置，default为zjutils.logger默认使用的日志名称
LOGGING_CONFIG = {
    'default': 'app',
    'app': dict(
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S',
        enable_color=True,
        format=[
            '[',
            '%(name)s',
            '|%(asctime)s|%(filename)s:%(lineno)s(%(funcName)s)|',
            '%(levelname)s',
            ']%(message)s',
        ],
    ),
}

INNER_API = {}

# apilist路径，默认不开启
APILIST_PATH = None
# 请求远端api服务的地址，仅在APILIST_PATH已设置的情况下有效
REMOTE_APILIST_PATH = None

# 显示路由信息
LIST_ROUTES = True
LLM = dict()

# 登录路径
LOGIN_PATH = '/login'

HOST = "devtest8.buildingqm.com"

CONNAGENT = {
    "agent_addr": "127.0.0.1:40000",
    "srv_domain": ".connagent.zhijiancloud.net"
}

IMAGE_UPLOAD = {
    "path": "/data/zhijian/pictures",
    "store_key_prefix": "pictures",
    "allow_extensions": ["jpg"]
}


def _load_config():
    config_file = Path(osp.join(osp.dirname(osp.abspath(__file__)), "conf", "auto.yaml"))
    print('>>> load config file:', config_file)
    with open(config_file, 'rb') as fr:
        cfg = yaml.load(fr, Loader=yaml.Loader)
    for k, v in cfg.items():
        _custom_cfgs[k.upper()] = v


_custom_cfgs = {}
_load_config()
globals().update(_custom_cfgs)
del _custom_cfgs

for index, directory in enumerate(EXTENTIONS_DIRECTORIES):
    sys.path.insert(index + 1, directory)

