#!/usr/bin/env python3
"""
Synology Chat - 智能远程管理服务
支持自然语言命令，自动识别意图并执行
"""

import os
import json
import logging
import subprocess
import psutil
import uuid
import re
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from zhipuai import ZhipuAI

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置
CONFIG = {
    'port': int(os.getenv('PORT', 5001)),
    'glm_api_key': os.getenv('GLM_API_KEY', ''),
    'glm_model': os.getenv('GLM_MODEL', 'glm-4-plus'),
    'max_tokens': int(os.getenv('MAX_TOKENS', 4096)),
    'tasks_dir': os.path.expanduser('~/SynologyChatbotClaude/tasks'),
}

# 初始化 API 客户端
glm_client = None
if CONFIG['glm_api_key']:
    glm_client = ZhipuAI(api_key=CONFIG['glm_api_key'])

# 确保任务目录存在
Path(CONFIG['tasks_dir']).mkdir(parents=True, exist_ok=True)


# ===================== 意图识别 =====================

def classify_intent(message: str) -> dict:
    """
    使用 GLM-4 分类用户意图

    返回: {
        'intent': 'chat' | 'system' | 'file' | 'command' | 'complex',
        'confidence': float,
        'extracted': dict  # 提取的参数
    }
    """
    try:
        prompt = f"""你是一个意图分类助手。分析用户消息，判断意图类型。

用户消息: {message}

意图类型:
1. chat - 普通对话、问答、闲聊
2. system - 查询系统信息（CPU、内存、进程等）
3. file - 文件操作（读取、写入、列表）
4. command - 执行具体命令（ls, pwd 等）
5. complex - 复杂任务（需要多步骤）

请以 JSON 格式返回，只返回 JSON，不要其他内容：
{{
    "intent": "意图类型",
    "confidence": 0.95,
    "extracted": {{"path": "路径", "command": "命令"}}
}}"""

        response = glm_client.chat.completions.create(
            model=CONFIG['glm_model'],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.1
        )

        result_text = response.choices[0].message.content.strip()

        # 提取 JSON
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            logger.info(f"意图识别: {result['intent']} (置信度: {result.get('confidence', 0)})")
            return result
        else:
            logger.warning(f"无法解析意图，默认为 chat")
            return {'intent': 'chat', 'confidence': 0.5, 'extracted': {}}

    except Exception as e:
        logger.error(f"意图识别失败: {str(e)}")
        return {'intent': 'chat', 'confidence': 0.0, 'extracted': {}}


# ===================== 系统命令 =====================

