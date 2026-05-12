# Supervisor 配置变量说明

## 变量来源

这些 `{{变量名}}` 格式的变量通常来自以下几个地方：

### 1. **部署脚本/工具**
- **Ansible Playbook**: 在 `vars` 或 `group_vars` 中定义
- **Fabric/Invoke**: 在部署脚本中定义
- **自定义部署脚本**: Python/Shell 脚本中定义

### 2. **配置文件**
- **conf/auto.yaml**: 项目配置文件（如 `repo_name`）
- **环境配置文件**: 不同环境的配置文件

### 3. **环境变量**
- 系统环境变量
- CI/CD 系统设置的环境变量

### 4. **CI/CD 系统**
- Jenkins Pipeline 变量
- GitLab CI/CD 变量
- GitHub Actions 变量

## 变量说明

| 变量名 | 说明 | 示例值 | 可能来源 |
|--------|------|--------|----------|
| `{{supervisor_program_name}}` | Supervisor 程序名称 | `wizard` 或 `tiger` | 部署脚本/配置文件 |
| `{{user}}` | 运行用户 | `www-data`, `nobody` | 部署脚本/系统配置 |
| `{{zjvenv3}}` | 虚拟环境根目录 | `/data/py/venv3` | 系统配置/环境变量 |
| `{{env_name}}` | 环境名称 | `tayg-test`, `prod` | conf/auto.yaml 的 `enterprise_id` 或 `env_group` |
| `{{repo_name}}` | 仓库名称 | `zj_setting_svr`, `wizard` | conf/auto.yaml 的 `repo_name` |
| `{{port}}` | 服务端口 | `5005`, `29918` | conf/auto.yaml 的 `svr_config.port` |
| `{{project_dir}}` | 项目目录 | `/data/zhijian/wizard` | 部署脚本/系统配置 |
| `{{log_dir}}` | 日志目录 | `/data/log/python` | 系统配置/环境变量 |
| `{{conf_path}}` | 配置文件路径 | `auto`, `prod` | 部署脚本/环境变量 |

## 变量替换方式

### 方式 1: Python 脚本替换（推荐）

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import yaml
import os

# 读取配置文件
with open('conf/auto.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 定义变量
variables = {
    'supervisor_program_name': 'wizard',
    'user': 'www-data',
    'zjvenv3': '/data/py/venv3',
    'env_name': config.get('enterprise_id', 'tayg-test'),
    'repo_name': config.get('repo_name', 'wizard'),
    'port': config.get('svr_config', {}).get('port', 5005),
    'project_dir': '/data/zhijian/wizard',
    'log_dir': '/data/log/python',
    'conf_path': 'auto',
}

# 读取模板
with open('supervisor_template.conf', 'r', encoding='utf-8') as f:
    template = f.read()

# 替换变量
for key, value in variables.items():
    template = template.replace('{{' + key + '}}', str(value))

# 写入配置文件
with open('supervisor.conf', 'w', encoding='utf-8') as f:
    f.write(template)

print("Supervisor 配置文件已生成: supervisor.conf")
```

### 方式 2: Shell 脚本替换

```bash
#!/bin/bash

# 读取配置文件
ENV_NAME=$(grep 'enterprise_id:' conf/auto.yaml | awk '{print $2}')
REPO_NAME=$(grep 'repo_name:' conf/auto.yaml | awk '{print $2}')
PORT=$(grep -A 2 'svr_config:' conf/auto.yaml | grep 'port:' | awk '{print $2}')

# 替换变量
sed -e "s/{{supervisor_program_name}}/wizard/g" \
    -e "s/{{user}}/www-data/g" \
    -e "s|{{zjvenv3}}|/data/py/venv3|g" \
    -e "s/{{env_name}}/$ENV_NAME/g" \
    -e "s/{{repo_name}}/$REPO_NAME/g" \
    -e "s/{{port}}/$PORT/g" \
    -e "s|{{project_dir}}|/data/zhijian/wizard|g" \
    -e "s|{{log_dir}}|/data/log/python|g" \
    -e "s/{{conf_path}}/auto/g" \
    supervisor_template.conf > supervisor.conf

echo "Supervisor 配置文件已生成: supervisor.conf"
```

### 方式 3: Ansible 模板

```yaml
# playbook.yml
- hosts: web_servers
  vars:
    supervisor_program_name: "wizard"
    user: "www-data"
    zjvenv3: "/data/py/venv3"
    env_name: "{{ enterprise_id }}"
    repo_name: "{{ repo_name }}"
    port: "{{ svr_config.port }}"
    project_dir: "/data/zhijian/wizard"
    log_dir: "/data/log/python"
    conf_path: "auto"
  tasks:
    - name: 生成 supervisor 配置
      template:
        src: supervisor_template.conf
        dest: /etc/supervisor/conf.d/wizard.conf
```

### 方式 4: Jinja2 模板引擎

```python
from jinja2 import Template

# 读取模板
with open('supervisor_template.conf', 'r') as f:
    template = Template(f.read())

# 渲染模板
config = template.render(
    supervisor_program_name='wizard',
    user='www-data',
    zjvenv3='/data/py/venv3',
    env_name='tayg-test',
    repo_name='wizard',
    port=5005,
    project_dir='/data/zhijian/wizard',
    log_dir='/data/log/python',
    conf_path='auto',
)

# 写入文件
with open('supervisor.conf', 'w') as f:
    f.write(config)
```

## 根据当前项目生成配置

基于 `conf/auto.yaml` 中的配置，变量值应该是：

- `env_name`: `tayg-test` (来自 `enterprise_id`)
- `repo_name`: `zj_setting_svr` (来自 `repo_name`)
- `port`: `29918` (来自 `svr_config.port`)
- `conf_path`: `auto` (对应 `conf/auto.yaml`)

其他变量需要根据实际部署环境设置。
