# Synology Chat - 远程管理助手

🤖 通过 Synology Chat 远程管理您的 Mac/Linux 服务器，替代 Tailscale + Termius！

## ✨ 特性

- 🎯 **智能意图识别** - 直接用自然语言描述需求，系统自动识别并执行
- 💬 **通过聊天管理服务器** - 在 Synology Chat 中执行命令、查看系统状态
- 🤖 **AI 驱动** - 集成 GLM-4 或 Claude API，智能理解您的需求
- 📋 **任务系统** - 创建复杂任务，让 AI 助手帮您处理
- 🔒 **安全可靠** - 命令白名单、路径限制，保护您的系统
- 🚀 **简单易用** - 无需记忆命令语法，直接说话即可

## 🎯 功能

### 💻 快捷命令（最快）

直接执行 Shell 命令，最快速的方式：

| 命令 | 说明 |
|------|------|
| `/pwd` | 显示当前目录 |
| `/ls` | 列出当前目录文件 |
| `/whoami` | 显示当前用户 |
| `/df -h` | 查看磁盘使用 |
| `/ps aux` | 查看进程 |
| `/任意命令` | 执行任意 Shell 命令 |

### 🎤 智能自然语言命令（推荐）

直接用自然语言描述，系统自动识别并执行：

| 你说的话 | 系统自动执行 |
|---------|------------|
| "帮我分析下下载目录" | 📊 分析 ~/Downloads 目录 |
| "看看系统状态" | 💻 显示 CPU/内存/磁盘 |
| "列出文件" | 📁 显示当前目录文件列表 |
| "进程情况" | ⚙️ 显示运行中的进程 |
| "执行 ls 命令" | 💻 执行 ls 命令 |

### 传统命令模式
- `$sys` - 查看系统信息（CPU、内存、磁盘）
- `$ps` - 查看进程列表
- `$ command` - 执行任意 Shell 命令

### Claude Code 任务系统
- `/task 任务描述` - 创建新任务
- `/status task_id` - 查看任务状态
- `/tasks` - 查看所有任务

### AI 对话
- 直接发送任何问题，GLM-4 或 Claude 会回复您

## 📦 快速开始

### 1. 安装依赖

#### macOS
```bash
# 安装 Python 3（如果还没有）
brew install python@3.13

# 克隆项目
cd ~
git clone https://github.com/yourusername/SynologyChatbotClaude.git
cd SynologyChatbotClaude

# 创建虚拟环境并安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Linux
```bash
# 安装 Python 3 和 pip
sudo apt update
sudo apt install python3 python3-pip python3-venv

# 克隆项目
cd ~
git clone https://github.com/yourusername/SynologyChatbotClaude.git
cd SynologyChatbotClaude

# 创建虚拟环境并安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
nano .env  # 或使用您喜欢的编辑器
```

**必须配置项：**
```env
# GLM API 密钥（在 https://open.bigmodel.cn/ 获取）
GLM_API_KEY=your_glm_api_key_here

# 或 Claude API 密钥（在 https://console.anthropic.com/ 获取）
# CLAUDE_API_KEY=your_claude_api_key_here
```

### 3. 启动服务

```bash
# 使用 app_v4.py（推荐，支持智能识别）
source venv/bin/activate
gunicorn -w 2 -b 0.0.0.0:5001 --timeout 120 --daemon app_v4:app

# 或使用 app_v3.py
gunicorn -w 2 -b 0.0.0.0:5001 --timeout 120 --daemon app_v3:app

# 查看日志
tail -f service.log
```

### 4. 配置 Synology Chat

#### 创建 Outgoing Webhook

1. 打开 **Synology Chat**
2. 进入您要使用的频道
3. 点击 **频道设置** → **Integration**
4. 点击 **Outgoing Webhook** → **Create**
5. 填写配置：
   - **Name**: 远程管理助手
   - **URL**: `http://your-mac-ip:5001/webhook`
   - **Trigger**: 选择 "All messages"
6. **保存**

#### 获取您的 Mac IP 地址

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Linux
ip addr show | grep "inet " | grep -v 127.0.0.1
```

## 📝 使用示例

### 💻 快捷命令（最快）

```
你: /pwd
机器人: ✅ 命令执行成功

       /Users/placid

你: /ls -la
机器人: ✅ 命令执行成功

       total 32
       drwxr-xr-x  8 placid  staff   256 Jan 28 12:00 .
       drwxr-xr-x  3 placid  staff    96 Jan 28 10:00 ..
       -rw-r--r--  1 placid  staff  1234 Jan 28 11:30 file.txt
       drwxr-xr-x  2 placid  staff    64 Jan 28 09:15 Documents

你: /whoami
机器人: ✅ 命令执行成功

       placid