def get_system_info() -> dict:
    """获取系统信息"""
    try:
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            'success': True,
            'data': {
                'CPU': f'{cpu}%',
                '内存': f'{memory.percent}% ({memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB)',
                '磁盘': f'{disk.percent}% ({disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB)',
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def list_directory(path: str = None) -> dict:
    """列出目录内容"""
    try:
        target_path = os.path.expanduser(path) if path else os.path.expanduser('~')

        if not os.path.exists(target_path):
            return {'success': False, 'error': f'路径不存在: {target_path}'}

        if not os.path.isdir(target_path):
            return {'success': False, 'error': f'不是目录: {target_path}'}

        entries = []
        for item in os.listdir(target_path):
            item_path = os.path.join(target_path, item)
            if os.path.isdir(item_path):
                entries.append(f"📁 {item}/")
            else:
                size = os.path.getsize(item_path)
                size_str = f"{size / 1024**2:.1f}MB" if size > 1024**2 else f"{size}KB"
                entries.append(f"📄 {item} ({size_str})")

        return {
            'success': True,
            'path': target_path,
            'entries': entries
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def analyze_directory(path: str = None) -> dict:
    """分析目录"""
    try:
        target_path = os.path.expanduser(path) if path else os.path.expanduser('~/Downloads')

        if not os.path.exists(target_path):
            return {'success': False, 'error': f'路径不存在: {target_path}'}

        total_size = 0
        file_count = 0
        dir_count = 0
        largest_files = []

        for root, dirs, files in os.walk(target_path):
            dir_count += len(dirs)
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    total_size += size
                    file_count += 1
                    largest_files.append((file_path, size))
                except:
                    pass

        # 排序找出最大的文件
        largest_files.sort(key=lambda x: x[1], reverse=True)
        top_files = [(f, f"{s / 1024**2:.1f}MB") for f, s in largest_files[:10]]

        return {
            'success': True,
            'path': target_path,
            'summary': {
                '文件数': file_count,
                '目录数': dir_count,
                '总大小': f"{total_size / 1024**3:.2f}GB",
                '最大文件': top_files[0] if top_files else None
            },
            'top_files': top_files
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def execute_shell_command(command: str, timeout: int = 30) -> dict:
    """执行 Shell 命令"""
    try:
        # 安全检查
        dangerous = ['rm -rf /', 'rm -rf /*', 'mkfs', 'format', ':(){:|:&};:']
        if any(danger in command.lower() for danger in dangerous):
            return {'success': False, 'error': '❌ 危险命令已阻止'}

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.expanduser('~')
        )

        output = result.stdout if result.stdout else result.stderr

        return {
            'success': result.returncode == 0,
            'output': output,
            'return_code': result.returncode
        }

    except subprocess.TimeoutExpired:
        return {'success': False, 'error': '❌ 命令超时'}
    except Exception as e:
        return {'success': False, 'error': f'❌ 错误: {str(e)}'}


def call_glm_api(message: str) -> str:
    """调用 GLM API 进行对话"""
    if not glm_client:
        return "⚠️ GLM API 未配置。请在 .env 文件中设置 GLM_API_KEY。\n\n注意：系统命令仍然可以正常使用，如：\n- \"帮我分析下下载目录\"\n- \"看看系统状态\"\n- \"列出文件\""

    try:
        response = glm_client.chat.completions.create(
            model=CONFIG['glm_model'],
            messages=[{"role": "user", "content": message}],
            max_tokens=CONFIG['max_tokens']
        )

        reply = response.choices[0].message.content
        logger.info(f"GLM API 调用成功")
        return reply

    except Exception as e:
        logger.error(f"调用 GLM API 失败: {str(e)}")
        return f"⚠️ 调用 GLM API 出错: {str(e)}\n\n💡 请检查 API 密钥配置或使用系统命令功能。"


# ===================== 智能处理器 =====================

def smart_process(message: str) -> str:
    """智能处理用户消息"""

    message_lower = message.lower()

    # ========== 系统命令（快捷方式）==========
    if message.startswith('$'):
        # 手动命令模式
        return process_command(message)

    # ========== 帮助命令 ==========
    if message in ['/help', '帮助', 'help']:
        return """🤖 Synology Chat 智能助手

💬 **直接说**：
   "帮我分析下下载目录"
   "看看系统状态"
   "列出文件"
   "执行 ls 命令"

📋 **任务系统**：
   /task <任务描述> - 创建复杂任务
   /status <id>      - 查看任务状态
   /tasks            - 查看所有任务

💻 **命令模式**：
   $sys              - 系统信息
   $ps               - 进程列表
   $ command         - 执行命令"""

    # ========== 任务系统命令 ==========
    if message.startswith('/task '):
        task_desc = message[6:].strip()
        result = create_task('claude_code', task_desc)
        if result['success']:
            task_id = result['task_id']
            return f"""✅ 任务已创建！

📋 任务: {task_desc}
🆔 ID: {task_id}

💡 使用 Claude Code 处理：
   /cat ~/SynologyChatbotClaude/tasks/{task_id}.json

📊 查看结果：
   /status {task_id}"""
        return f"❌ 创建任务失败: {result.get('error')}"

    elif message.startswith('/status '):
        task_id = message[8:].strip()
        result = get_task(task_id)
        if result['success']:
            task = result['task']
            status_emoji = {'pending': '⏳', 'processing': '🔄', 'completed': '✅', 'failed': '❌'}
            output = f"{status_emoji.get(task['status'], '📝')} [{task['id']}] {task['description']}\n状态: {task['status']}"
            if task.get('result'):
                output += f"\n\n📤 结果:\n{task['result'][:500]}"
            return output
        return f"❌ {result['error']}"

    elif message == '/tasks':
        result = list_tasks()
        if result['success'] and result['tasks']:
            tasks_list = result['tasks']
            output = f"📋 任务列表 ({len(tasks_list)} 个)\n\n"
            for task in tasks_list[:5]:
                status_emoji = {'pending': '⏳', 'processing': '🔄', 'completed': '✅', 'failed': '❌'}
                output += f"{status_emoji.get(task['status'], '📝')} {task['description'][:40]}... ({task['status']})\n"
            return output
        return "📝 暂无任务"

    # ========== 智能意图识别 + 自动执行 ==========
    logger.info(f"智能处理消息: {message}")

    # 模式 1: 系统信息查询
    system_keywords = ['系统', '状态', 'cpu', '内存', '磁盘', 'system', '状态']
    if any(kw in message_lower for kw in system_keywords):
        result = get_system_info()
        if result['success']:
            return f"📊 **系统状态**\n\n" + "\n".join([f"**{k}**: {v}" for k, v in result['data'].items()])

    # 模式 2: 目录分析
    if '分析' in message and ('目录' in message or '文件夹' in message or '下载' in message):
        # 提取路径
        path = None
        if '下载' in message or 'download' in message_lower:
            path = '~/Downloads'
        elif '文档' in message or 'document' in message_lower:
            path = '~/Documents'
        elif '桌面' in message or 'desktop' in message_lower:
            path = '~/Desktop'

        result = analyze_directory(path)
        if result['success']:
            summary = result['summary']
            output = f"📁 **目录分析** - {result['path']}\n\n"
            output += f"📊 **统计**\n"
            output += f"- 文件数: {summary['文件数']:,}\n"
            output += f"- 目录数: {summary['目录数']:,}\n"
            output += f"- 总大小: {summary['总大小']}\n"

            if summary.get('最大文件'):
                output += f"\n📦 **最大的文件**\n"
                for f, size in result['top_files'][:5]:
                    fname = f.split('/')[-1]
                    output += f"- {fname}: {size}\n"

            return output
        else:
            return f"❌ 分析失败: {result['error']}"

    # 模式 3: 列出文件
    if '列表' in message or '列出' in message or 'ls' in message_lower or '文件' in message:
        # 尝试提取路径
        path = None
        if '下载' in message or 'download' in message_lower:
            path = '~/Downloads'
        elif '当前' in message:
            path = '.'

        result = list_directory(path)
        if result['success']:
            output = f"📁 **{result['path']}**\n\n"
            for entry in result['entries'][:20]:
                output += f"{entry}\n"
            if len(result['entries']) > 20:
                output += f"\n... 还有 {len(result['entries']) - 20} 项"
            return output
        else:
            return f"❌ 列出失败: {result['error']}"

    # 模式 4: 进程查询
    if '进程' in message or 'process' in message_lower or '运行' in message:
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu': f"{proc.info['cpu_percent']:.1f}%",
                        'mem': f"{proc.info['memory_percent']:.1f}%"
                    })
                except:
                    pass

            processes.sort(key=lambda x: float(x['cpu'].rstrip('%')), reverse=True)

            output = "⚙️ **进程列表（按 CPU 排序）**\n\n"
            for p in processes[:10]:
                output += f"PID {p['pid']}: {p['name']} - CPU {p['cpu']} 内存 {p['mem']}\n"
            return output
        except Exception as e:
            return f"❌ 获取进程失败: {str(e)}"

    # 模式 5: 执行命令
    if message.startswith('执行') or message.startswith('run') or message.startswith('运行'):
        # 提取命令
        cmd_match = re.search(r'(执行|run|运行)\s+(.+)', message, re.IGNORECASE)
        if cmd_match:
            cmd = cmd_match.group(2).strip()
            result = execute_shell_command(cmd)
            if result['success']:
                return f"✅ **命令执行成功**\n\n```\n{result['output'][:1000]}\n```"
            else:
                return f"❌ **命令执行失败**\n\n{result.get('error', '未知错误')}"

    # 默认：普通对话
    return call_glm_api(message)


