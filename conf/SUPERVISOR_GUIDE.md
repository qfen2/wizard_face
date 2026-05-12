# Supervisor 部署管理指南

## 目录
1. [安装 Supervisor](#安装-supervisor)
2. [配置文件说明](#配置文件说明)
3. [部署步骤](#部署步骤)
4. [常用命令](#常用命令)
5. [故障排查](#故障排查)
6. [最佳实践](#最佳实践)

---

## 安装 Supervisor

### Ubuntu/Debian

```bash
# 安装 supervisor
sudo apt-get update
sudo apt-get install supervisor

# 启动 supervisor 服务
sudo systemctl start supervisor
sudo systemctl enable supervisor  # 设置开机自启
```

### CentOS/RHEL

```bash
# 安装 supervisor
sudo yum install supervisor

# 启动 supervisor 服务
sudo systemctl start supervisord
sudo systemctl enable supervisord  # 设置开机自启
```

### 验证安装

```bash
# 检查 supervisor 状态
sudo systemctl status supervisor  # Ubuntu/Debian
sudo systemctl status supervisord  # CentOS/RHEL

# 检查 supervisorctl 命令
supervisorctl --version
```

---

## 配置文件说明

### Supervisor 主配置文件

- **Ubuntu/Debian**: `/etc/supervisor/supervisord.conf`
- **CentOS/RHEL**: `/etc/supervisord.conf`

主配置文件通常包含：

```ini
[unix_http_server]
file=/var/run/supervisor.sock

[supervisord]
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[include]
files = /etc/supervisor/conf.d/*.conf  # 包含所有子配置文件
```

### 项目配置文件位置

项目配置文件应放在：
- **Ubuntu/Debian**: `/etc/supervisor/conf.d/`
- **CentOS/RHEL**: `/etc/supervisord.d/`

---

## 部署步骤

### 步骤 1: 准备项目

```bash
# 1. 进入项目目录
cd /path/to/wizard

# 2. 确保虚拟环境已创建
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. 测试应用是否能正常启动
python run.py
# 按 Ctrl+C 停止测试
```

### 步骤 2: 生成 Supervisor 配置

```bash
# 方式 1: 使用自动生成脚本
python generate_supervisor_conf.py

# 方式 2: 手动编辑配置文件
# 复制模板文件并修改
cp supervisor_template.conf supervisor.conf
# 编辑 supervisor.conf，替换所有 {{变量}}
```

### 步骤 3: 创建日志目录

```bash
# 创建日志目录（根据配置中的 log_dir）
sudo mkdir -p /data/log/python
sudo chown $USER:$USER /data/log/python

# 或者使用默认目录
sudo mkdir -p /var/log/wizard
sudo chown $USER:$USER /var/log/wizard
```

### 步骤 4: 安装配置文件

```bash
# 复制配置文件到 supervisor 配置目录
sudo cp supervisor.conf /etc/supervisor/conf.d/wizard.conf

# 设置正确的权限
sudo chmod 644 /etc/supervisor/conf.d/wizard.conf
sudo chown root:root /etc/supervisor/conf.d/wizard.conf
```

### 步骤 5: 重新加载配置

```bash
# 重新读取配置文件
sudo supervisorctl reread

# 输出示例:
# wizard: available

# 更新配置（添加新程序）
sudo supervisorctl update

# 输出示例:
# wizard: added process group
```

### 步骤 6: 启动服务

```bash
# 启动程序
sudo supervisorctl start wizard

# 查看状态
sudo supervisorctl status wizard

# 输出示例:
# wizard                            RUNNING   pid 12345, uptime 0:00:05
```

---

## 常用命令

### 程序管理

```bash
# 启动程序
sudo supervisorctl start wizard

# 停止程序
sudo supervisorctl stop wizard

# 重启程序
sudo supervisorctl restart wizard

# 查看状态
sudo supervisorctl status wizard

# 查看所有程序状态
sudo supervisorctl status

# 重新加载配置（不重启程序）
sudo supervisorctl reread
sudo supervisorctl update
```

### 日志查看

```bash
# 查看实时日志（标准输出）
sudo supervisorctl tail wizard stdout

# 查看实时日志（标准错误）
sudo supervisorctl tail wizard stderr

# 查看最后 100 行日志
sudo supervisorctl tail -100 wizard stdout

# 持续跟踪日志
sudo supervisorctl tail -f wizard stdout

# 直接查看日志文件
tail -f /var/log/wizard/wizard_stdout.log
tail -f /var/log/wizard/wizard_stderr.log
```

### Supervisor 服务管理

```bash
# 启动 supervisor 服务
sudo systemctl start supervisor  # Ubuntu/Debian
sudo systemctl start supervisord  # CentOS/RHEL

# 停止 supervisor 服务
sudo systemctl stop supervisor
sudo systemctl stop supervisord

# 重启 supervisor 服务
sudo systemctl restart supervisor
sudo systemctl restart supervisord

# 查看 supervisor 服务状态
sudo systemctl status supervisor
sudo systemctl status supervisord

# 重新加载 supervisor 配置（不重启服务）
sudo supervisorctl reload
```

### 批量操作

```bash
# 启动所有程序
sudo supervisorctl start all

# 停止所有程序
sudo supervisorctl stop all

# 重启所有程序
sudo supervisorctl restart all

# 清除所有程序的日志
sudo supervisorctl clear all
```

---

## 故障排查

### 1. 程序无法启动

```bash
# 检查配置文件语法
sudo supervisorctl reread

# 查看详细错误信息
sudo supervisorctl tail wizard stderr

# 检查日志文件
cat /var/log/wizard/wizard_stderr.log

# 检查 supervisor 主日志
sudo tail -f /var/log/supervisor/supervisord.log
```

### 2. 程序频繁重启

```bash
# 查看程序状态和重启次数
sudo supervisorctl status wizard

# 查看错误日志
sudo supervisorctl tail wizard stderr

# 检查程序退出码
# 在配置文件中设置 exitcodes=0,2 表示正常退出码
```

### 3. 权限问题

```bash
# 检查文件权限
ls -l /etc/supervisor/conf.d/wizard.conf
ls -l /var/log/wizard/

# 检查运行用户权限
# 确保配置中的 user 有权限访问项目目录和日志目录
```

### 4. 端口被占用

```bash
# 检查端口占用
sudo netstat -tlnp | grep 5005
# 或
sudo ss -tlnp | grep 5005

# 如果端口被占用，修改配置文件中的 port
```

### 5. 配置文件错误

```bash
# 验证配置文件语法
sudo supervisorctl reread

# 如果有错误，会显示具体错误信息
# 修复后再次执行
```

---

## 最佳实践

### 1. 配置文件管理

```bash
# 将配置文件纳入版本控制
git add supervisor.conf
git commit -m "Add supervisor configuration"

# 使用模板文件 + 生成脚本，避免硬编码
```

### 2. 日志管理

```bash
# 定期清理旧日志（添加到 crontab）
# 每天凌晨清理 30 天前的日志
0 0 * * * find /var/log/wizard -name "*.log.*" -mtime +30 -delete
```

### 3. 监控和告警

```bash
# 创建监控脚本检查服务状态
#!/bin/bash
if ! supervisorctl status wizard | grep -q RUNNING; then
    echo "警告: wizard 服务未运行" | mail -s "服务告警" admin@example.com
fi
```

### 4. 部署流程

```bash
#!/bin/bash
# deploy.sh - 部署脚本示例

set -e  # 遇到错误立即退出

echo "1. 拉取最新代码"
git pull

echo "2. 安装依赖"
source .venv/bin/activate
pip install -r requirements.txt

echo "3. 生成配置文件"
python generate_supervisor_conf.py

echo "4. 安装配置文件"
sudo cp supervisor.conf /etc/supervisor/conf.d/wizard.conf

echo "5. 重新加载配置"
sudo supervisorctl reread
sudo supervisorctl update

echo "6. 重启服务"
sudo supervisorctl restart wizard

echo "7. 检查状态"
sleep 2
sudo supervisorctl status wizard

echo "部署完成！"
```

### 5. 多环境配置

```bash
# 为不同环境创建不同的配置文件
# supervisor_dev.conf
# supervisor_test.conf
# supervisor_prod.conf

# 部署时根据环境选择
ENV=${1:-dev}
sudo cp supervisor_${ENV}.conf /etc/supervisor/conf.d/wizard.conf
sudo supervisorctl reread
sudo supervisorctl update
```

### 6. 健康检查

```bash
# 创建健康检查脚本
#!/bin/bash
# health_check.sh

URL="http://localhost:5005/health"  # 假设有健康检查接口
STATUS=$(curl -s -o /dev/null -w "%{http_code}" $URL)

if [ $STATUS -eq 200 ]; then
    echo "服务正常"
    exit 0
else
    echo "服务异常，HTTP 状态码: $STATUS"
    # 可以在这里添加重启逻辑
    # sudo supervisorctl restart wizard
    exit 1
fi
```

---

## 完整部署示例

```bash
#!/bin/bash
# 完整部署流程

# 1. 进入项目目录
cd /data/zhijian/wizard

# 2. 激活虚拟环境
source .venv/bin/activate

# 3. 更新代码（如果使用 Git）
# git pull origin main

# 4. 安装/更新依赖
pip install -r requirements.txt

# 5. 生成 Supervisor 配置
python generate_supervisor_conf.py

# 6. 创建日志目录
sudo mkdir -p /data/log/python
sudo chown $USER:$USER /data/log/python

# 7. 安装配置文件
sudo cp supervisor.conf /etc/supervisor/conf.d/wizard.conf

# 8. 重新加载配置
sudo supervisorctl reread
sudo supervisorctl update

# 9. 重启服务
sudo supervisorctl restart wizard

# 10. 等待服务启动
sleep 3

# 11. 检查状态
echo "=== 服务状态 ==="
sudo supervisorctl status wizard

echo "=== 最近日志 ==="
sudo supervisorctl tail wizard stdout | tail -20

echo "部署完成！"
```

---

## 常见问题 FAQ

### Q: 如何查看程序的完整日志？

A: 使用 `tail -f` 查看日志文件：
```bash
tail -f /var/log/wizard/wizard_stdout.log
tail -f /var/log/wizard/wizard_stderr.log
```

### Q: 如何修改配置后不重启程序？

A: 使用 `reread` 和 `update`，但某些配置修改（如 command）需要重启：
```bash
sudo supervisorctl reread
sudo supervisorctl update
```

### Q: 如何设置程序在系统启动时自动启动？

A: 在配置文件中设置 `autostart=true`，并确保 supervisor 服务开机自启：
```bash
sudo systemctl enable supervisor
```

### Q: 如何限制程序的内存使用？

A: 在配置文件中添加（需要安装 memlimit 插件）：
```ini
memlimit=512MB
```

### Q: 如何设置程序的重启策略？

A: 使用 `autorestart` 参数：
- `autorestart=true`: 总是重启
- `autorestart=false`: 不自动重启
- `autorestart=unexpected`: 只在意外退出时重启

---

## 参考资源

- [Supervisor 官方文档](http://supervisord.org/)
- [Supervisor 配置示例](http://supervisord.org/configuration.html)
- [Supervisor 命令行工具](http://supervisord.org/running.html#supervisorctl-commands)
