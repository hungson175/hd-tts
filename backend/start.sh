#!/bin/bash
# VietVoice TTS Server Startup Script
#
# Usage:
#   ./start.sh              # Start with 2 high-quality workers (default)
#   ./start.sh 3            # Start with 3 high-quality workers
#   ./start.sh "2h,1f"      # Start with 2 high-quality + 1 fast worker
#   ./start.sh stop         # Stop all components
#   ./start.sh status       # Show status

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$SCRIPT_DIR/logs"
PID_DIR="$SCRIPT_DIR/pids"

# Configuration
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
API_PORT="${API_PORT:-17603}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Create directories
mkdir -p "$LOG_DIR" "$PID_DIR"

check_redis() {
    # Try redis-cli first, then try via Docker
    if redis-cli ping > /dev/null 2>&1; then
        return 0
    fi
    # Check if Redis is available via Docker
    if docker exec mhub2-redis-dev redis-cli ping > /dev/null 2>&1; then
        return 0
    fi
    # Check any Redis container on port 6379
    if nc -z localhost 6379 2>/dev/null; then
        return 0
    fi
    return 1
}

cleanup_gpu() {
    # Kill zombie Python workers using GPU memory
    log_info "Checking for zombie GPU processes..."

    # Get PIDs of Python processes using GPU (exclude system processes)
    GPU_PIDS=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | tr -d ' ')

    if [ -n "$GPU_PIDS" ]; then
        for PID in $GPU_PIDS; do
            # Check if it's a Python process
            if ps -p $PID -o comm= 2>/dev/null | grep -q python; then
                log_warn "Killing zombie Python process using GPU (PID: $PID)"
                kill -9 $PID 2>/dev/null || true
            fi
        done
        sleep 1
        log_info "GPU cleanup complete"
    else
        log_info "No zombie GPU processes found"
    fi
}

start_redis() {
    if check_redis; then
        log_info "Redis is already running"
        return 0
    fi

    log_info "Starting Redis..."
    if command -v redis-server &> /dev/null; then
        redis-server --daemonize yes --logfile "$LOG_DIR/redis.log"
        sleep 1
        if check_redis; then
            log_info "Redis started"
        else
            log_error "Failed to start Redis"
            exit 1
        fi
    elif command -v docker &> /dev/null; then
        log_info "Starting Redis via Docker..."
        docker run -d --name redis-tts -p 6379:6379 redis:7-alpine
        sleep 2
        if check_redis; then
            log_info "Redis started via Docker"
        else
            log_error "Failed to start Redis via Docker"
            exit 1
        fi
    else
        log_error "Redis is not installed. Install with: sudo apt install redis-server"
        exit 1
    fi
}

start_gateway() {
    log_info "Starting API Gateway on port $API_PORT..."

    source "$VENV_DIR/bin/activate"

    REDIS_URL="$REDIS_URL" API_PORT="$API_PORT" \
        nohup python "$SCRIPT_DIR/gateway/main.py" \
        > "$LOG_DIR/gateway.log" 2>&1 &

    echo $! > "$PID_DIR/gateway.pid"
    log_info "Gateway started (PID: $(cat "$PID_DIR/gateway.pid"))"
}

# Parse worker config: "2h,1f" or just a number
parse_worker_config() {
    local config="$1"
    HIGH_WORKERS=0
    FAST_WORKERS=0

    if [[ "$config" =~ ^[0-9]+$ ]]; then
        # Just a number, all high quality
        HIGH_WORKERS="$config"
    elif [[ "$config" =~ ([0-9]+)h ]]; then
        # Parse high workers
        HIGH_WORKERS="${BASH_REMATCH[1]}"
    fi

    if [[ "$config" =~ ([0-9]+)f ]]; then
        # Parse fast workers
        FAST_WORKERS="${BASH_REMATCH[1]}"
    fi

    # Default: 2 high quality if nothing specified
    if [ "$HIGH_WORKERS" -eq 0 ] && [ "$FAST_WORKERS" -eq 0 ]; then
        HIGH_WORKERS=2
    fi
}

start_workers() {
    local total=$((HIGH_WORKERS + FAST_WORKERS))
    log_info "Starting $total TTS workers ($HIGH_WORKERS high-quality, $FAST_WORKERS fast)..."

    source "$VENV_DIR/bin/activate"

    local worker_num=0

    # Start high-quality workers
    for i in $(seq 1 "$HIGH_WORKERS"); do
        worker_num=$((worker_num + 1))
        local worker_id="worker-high-$i"

        WORKER_ID="$worker_id" REDIS_URL="$REDIS_URL" QUALITY="high" \
            nohup python "$SCRIPT_DIR/worker/main.py" \
            > "$LOG_DIR/$worker_id.log" 2>&1 &

        echo $! > "$PID_DIR/$worker_id.pid"
        log_info "High-quality worker $i started (PID: $(cat "$PID_DIR/$worker_id.pid"), NFE=32)"

        # Stagger worker starts to avoid GPU contention during model loading
        if [ "$worker_num" -lt "$total" ]; then
            log_info "Waiting 10s before starting next worker..."
            sleep 10
        fi
    done

    # Start fast workers
    for i in $(seq 1 "$FAST_WORKERS"); do
        worker_num=$((worker_num + 1))
        local worker_id="worker-fast-$i"

        WORKER_ID="$worker_id" REDIS_URL="$REDIS_URL" QUALITY="fast" \
            nohup python "$SCRIPT_DIR/worker/main.py" \
            > "$LOG_DIR/$worker_id.log" 2>&1 &

        echo $! > "$PID_DIR/$worker_id.pid"
        log_info "Fast worker $i started (PID: $(cat "$PID_DIR/$worker_id.pid"), NFE=16)"

        # Stagger worker starts
        if [ "$worker_num" -lt "$total" ]; then
            log_info "Waiting 10s before starting next worker..."
            sleep 10
        fi
    done
}