def process_command(message: str) -> str:
    """处理 $ 开头的命令"""
    parts = message[1:].strip().split(maxsplit=1)
    cmd = parts[0] if parts else ''

    if cmd == 'sys':
        result = get_system_info()
        if result['success']:
            return '\n'.join([f"{k}: {v}" for k, v in result['data'].items()])
        return f"错误: {result['error']}"

    elif cmd == 'ps' or cmd == 'top':
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu': f"{proc.info['cpu_percent']:.1f}%"
                    })
                except:
                    pass
            processes.sort(key=lambda x: float(x['cpu'].rstrip('%')), reverse=True)

            output = "进程列表（按 CPU 排序）：\n"
            output += "\n".join([f"PID: {p['pid']:<8} NAME: {p['name']:<20} CPU: {p['cpu']}" for p in processes[:10]])
            return output
        except Exception as e:
            return f"错误: {str(e)}"

    else:
        shell_cmd = message[1:].strip()
        if not shell_cmd:
            return "用法: $ command"

        result = execute_shell_command(shell_cmd)
        output = result.get('output', '') or result.get('error', '')
        return output if output else "命令执行完成，无输出"


def create_task(task_type: str, description: str) -> dict:
    """创建任务"""
    task_id = str(uuid.uuid4())[:8]
    task = {
        'id': task_id,
        'type': task_type,
        'description': description,
        'params': {},
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'result': None,
        'error': None
    }

    task_file = os.path.join(CONFIG['tasks_dir'], f'{task_id}.json')
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, ensure_ascii=False, indent=2)

    logger.info(f"任务已创建: {task_id}")
    return {'success': True, 'task_id': task_id, 'task': task}


