#!/bin/bash
# Supervisor 配置安装脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Wizard 项目 Supervisor 配置安装脚本 ===${NC}\n"

# 获取项目路径
PROJECT_DIR=$(pwd)
echo -e "${YELLOW}当前项目路径: ${PROJECT_DIR}${NC}"

# 检查 supervisor 是否安装
if ! command -v supervisorctl &> /dev/null; then
    echo -e "${RED}错误: supervisor 未安装${NC}"
    echo "请先安装 supervisor:"
    echo "  Ubuntu/Debian: sudo apt-get install supervisor"
    echo "  CentOS/RHEL: sudo yum install supervisor"
    exit 1
fi

# 检查配置文件
CONFIG_FILE="supervisor_wizard.conf"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}错误: 找不到配置文件 ${CONFIG_FILE}${NC}"
    exit 1
fi

# 创建日志目录
LOG_DIR="/var/log/wizard"
echo -e "${YELLOW}创建日志目录: ${LOG_DIR}${NC}"
sudo mkdir -p "$LOG_DIR"
sudo chown $USER:$USER "$LOG_DIR" 2>/dev/null || echo "注意: 可能需要手动设置日志目录权限"

# 替换配置文件中的路径
TEMP_CONFIG="/tmp/wizard_supervisor.conf"
sed "s|/path/to/wizard|${PROJECT_DIR}|g" "$CONFIG_FILE" > "$TEMP_CONFIG"

# 获取 supervisor 配置目录
SUPERVISOR_CONF_DIR="/etc/supervisor/conf.d"
if [ ! -d "$SUPERVISOR_CONF_DIR" ]; then
    echo -e "${RED}错误: 找不到 supervisor 配置目录 ${SUPERVISOR_CONF_DIR}${NC}"
    echo "请检查 supervisor 配置"
    exit 1
fi

# 复制配置文件
TARGET_CONFIG="${SUPERVISOR_CONF_DIR}/wizard.conf"
echo -e "${YELLOW}复制配置文件到: ${TARGET_CONFIG}${NC}"
sudo cp "$TEMP_CONFIG" "$TARGET_CONFIG"
rm "$TEMP_CONFIG"

# 设置配置文件权限
sudo chmod 644 "$TARGET_CONFIG"

echo -e "\n${GREEN}配置完成！${NC}\n"
echo -e "${YELLOW}接下来的步骤:${NC}"
echo "1. 检查配置文件: sudo supervisorctl reread"
echo "2. 更新配置: sudo supervisorctl update"
echo "3. 启动程序: sudo supervisorctl start wizard"
echo "4. 查看状态: sudo supervisorctl status wizard"
echo "5. 查看日志: tail -f /var/log/wizard/wizard_stdout.log"
echo ""
echo -e "${YELLOW}常用命令:${NC}"
echo "  启动: sudo supervisorctl start wizard"
echo "  停止: sudo supervisorctl stop wizard"
echo "  重启: sudo supervisorctl restart wizard"
echo "  状态: sudo supervisorctl status wizard"
echo "  日志: sudo supervisorctl tail wizard"
echo "  重载: sudo supervisorctl reload"
