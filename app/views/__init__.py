import importlib
import os
import re

from flask import Flask
from flask.views import View


class LoginRequiredDispatchView(object):
    # methods = ['GET', 'POST', 'PUT', 'DELETE']

    @classmethod
    def register(cls, app_or_blueprint):
        """
        注册视图类的所有路由
        """
        # 获取类名并转换为URL前缀
        url_prefix = '/' + '_'.join([s.lower() for s in re.findall('[A-Z][^A-Z]*', cls.__name__)])
        # view_func = cls.as_view(cls.__name__.lower())

        # 实例化一次，确保绑定方法的 self
        instance = cls()

        # 遍历类中的所有方法
        for name, method in cls.__dict__.items():
            if hasattr(method, '_is_route'):
                method_name = name
                if method_name.endswith('_POST'):
                    _http_method = ['POST']
                    _method_name = method_name[:-5]
                elif method_name.endswith('_GET'):
                    _http_method = ['GET']
                    _method_name = method_name[:-4]
                else:
                    _http_method = ['GET', 'POST']
                    _method_name = method_name

                # 绑定实例方法，避免缺失 self
                view_func = getattr(instance, method_name)

                # 注册路由
                app_or_blueprint.add_url_rule(
                    f'{url_prefix}/{_method_name}',
                    view_func=view_func,
                    methods=_http_method
                )


def register_all_views(app, views_folder='views'):
    """
    自动注册views文件夹下所有视图类的路由
    """
    # 获取views文件夹的绝对路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    views_dir = os.path.join(base_dir, views_folder)

    # 遍历views文件夹下的所有Python文件
    for root, dirs, files in os.walk(views_dir):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                # 构建模块路径
                rel_path = os.path.relpath(root, base_dir)
                module_path = f"app.{'.'.join(rel_path.split(os.sep))}.{file[:-3]}"

                try:
                    # 导入模块
                    module = importlib.import_module(module_path)

                    # 遍历模块中的所有成员
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        # 检查是否是LoginRequiredDispatchView的子类
                        if (isinstance(attr, type) and
                                issubclass(attr, LoginRequiredDispatchView) and
                                attr != LoginRequiredDispatchView):
                            # 注册视图类的路由
                            attr.register(app)
                            print(f"Registered routes for {attr.__name__}")

                except Exception as e:
                    print(f"Error loading module {module_path}: {str(e)}")