def get_task(task_id: str) -> dict:
    """获取任务"""
    task_file = os.path.join(CONFIG['tasks_dir'], f'{task_id}.json')
    if not os.path.exists(task_file):
        return {'success': False, 'error': f'任务不存在: {task_id}'}

    with open(task_file, 'r', encoding='utf-8') as f:
        task = json.load(f)

    return {'success': True, 'task': task}


def list_tasks() -> dict:
    """列出所有任务"""
    tasks = []
    for filename in os.listdir(CONFIG['tasks_dir']):
        if filename.endswith('.json'):
            task_file = os.path.join(CONFIG['tasks_dir'], filename)
            with open(task_file, 'r', encoding='utf-8') as f:
                task = json.load(f)
                tasks.append(task)

    tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return {'success': True, 'tasks': tasks}


# ===================== API 端点 =====================

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'features': ['nlp', 'auto_execute', 'system_monitoring', 'glm_chat']
    })


@app.route('/webhook', methods=['POST'])
def webhook():
    """接收 Synology Chat Webhook"""
    try:
        # 获取请求数据
        content_type = request.content_type

        if content_type and 'application/json' in content_type:
            data = request.get_json()
        else:
            data = {
                'text': request.form.get('text') or request.values.get('text', ''),
                'user_id': request.form.get('user_id') or request.values.get('user_id')
            }

        if not data or not data.get('text'):
            return jsonify({'error': 'No data received'}), 400

        logger.info(f"收到消息: {data.get('text', '')[:50]}")

        user_message = data.get('text', '').strip()

        # 智能处理
        reply = smart_process(user_message)

        return jsonify({'text': reply}), 200

    except Exception as e:
        logger.error(f"处理 Webhook 时出错: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Synology Chat - 智能远程管理服务启动中...")
    logger.info(f"端口: {CONFIG['port']}")
    logger.info("=" * 60)

    app.run(host='0.0.0.0', port=CONFIG['port'], debug=False)
