#!/bin/bash
# Synology Chatbot Claude 重启脚本

INSTALL_DIR="$HOME/SynologyChatbotClaude"

echo "🔄 重启服务..."
cd "$INSTALL_DIR"

# 停止现有服务
pkill -f "gunicorn.*app_v3" 2>/dev/null || true
sleep 2

# 启动服务
source venv/bin/activate
gunicorn -w 2 -b 0.0.0.0:5001 --timeout 120 --daemon app_v3:app

sleep 2

# 检查服务状态
if curl -s http://localhost:5001/health > /dev/null; then
    echo "✅ 服务重启成功"
else
    echo "❌ 服务启动失败，请查看日志:"
    echo "   tail -f $INSTALL_DIR/service.log"
    exit 1
fi
