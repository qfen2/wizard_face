#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成 Supervisor 配置文件
从 conf/auto.yaml 和系统配置中读取变量，替换模板文件中的变量
"""

import os
import yaml
from pathlib import Path


def load_config():
    """加载配置文件"""
    config_file = Path('conf/auto.yaml')
    if not config_file.exists():
        print(f"警告: 找不到配置文件 {config_file}")
        return {}
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def get_variables(config):
    """获取所有变量"""
    # 从配置文件读取
    env_name = config.get('enterprise_id', 'tayg-test')
    repo_name = config.get('repo_name', 'wizard')
    svr_config = config.get('svr_config', {})
    port = svr_config.get('port', 5005)
    
    # 从环境变量或默认值获取
    variables = {
        'supervisor_program_name': os.environ.get('SUPERVISOR_PROGRAM_NAME', repo_name),
        'user': os.environ.get('SUPERVISOR_USER', 'www-data'),
        'zjvenv3': os.environ.get('ZJVENV3', '/data/py/venv3'),
        'env_name': env_name,
        'repo_name': repo_name,
        'port': port,
        'project_dir': os.environ.get('PROJECT_DIR', '/data/zhijian/wizard'),
        'log_dir': os.environ.get('LOG_DIR', '/data/log/python'),
        'conf_path': os.environ.get('CONF_PATH', 'auto'),
    }
    
    return variables


def generate_config(template_file='supervisor_template.conf', output_file='supervisor.conf'):
    """生成配置文件"""
    # 加载配置
    config = load_config()
    variables = get_variables(config)
    
    # 读取模板
    template_path = Path(template_file)
    if not template_path.exists():
        print(f"错误: 找不到模板文件 {template_file}")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 替换变量
    for key, value in variables.items():
        template = template.replace('{{' + key + '}}', str(value))
    
    # 写入配置文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(template)
    
    print(f"✓ Supervisor 配置文件已生成: {output_file}")
    print("\n变量值:")
    for key, value in variables.items():
        print(f"  {key}: {value}")
    
    return True


if __name__ == '__main__':
    import sys
    
    template_file = sys.argv[1] if len(sys.argv) > 1 else 'supervisor_template.conf'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'supervisor.conf'
    
    success = generate_config(template_file, output_file)
    sys.exit(0 if success else 1)
