#!/usr/bin/env python3
"""
Synology Chat - 远程管理 + Claude Code 任务系统
"""

import os
import json
import logging
import subprocess
import psutil
import uuid
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


def create_task(task_type: str, description: str, params: dict = None) -> dict:
    """创建新任务"""
    task_id = str(uuid.uuid4())[:8]
    task = {
        'id': task_id,
        'type': task_type,
        'description': description,
        'params': params or {},
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'result': None,
        'error': None
    }

    task_file = os.path.join(CONFIG['tasks_dir'], f'{task_id}.json')
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, ensure_ascii=False, indent=2)

    logger.info(f"任务已创建: {task_id} - {description}")
    return {
        'success': True,
        'task_id': task_id,
        'task': task
    }


def get_task(task_id: str) -> dict:
    """获取任务状态"""
    task_file = os.path.join(CONFIG['tasks_dir'], f'{task_id}.json')

    if not os.path.exists(task_file):
        return {'success': False, 'error': f'任务不存在: {task_id}'}

    with open(task_file, 'r', encoding='utf-8') as f:
        task = json.load(f)

    return {
        'success': True,
        'task': task
    }


def list_tasks(status: str = None) -> dict:
    """列出所有任务"""
    tasks = []
    for filename in os.listdir(CONFIG['tasks_dir']):
        if filename.endswith('.json'):
            task_file = os.path.join(CONFIG['tasks_dir'], filename)
            with open(task_file, 'r', encoding='utf-8') as f:
                task = json.load(f)
                if status is None or task.get('status') == status:
                    tasks.append(task)

    # 按创建时间排序
    tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    return {
        'success': True,
        'tasks': tasks[:20]  # 最多返回20个
    }


def update_task(task_id: str, **kwargs) -> dict:
    """更新任务状态"""
    task_file = os.path.join(CONFIG['tasks_dir'], f'{task_id}.json')

    if not os.path.exists(task_file):
        return {'success': False, 'error': f'任务不存在: {task_id}'}

    with open(task_file, 'r', encoding='utf-8') as f:
        task = json.load(f)

    task.update(kwargs)
    task['updated_at'] = datetime.now().isoformat()

    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, ensure_ascii=False, indent=2)

    return {'success': True, 'task': task}


