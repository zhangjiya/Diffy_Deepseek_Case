#!/bin/bash

# 测试用例生成平台启动脚本
# 使用方法: ./start.sh [start|stop|restart|status|logs|clean]

# 配置
APP_NAME="测试用例生成平台"
PID_FILE="web_app.pid"
LOG_FILE="logs/web_app.log"
PORT=5002

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python环境
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "未找到Python环境，请先安装Python 3.7+"
        exit 1
    fi
    log_info "使用Python命令: $PYTHON_CMD"
}

# 检查依赖
check_dependencies() {
    log_info "检查Python依赖..."
    if [ ! -f "requirements.txt" ]; then
        log_warning "未找到requirements.txt文件"
        return
    fi
    
    if ! $PYTHON_CMD -c "import yaml, flask, requests" 2>/dev/null; then
        log_warning "缺少必要的Python依赖，正在安装..."
        $PYTHON_CMD -m pip install -r requirements.txt
    else
        log_success "Python依赖检查通过"
    fi
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    mkdir -p logs
    mkdir -p output
    mkdir -p output/tmp
    log_success "目录创建完成"
}

# 启动应用
start_app() {
    log_info "启动 $APP_NAME..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            log_warning "$APP_NAME 已经在运行 (PID: $PID)"
            return
        else
            log_warning "发现无效的PID文件，正在清理..."
            rm -f "$PID_FILE"
        fi
    fi
    
    check_python
    check_dependencies
    create_directories
    
    # 启动应用
    nohup $PYTHON_CMD web_app.py > "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    
    # 等待应用启动
    sleep 3
    
    if ps -p $PID > /dev/null 2>&1; then
        log_success "$APP_NAME 启动成功 (PID: $PID)"
        log_info "访问地址: http://localhost:$PORT"
        log_info "日志文件: $LOG_FILE"
    else
        log_error "$APP_NAME 启动失败，请检查日志文件: $LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# 停止应用
stop_app() {
    log_info "停止 $APP_NAME..."
    
    if [ ! -f "$PID_FILE" ]; then
        log_warning "$APP_NAME 未在运行"
        return
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        sleep 2
        
        if ps -p $PID > /dev/null 2>&1; then
            log_warning "应用未正常停止，强制终止..."
            kill -9 $PID
        fi
        
        rm -f "$PID_FILE"
        log_success "$APP_NAME 已停止"
    else
        log_warning "$APP_NAME 未在运行"
        rm -f "$PID_FILE"
    fi
}

# 重启应用
restart_app() {
    log_info "重启 $APP_NAME..."
    stop_app
    sleep 2
    start_app
}

# 查看状态
check_status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            log_success "$APP_NAME 正在运行 (PID: $PID)"
            log_info "端口: $PORT"
            log_info "日志文件: $LOG_FILE"
        else
            log_error "$APP_NAME 进程不存在，但PID文件存在"
            rm -f "$PID_FILE"
        fi
    else
        log_warning "$APP_NAME 未在运行"
    fi
}

# 查看日志
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        log_info "显示 $APP_NAME 日志 (最后50行):"
        echo "----------------------------------------"
        tail -n 50 "$LOG_FILE"
        echo "----------------------------------------"
        log_info "实时日志查看: tail -f $LOG_FILE"
    else
        log_error "日志文件不存在: $LOG_FILE"
    fi
}

# 清理临时文件
clean_temp() {
    log_info "清理临时文件..."
    rm -rf output/tmp/*
    rm -f web_app.pid
    log_success "临时文件清理完成"
}

# 显示帮助信息
show_help() {
    echo "使用方法: $0 [命令]"
    echo ""
    echo "可用命令:"
    echo "  start    启动应用"
    echo "  stop     停止应用"
    echo "  restart  重启应用"
    echo "  status   查看应用状态"
    echo "  logs     查看应用日志"
    echo "  clean    清理临时文件"
    echo "  help     显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start      # 启动应用"
    echo "  $0 logs       # 查看日志"
    echo "  $0 restart    # 重启应用"
}

# 主逻辑
case "${1:-start}" in
    start)
        start_app
        ;;
    stop)
        stop_app
        ;;
    restart)
        restart_app
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs
        ;;
    clean)
        clean_temp
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "未知命令: $1"
        show_help
        exit 1
        ;;
esac 