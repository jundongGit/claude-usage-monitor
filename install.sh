#\!/bin/bash
# Claude Usage Monitor - 一键安装脚本

set -e  # 遇到错误立即退出

echo "🚀 Claude Usage Monitor 安装脚本"
echo "================================"
echo ""

# 颜色定义
GREEN='[0;32m'
YELLOW='[1;33m'
RED='[0;31m'
NC='[0m' # No Color

# 检查是否在 macOS 上运行
if [[ "$OSTYPE" \!= "darwin"* ]]; then
    echo "${RED}❌ 错误：此应用仅支持 macOS${NC}"
    exit 1
fi

echo "${YELLOW}📋 检查前置条件...${NC}"

# 检查 Python 版本
if \! command -v python3 &> /dev/null; then
    echo "${RED}❌ 未找到 Python 3${NC}"
    echo "请先安装 Python 3.8 或更高版本"
    echo "访问: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d" " -f2 | cut -d"." -f1,2)
echo "${GREEN}✓${NC} Python 版本: $PYTHON_VERSION"

# 检查 pip
if \! command -v pip3 &> /dev/null; then
    echo "${RED}❌ 未找到 pip3${NC}"
    exit 1
fi
echo "${GREEN}✓${NC} pip3 已安装"

echo ""
echo "${YELLOW}📦 安装依赖包...${NC}"

# 安装依赖
if pip3 install -r requirements.txt --quiet; then
    echo "${GREEN}✓${NC} 依赖安装成功"
else
    echo "${RED}❌ 依赖安装失败${NC}"
    echo "尝试使用以下命令手动安装："
    echo "  pip3 install rumps requests"
    exit 1
fi

echo ""
echo "${GREEN}✅ 安装完成！${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📌 ${YELLOW}下一步：${NC}"
echo ""
echo "1. 启动应用："
echo "   ${GREEN}python3 main.py${NC}"
echo ""
echo "2. 首次使用需要配置 Cookie 和组织 ID"
echo "   详细步骤请查看 README.md"
echo ""
echo "3. 要启用开机自动启动："
echo "   启动应用后，点击菜单中的 ${GREEN}🚀 开机自动启动${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "需要帮助？查看 README.md 或提交 Issue"
echo ""

# 询问是否立即启动
read -p "现在启动应用吗？[Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    echo ""
    echo "${GREEN}🎉 正在启动 Claude Usage Monitor...${NC}"
    echo ""
    python3 main.py
else
    echo ""
    echo "稍后运行以下命令启动应用："
    echo "  ${GREEN}python3 main.py${NC}"
    echo ""
fi