stop_component() {
    local name="$1"
    local pid_file="$PID_DIR/$name.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping $name (PID: $pid)..."
            kill "$pid"
            rm -f "$pid_file"
        else
            log_warn "$name not running (stale PID file)"
            rm -f "$pid_file"
        fi
    else
        log_warn "$name PID file not found"
    fi
}

stop_all() {
    log_info "Stopping all components..."

    # Stop workers
    for pid_file in "$PID_DIR"/worker-*.pid; do
        if [ -f "$pid_file" ]; then
            local name=$(basename "$pid_file" .pid)
            stop_component "$name"
        fi
    done

    # Stop gateway
    stop_component "gateway"

    log_info "All components stopped"
}

show_status() {
    echo ""
    echo "=== VietVoice TTS Server Status ==="
    echo ""

    # Redis
    if check_redis; then
        echo -e "Redis:    ${GREEN}Running${NC}"
    else
        echo -e "Redis:    ${RED}Stopped${NC}"
    fi

    # Gateway
    if [ -f "$PID_DIR/gateway.pid" ] && kill -0 "$(cat "$PID_DIR/gateway.pid")" 2>/dev/null; then
        echo -e "Gateway:  ${GREEN}Running${NC} (PID: $(cat "$PID_DIR/gateway.pid"), Port: $API_PORT)"
    else
        echo -e "Gateway:  ${RED}Stopped${NC}"
    fi

    # Workers
    local high_workers=0
    local fast_workers=0
    for pid_file in "$PID_DIR"/worker-*.pid; do
        if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            if [[ "$pid_file" == *"high"* ]]; then
                high_workers=$((high_workers + 1))
            elif [[ "$pid_file" == *"fast"* ]]; then
                fast_workers=$((fast_workers + 1))
            fi
        fi
    done
    echo -e "Workers:  ${GREEN}$high_workers high-quality${NC}, ${BLUE}$fast_workers fast${NC}"

    # Queue stats (if Redis is running)
    if check_redis; then
        echo ""
        echo "=== Queue Stats ==="
        local high_queue=$(redis-cli LLEN tts:jobs:high 2>/dev/null || echo "0")
        local fast_queue=$(redis-cli LLEN tts:jobs:fast 2>/dev/null || echo "0")
        local high_workers_redis=$(redis-cli KEYS "tts:worker:*high*" 2>/dev/null | wc -l || echo "0")
        local fast_workers_redis=$(redis-cli KEYS "tts:worker:*fast*" 2>/dev/null | wc -l || echo "0")
        echo "High-quality queue: $high_queue jobs"
        echo "Fast queue:         $fast_queue jobs"
        echo "Registered workers: $high_workers_redis high, $fast_workers_redis fast"
    fi

    echo ""
}

case "$1" in
    stop)
        stop_all
        ;;
    status)
        show_status
        ;;
    *)
        # Parse worker configuration
        parse_worker_config "${1:-2}"

        log_info "Starting VietVoice TTS Server"
        log_info "Workers: $HIGH_WORKERS high-quality (NFE=32), $FAST_WORKERS fast (NFE=16)"
        log_info "Project dir: $PROJECT_DIR"
        log_info "Logs dir: $LOG_DIR"

        # Check venv
        if [ ! -d "$VENV_DIR" ]; then
            log_error "Virtual environment not found at $VENV_DIR"
            log_error "Create it with: python3 -m venv venv && source venv/bin/activate && pip install -e ."
            exit 1
        fi

        cleanup_gpu  # Kill zombie Python processes using GPU
        start_redis
        start_gateway
        sleep 2  # Wait for gateway to start
        start_workers

        echo ""
        log_info "Server started!"
        echo ""
        echo "  API:  http://localhost:$API_PORT"
        echo "  Docs: http://localhost:$API_PORT/docs"
        echo ""
        echo "  Workers:"
        echo "    - High-quality (NFE=32): $HIGH_WORKERS instances"
        echo "    - Fast (NFE=16):         $FAST_WORKERS instances"
        echo ""
        echo "  Logs: $LOG_DIR/"
        echo ""
        echo "  Stop with: $0 stop"
        echo "  Status:    $0 status"
        echo ""
        ;;
esac
