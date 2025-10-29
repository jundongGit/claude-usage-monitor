#!/bin/bash
# Claude Usage Monitor - 环境设置脚本

cd "/Users/jundong/Documents/FREEAI/Dev/Claude usage"

echo "正在创建虚拟环境..."
python3 -m venv venv

echo "正在激活虚拟环境..."
source venv/bin/activate

echo "正在安装依赖..."
pip install -r requirements.txt

echo ""
echo "✅ 环境设置完成！"
echo ""
echo "要运行应用，请执行："
echo "  source venv/bin/activate"
echo "  python3 main.py"