def execute_shell_command(command: str, timeout: int = 30) -> dict:
    """执行 Shell 命令"""
    try:
        # 安全检查
        dangerous = ['rm -rf /', 'rm -rf /*', 'mkfs', 'format']
        if any(danger in command.lower() for danger in dangerous):
            return {'success': False, 'error': '危险命令已阻止'}

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.expanduser('~')
        )

        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr,
            'return_code': result.returncode
        }

    except subprocess.TimeoutExpired:
        return {'success': False, 'error': f'命令超时（{timeout}秒）'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_system_info() -> dict:
    """获取系统信息"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            'success': True,
            'data': {
                'CPU使用率': f'{cpu_percent}%',
                '内存使用': f'{memory.percent}% ({memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB)',
                '磁盘使用': f'{disk.percent}% ({disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB)',
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def call_glm_api(message: str) -> str:
    """调用 GLM API"""
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
        return f"抱歉，调用 GLM API 时出错: {str(e)}"


def process_command(message: str) -> str:
    """处理命令"""

    message = message.strip()

    # ========== Claude Code 任务系统 ==========
    if message.startswith('/task '):
        # 创建新任务
        task_desc = message[6:].strip()
        result = create_task('claude_code', task_desc)

        if result['success']:
            task_id = result['task_id']
            return f"""✅ 任务已创建！

任务ID: {task_id}
描述: {task_desc}
状态: 等待处理

📍 使用以下方式处理任务：

方式1 - 使用 Claude Code 手动处理：
   在 Claude Code 中运行：
   /cat ~/SynologyChatbotClaude/tasks/{task_id}.json

方式2 - 查看任务状态：
   /status {task_id}

方式3 - 查看所有任务：
   /tasks"""
        else:
            return f"❌ 创建任务失败: {result.get('error')}"

    elif message.startswith('/status '):
        # 查看任务状态
        task_id = message[8:].strip()
        result = get_task(task_id)

        if result['success']:
            task = result['task']
            status_emoji = {
                'pending': '⏳',
                'processing': '🔄',
                'completed': '✅',
                'failed': '❌'
            }

            output = f"""{status_emoji.get(task['status'], '📝')} 任务状态

ID: {task['id']}
类型: {task['type']}
描述: {task['description']}
状态: {task['status']}
创建时间: {task['created_at']}"""

            if task.get('result'):
                output += f"\n\n📤 结果:\n{task['result']}"
            if task.get('error'):
                output += f"\n\n❌ 错误: {task['error']}"

            return output
        else:
            return f"❌ {result['error']}"

    elif message == '/tasks' or message.startswith('/tasks '):
        # 列出所有任务
        args = message[6:].strip().split() if len(message) > 6 else []
        status_filter = args[0] if args else None

        result = list_tasks(status_filter)

        if result['success'] and result['tasks']:
            tasks_list = result['tasks']
            if not tasks_list:
                return "📝 没有找到任务"

            output = f"📋 任务列表 ({len(tasks_list)} 个任务)\n\n"
            for task in tasks_list[:10]:  # 最多显示10个
                status_emoji = {
                    'pending': '⏳',
                    'processing': '🔄',
                    'completed': '✅',
                    'failed': '❌'
                }
                emoji = status_emoji.get(task['status'], '📝')
                output += f"{emoji} [{task['id']}] {task['description'][:50]}...\n"
                output += f"   状态: {task['status']} | {task['created_at']}\n\n"

            if len(tasks_list) > 10:
                output += f"... 还有 {len(tasks_list) - 10} 个任务\n"

            return output
        else:
            return "📝 暂无任务"

    # ========== Shell 命令系统 ==========
    elif message.startswith('$'):
        parts = message[1:].strip().split(maxsplit=1)
        cmd = parts[0] if parts else ''

        if cmd == 'sys':
            result = get_system_info()
            if result['success']:
                return '\n'.join([f"{k}: {v}" for k, v in result['data'].items()])
            return f"错误: {result['error']}"

        elif cmd == 'ps':
            try:
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cpu': f"{proc.info['cpu_percent']:.1f}%",
                            'memory': f"{proc.info['memory_percent']:.1f}%"
                        })
                    except:
                        pass

                processes.sort(key=lambda x: float(x['cpu'].rstrip('%')), reverse=True)

                output = "进程列表（按 CPU 排序）：\n"
                output += "\n".join([
                    f"PID: {p['pid']:<8} NAME: {p['name']:<20} CPU: {p['cpu']:<8} MEM: {p['memory']}"
                    for p in processes[:10]
                ])
                return output
            except Exception as e:
                return f"错误: {str(e)}"

        elif cmd == 'cat' and len(parts) > 1:
            filepath = parts[1].split()[0]
            try:
                filepath = os.path.expanduser(filepath)
                if not os.path.exists(filepath):
                    return f"❌ 文件不存在: {filepath}"

                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 限制显示长度
                if len(content) > 2000:
                    content = content[:2000] + f"\n... (文件太长，已截断，共 {len(content)} 字符)"

                return f"📄 {filepath}\n\n{content}"
            except Exception as e:
                return f"❌ 错误: {str(e)}"

        elif cmd == 'write' and len(parts) > 1:
            args = parts[1].split(maxsplit=1)
            if len(args) < 2:
                return "用法: $write /path/to/file 内容"
            filepath, content = args[0], args[1]
            try:
                filepath = os.path.expanduser(filepath)
                os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

                return f"✅ 文件已保存: {filepath}"
            except Exception as e:
                return f"❌ 错误: {str(e)}"

        else:
            # 执行任意 Shell 命令
            shell_cmd = message[1:].strip()
            if not shell_cmd:
                return "用法: $ command"

            result = execute_shell_command(shell_cmd)

            output = ""
            if result['output']:
                output = result['output']
            if result['error']:
                output += f"\n错误: {result['error']}" if output else f"错误: {result['error']}"

            return output if output else "命令执行完成，无输出"

    # ========== 系统命令 ==========
    elif message == '/help':
        return """🤖 Synology Chat 远程助手

📋 Claude Code 任务系统：
  /task 你的任务描述    - 创建新任务（等待 Claude Code 处理）
  /status <task_id>     - 查看任务状态
  /tasks                - 查看所有任务

💻 系统管理：
  $sys                  - 系统信息
  $ps                   - 进程列表
  $cat /path/file       - 读取文件
  $write /path/file txt - 写入文件
  $ command             - 执行 Shell 命令

💬 对话：
  直接发送消息即可与 GLM-4 对话

示例：
  /task 帮我分析 ~/Documents 目录
  /status abc123
  $ls -la
  你好"""

    elif message == '/status' or message.startswith('/status'):
        return "用法: /status <任务ID>\n示例: /status abc12345"

    # ========== 普通对话 ==========
    else:
        return call_glm_api(message)


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'features': ['claude_code_tasks', 'shell_commands', 'system_info', 'glm_chat']
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
                'token': request.form.get('token') or request.values.get('token'),
                'user_id': request.form.get('user_id') or request.values.get('user_id'),
                'username': request.form.get('username') or request.values.get('username'),
                'post_id': request.form.get('post_id') or request.values.get('post_id'),
                'timestamp': request.form.get('timestamp') or request.values.get('timestamp'),
                'text': request.form.get('text') or request.values.get('text', '')
            }

        if not data or not data.get('text'):
            logger.warning("收到空请求")
            return jsonify({'error': 'No data received'}), 400

        logger.info(f"收到请求: {data.get('text', '')[:50]}")

        user_message = data.get('text', '').strip()

        # 处理消息
        reply = process_command(user_message)

        # 返回响应
        return jsonify({'text': reply}), 200

    except Exception as e:
        logger.error(f"处理 Webhook 时出错: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Synology Chat - 远程管理服务启动中...")
    logger.info(f"端口: {CONFIG['port']}")
    logger.info(f"任务目录: {CONFIG['tasks_dir']}")
    logger.info("=" * 60)

    app.run(host='0.0.0.0', port=CONFIG['port'], debug=False)
