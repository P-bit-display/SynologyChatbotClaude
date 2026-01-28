#!/bin/bash
# Synology Chatbot Claude 安装脚本

set -e

echo "🤖 Synology Chatbot Claude 安装向导"
echo "======================================"
echo ""

# 检测操作系统
OS="$(uname -s)"
if [[ "$OS" == "Darwin" ]]; then
    PLATFORM="macOS"
elif [[ "$OS" == "Linux" ]]; then
    PLATFORM="Linux"
else
    echo "❌ 不支持的操作系统: $OS"
    exit 1
fi

echo "📱 检测到平台: $PLATFORM"
echo ""

# 检查 Python 3
echo "🔍 检查 Python 3..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo "✅ 找到 Python $PYTHON_VERSION"
else
    echo "❌ 未找到 Python 3"
    if [[ "$PLATFORM" == "macOS" ]]; then
        echo "请运行: brew install python@3.13"
    else
        echo "请运行: sudo apt install python3"
    fi
    exit 1
fi
echo ""

# 检查 pip
echo "🔍 检查 pip..."
if command -v pip3 &> /dev/null; then
    echo "✅ 找到 pip3"
else
    echo "⚠️  未找到 pip3，尝试安装..."
    if [[ "$PLATFORM" == "macOS" ]]; then
        brew install python3
    else
        sudo apt install python3-pip
    fi
fi
echo ""

# 获取安装目录
INSTALL_DIR="$HOME/SynologyChatbotClaude"
echo "📁 安装目录: $INSTALL_DIR"
echo ""

# 创建虚拟环境
if [ -d "$INSTALL_DIR/venv" ]; then
    echo "⚠️  虚拟环境已存在，跳过创建"
else
    echo "🔧 创建 Python 虚拟环境..."
    cd "$INSTALL_DIR"
    python3 -m venv venv
    echo "✅ 虚拟环境创建完成"
fi
echo ""

# 安装依赖
echo "📦 安装 Python 依赖..."
source "$INSTALL_DIR/venv/bin/activate"
pip install --upgrade pip -q
pip install -r "$INSTALL_DIR/requirements.txt" -q
echo "✅ 依赖安装完成"
echo ""

# 检查 .env 文件
if [ -f "$INSTALL_DIR/.env" ]; then
    echo "⚠️  配置文件 .env 已存在"
else
    echo "📝 创建配置文件..."
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"

    echo ""
    echo "========================================="
    echo "⚙️  请配置您的 API 密钥"
    echo "========================================="
    echo ""
    echo "编辑 $INSTALL_DIR/.env 文件，填入以下信息："
    echo ""
    echo "1. GLM API 密钥（推荐）"
    echo "   访问: https://open.bigmodel.cn/"
    echo "   获取 API 密钥并填入 GLM_API_KEY"
    echo ""
    echo "2. 或 Claude API 密钥"
    echo "   访问: https://console.anthropic.com/"
    echo "   获取 API 密钥并填入 CLAUDE_API_KEY"
    echo ""

    # 询问是否现在编辑
    read -p "是否现在编辑配置文件？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} "$INSTALL_DIR/.env"
    else
        echo "请稍后手动编辑: nano $INSTALL_DIR/.env"
    fi
fi
echo ""

# 创建任务目录
mkdir -p "$INSTALL_DIR/tasks"
echo "✅ 任务目录已创建: $INSTALL_DIR/tasks"
echo ""

# 启动服务
echo "========================================="
echo "🚀 准备启动服务"
echo "========================================="
echo ""

read -p "是否现在启动服务？(y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 停止现有服务
    pkill -f "gunicorn.*app_v3" 2>/dev/null || true
    sleep 2

    # 启动服务
    cd "$INSTALL_DIR"
    source venv/bin/activate
    gunicorn -w 2 -b 0.0.0.0:5001 --timeout 120 --daemon app_v3:app

    sleep 2

    # 检查服务状态
    if curl -s http://localhost:5001/health > /dev/null; then
        echo "✅ 服务启动成功！"
        echo ""
        echo "========================================="
        echo "📋 后续步骤"
        echo "========================================="
        echo ""
        echo "1. 获取您的 IP 地址："
        if [[ "$PLATFORM" == "macOS" ]]; then
            echo "   ifconfig | grep \"inet \" | grep -v 127.0.0.1"
        else
            echo "   ip addr show | grep \"inet \" | grep -v 127.0.0.1"
        fi
        echo ""
        echo "2. 在 Synology Chat 中配置 Outgoing Webhook:"
        echo "   URL: http://YOUR_IP:5001/webhook"
        echo ""
        echo "3. 查看日志:"
        echo "   tail -f $INSTALL_DIR/service.log"
        echo ""
        echo "4. 管理服务:"
        echo "   停止: pkill -f gunicorn"
        echo "   重启: $INSTALL_DIR/restart.sh"
        echo ""
    else
        echo "❌ 服务启动失败，请查看日志:"
        echo "   tail -f $INSTALL_DIR/service.log"
        exit 1
    fi
else
    echo ""
    echo "稍后手动启动服务:"
    echo "  cd $INSTALL_DIR"
    echo "  source venv/bin/activate"
    echo "  gunicorn -w 2 -b 0.0.0.0:5001 --timeout 120 --daemon app_v3:app"
fi

echo ""
echo "🎉 安装完成！"
echo ""
echo "如有问题，请查看: $INSTALL_DIR/README.md"
