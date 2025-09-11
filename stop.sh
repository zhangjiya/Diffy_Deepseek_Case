#!/bin/bash

# 测试用例生成Web平台停止脚本（简化版）

PID_FILE="web_app.pid"

if [ -f "$PID_FILE" ]; then
    pid=$(cat "$PID_FILE")
    if ps -p $pid > /dev/null 2>&1; then
        echo "停止应用 (PID: $pid)..."
        kill $pid
        rm -f "$PID_FILE"
        echo "✓ 应用已停止"
    else
        echo "进程不存在，清理PID文件"
        rm -f "$PID_FILE"
    fi
else
    echo "未找到PID文件，应用可能未运行"
fi 