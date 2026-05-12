# Wizard 项目说明

这是一个基于 Flask 的后端服务项目（代号 Wizard 或 wizard ），其核心特色是集成了 LangChain 和 LangGraph 实现的复杂 AI 智能体（Agent）工作流，同时具备完善的 Web 服务基础设施。

以下是该项目的详细介绍：

### 1. 项目概览
该项目不仅是一个标准的 Web 后端，还内置了强大的 AI 研究助手功能。

- Web 框架 ：基于 Flask，提供自动路由注册、参数校验、异常处理等企业级开发能力。
- AI 引擎 ：集成 LangChain 和 LangGraph，实现了多智能体协作（Multi-Agent Collaboration）的工作流。
### 2. 核心技术栈
- Web 服务 ：
  - Flask : Web 框架
  - Gunicorn + Supervisor : 生产环境部署与进程管理
  - Peewee : 轻量级 ORM，支持 MySQL/SQLite
- AI & LLM ：
  - LangChain : 大语言模型应用开发框架
  - LangGraph : 用于构建有状态、多角色的 Agent 工作流
  - OpenAI : LLM 提供商
  - Tavily : 专为 AI 设计的搜索引擎工具
### 3. 主要功能模块 A. Web 基础设施
项目封装了一套高效的开发模式：

- 自动路由注册 ：无需手动配置 URL，根据类名和方法名自动生成路由（例如 Basic.add_account -> /basic/add_account ）。
- RPC 风格开发 ：提供 @rpc 装饰器，自动处理 JSON/Form 参数校验、类型转换和响应封装。
- 数据库管理 ： DatabaseManager 提供连接池管理和多数据库支持。

## 快速开始

```bash
# 1) 创建并激活虚拟环境（建议）
python -m venv .venv
. .venv/Scripts/activate   # Windows PowerShell: .\.venv\Scripts\activate

# 2) 安装依赖
pip install -r requirements.txt

# 3) 启动
python run.py
```

运行后默认监听 `http://127.0.0.1:5005/Wizard`。

## 路由与视图

- 视图基类：`app/views/__init__.py` 中的 `LoginRequiredDispatchView`
- 路由自动注册：`app/__init__.py` 在注册蓝图前调用 `register_all_views`
- 路由规则：
  - 前缀：类名拆分为下划线小写，例如 `Basic` → `/basic`
  - 方法后缀：`_GET` / `_POST` 指定请求方式；无后缀则 GET/POST 均可
  - 路径：方法名去掉后缀，例如 `add_account_POST` → `/basic/add_account`

### RPC 装饰器

位于 `app/_webapi/__init__.py`，负责入参校验和出参包装：

- `@rpc(desc, args, returns, input_type)`：
  - 入参：`args` 定义字段，支持 `required.*` / `optional.*`
  - 输入来源：
    - `input_type == JSON` 时取 `request.get_json(silent=True)`
    - 否则合并 `request.args`（querystring）与 `request.form`
  - 校验后赋值到 `req`，业务方法可直接访问 `req.xxx`
  - 出参：业务设置 `rsp.data`，若配置 `returns` 会再按 schema 校验/过滤
  - 最终响应：`jsonify(rsp.to_dict())`

示例（简化）：
```python
from app._webapi import rpc, InputType, required, optional
class LoginRequiredDispatchView(object):
    '''登录验证逻辑'''

class Basic(LoginRequiredDispatchView):
    @rpc(
        '添加账号',
        args=dict(
            securityCode=required.StringField(desc='安全码'),
            cardNumber=required.StringField(desc='卡号'),
            month=required.StringField(desc='月'),
            year=required.StringField(desc='年'),
            postalCode=optional.StringField(desc='邮编', default='')
        ),
        returns=dict(
            id=required.IntegerField(desc='主键'),
            msg=optional.StringField(desc='提示', default='ok')
        ),
        input_type=InputType.JSON
    )
    def add_account(self, req, rsp):
        # 业务逻辑……
        rsp.data = {'id': 1, 'msg': 'created'}
```

## 数据库

- 配置来源：`config.py` 中的 `DATABASES`
- 工具：`app/utils/db_utils.py`
  - `DbCfg`：单库配置封装，支持 MySQL/SQLite
  - `DatabaseManager`：`get(name, app=None)` 获取/缓存连接；`ping(name)` 健康检查；`close()` 关闭
  - 默认全局实例：`db_manager`
- 使用示例：
```python
from app.utils.db_utils import db_manager
import peewee

db = db_manager.get('zj3')

class MyModel(peewee.Model):
    class Meta:
        database = db
```

## 运行配置

- 主入口：`run.py`，读取 `config.SVR_CONFIG`（默认 `host=0.0.0.0`, `port=5005`, `debug=True`）
- 环境变量：
  - `SUBLIMETEXT`：若存在则禁用 debug（`debug=False`）
  - 你可在运行前覆盖 `SVR_CONFIG` 中的字段（如 `FLASK_ENV`/`FLASK_DEBUG`）

## 目录结构

```
app/
  __init__.py          # Flask 应用初始化、蓝图注册、自动路由注册
  module.py            # 主蓝图
  views/               # 视图与路由（自动注册）
  _webapi/             # rpc 装饰器、参数/响应校验
  services/            # 服务层
  models/              # 数据模型
  utils/               # 工具（db_utils 等）
config.py              # 全局配置（数据库、服务器端口等）
run.py                 # 启动入口
requirements.txt       # 依赖
```

## 调试提示

- 若在带空格路径的环境下调试（如 `C:\Program Files\...`），注意 IDE/调试器的子进程命令行需正确引用，确保使用 `.venv` 的解释器。
- 自动重载（Flask reloader）会启动子进程，需保证 PATH 优先 `.venv\Scripts`，避免误用其他 Python。