```

### 🎤 智能模式（推荐）

```
你: 帮我分析下下载目录
机器人: 📁 目录分析 - /Users/xxx/Downloads
       📊 统计
       - 文件数: 152
       - 目录数: 24
       - 总大小: 2.3GB

你: 看看系统状态
机器人: 📊 系统状态

       CPU
       ▓▓▓▓▓░░░░░░░░░░░░░░░ 25.4%

       内存
       ▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░ 75% (12GB / 16GB)

       磁盘
       ▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░ 55% (125GB / 228GB)

你: 列出文件
机器人: 📁 /Users/xxx
       📄 file1.txt (12KB)
       📁 Documents/
       📁 Downloads/
```

### 传统命令模式

```
你: $sys
机器人: CPU使用率: 25%
      内存使用: 75% (12GB / 16GB)
      磁盘使用: 55% (125GB / 228GB)

你: $ps
机器人: 进程列表（按 CPU 排序）：
      PID: 1234    Chrome    45.2%
      PID: 5678    Firefox   12.1%
```

### 创建任务

```
你: /task 帮我分析 ~/Downloads 目录中的文件
机器人: ✅ 任务已创建！
      任务ID: abc123
      状态: 等待处理

      使用以下方式处理任务：
      在 Claude Code 中运行：
      /cat ~/SynologyChatbotClaude/tasks/abc123.json

you: /status abc123
机器人: ✅ 任务完成
      结果:
      - 总文件数: 152
      - 最大文件: movie.mp4 (2.3GB)
      ...
```

### AI 对话

```
you: 解释一下 Docker 的原理
机器人: (GLM-4 或 Claude 的详细解释)
```

## 🔧 服务管理

### 启动服务
```bash
cd ~/SynologyChatbotClaude
source venv/bin/activate
gunicorn -w 2 -b 0.0.0.0:5001 --timeout 120 --daemon app_v3:app
```

### 停止服务
```bash
pkill -f gunicorn
```

### 重启服务
```bash
pkill -f gunicorn
sleep 2
cd ~/SynologyChatbotClaude
source venv/bin/activate
gunicorn -w 2 -b 0.0.0.0:5001 --timeout 120 --daemon app_v3:app
```

### 查看日志
```bash
tail -f ~/SynologyChatbotClaude/service.log
```

### 设置开机自启（macOS）

创建 `~/Library/LaunchAgents/com.synologychatbot.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.synologychatbot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/SynologyChatbotClaude/venv/bin/gunicorn</string>
        <string>-w</string>
        <string>2</string>
        <string>-b</string>
        <string>0.0.0.0:5001</string>
        <string>--timeout</string>
        <string>120</string>
        <string>app_v3:app</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/SynologyChatbotClaude</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/SynologyChatbotClaude/service.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/SynologyChatbotClaude/error.log</string>
</dict>
</plist>
```

加载服务：
```bash
# 替换 YOUR_USERNAME 为您的用户名
nano ~/Library/LaunchAgents/com.synologychatbot.plist
# 粘贴上面的内容，并替换路径

# 加载服务
launchctl load ~/Library/LaunchAgents/com.synologychatbot.plist

# 启动服务
launchctl start com.synologychatbot
```

## 🔐 安全建议

1. **修改默认端口** - 在 `.env` 中修改 `PORT`
2. **限制允许的命令** - 在 `ALLOWED_COMMANDS` 中只添加您需要的命令
3. **限制访问路径** - 在 `ALLOWED_PATHS` 中只设置必要的目录
4. **使用防火墙** - 只允许 Synology NAS 访问
5. **定期更新** - 保持依赖包最新

## 🛠️ 故障排查

### 服务无法启动
```bash
# 检查端口是否被占用
lsof -i :5001

# 查看详细错误
cd ~/SynologyChatbotClaude
source venv/bin/activate
python app_v3.py
```

### 无法连接到服务
- 检查防火墙设置
- 确认 Mac 和 Synology NAS 在同一网络
- 尝试用 `curl http://localhost:5001/health` 测试

### API 调用失败
- 检查 API 密钥是否正确
- 查看日志：`tail -f service.log`
- 确认 API 配额未用尽

## 📚 项目结构

```
SynologyChatbotClaude/
├── app_v3.py              # 主程序
├── requirements.txt        # Python 依赖
├── .env.example           # 配置模板
├── .gitignore             # Git 忽略文件
├── README.md              # 说明文档
├── install.sh             # 安装脚本
├── tasks/                 # 任务目录
│   └── README.md          # 任务说明
└── venv/                  # Python 虚拟环境（不提交）
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [Synology Chat](https://www.synology.com/en-us/dsm/chat) - 强大的团队协作工具
- [GLM-4](https://open.bigmodel.cn/) - 智谱 AI 的大语言模型
- [Claude](https://www.anthropic.com/) - Anthropic 的 AI 助手

---

⭐ 如果这个项目对您有帮助，请给个 Star！
