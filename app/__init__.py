import os

from flask import Flask
import os.path as osp
import importlib.util
import config
import inspect

from app.utils.db_utils import DbCfg
from app.views import register_all_views


class _Flask(Flask):
    ''''''

class FlaskApp(_Flask):
    def __init__(self, *args, **kwargs):
        super(FlaskApp, self).__init__(*args, **kwargs)

from app.views.basic_views import basic_app  # 导入蓝图

app = FlaskApp(
    config.APP_NAME,
    static_url_path='/%s/static' % config.APP_NAME,
    static_folder=osp.join(config.PROJECT_ROOT, config.STATIC_FOLDER))

app.config.update(**(config.SVR_FLASK_CONFIG or {}))
# 注册蓝图
# views_directory = os.path.join(os.path.dirname(__file__), 'views')

from .module import module

# 自动按类名/方法后缀注册 views 路由（必须在注册蓝图之前）
# 前缀：类名拆分小写，如 Basic -> /basic
# 请求名：方法名去掉后缀，如 add_account_POST -> add_account
# 请求方式：按后缀 GET/POST，否则 GET 与 POST 都支持
register_all_views(module)

app.register_blueprint(module, url_prefix='/%s' % config.APP_NAME)

db_zj3 = DbCfg('zj3', config.DATABASES).init_db(app)
db_zj3user = DbCfg('zj3user', config.DATABASES).init_db(app)
db_zj3setting = DbCfg('zj3setting', config.DATABASES).init_db(app)
db_zj3element = DbCfg('zj3element', config.DATABASES).init_db(app)
db_zj3bim = DbCfg('zj3bim', config.DATABASES).init_db(app)
