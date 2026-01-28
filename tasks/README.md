# 任务目录

此目录用于存储由 Claude Code 处理的任务。

## 任务文件格式

每个任务是一个 JSON 文件，包含以下字段：

```json
{
  "id": "任务ID",
  "type": "任务类型",
  "description": "任务描述",
  "params": {},
  "status": "pending | processing | completed | failed",
  "created_at": "创建时间",
  "updated_at": "更新时间",
  "result": "任务结果",
  "error": "错误信息"
}
```

## 使用方式

### 在 Synology Chat 中创建任务

```
/task 帮我分析系统状态
```

### 在 Claude Code 中读取任务

```
/cat ~/SynologyChatbotClaude/tasks/任务ID.json
```

### 处理完成后更新任务

Claude Code 会自动更新任务状态和结果。

### 在 Synology Chat 中查看结果

```
/status 任务ID
```
