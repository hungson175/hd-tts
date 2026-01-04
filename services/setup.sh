#!/bin/bash
# VietVoice TTS - Systemd Services Setup Script
#
# Usage:
#   ./setup.sh install      # Install and enable all services
#   ./setup.sh start        # Start all services
#   ./setup.sh stop         # Stop all services
#   ./setup.sh status       # Show status of all services
#   ./setup.sh uninstall    # Remove all services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load sudo password from env file
if [ -f ~/dev/.env ]; then
    source ~/dev/.env
fi

# Use SUDO_PASS variable
SUDO_PASSWORD="${SUDO_PASS:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Service files
SERVICES=(
    "vietvoice-redis.service"
    "vietvoice-gateway.service"
    "vietvoice-worker-high@.service"
    "vietvoice-worker-fast@.service"
    "vietvoice-frontend.service"
)

# Worker instances to enable
WORKER_INSTANCES=(
    "vietvoice-worker-high@1.service"
    "vietvoice-worker-high@2.service"
)

run_sudo() {
    if [ -n "$SUDO_PASSWORD" ]; then
        echo "$SUDO_PASSWORD" | sudo -S "$@"
    else
        sudo "$@"
    fi
}

install_services() {
    log_info "Installing systemd services..."

    # Copy service files to systemd directory
    for service in "${SERVICES[@]}"; do
        log_info "Installing $service..."
        run_sudo cp "$SCRIPT_DIR/$service" /etc/systemd/system/
    done

    # Reload systemd
    log_info "Reloading systemd daemon..."
    run_sudo systemctl daemon-reload

    # Enable services
    log_info "Enabling services..."
    run_sudo systemctl enable vietvoice-redis.service
    run_sudo systemctl enable vietvoice-gateway.service
    run_sudo systemctl enable vietvoice-frontend.service

    # Enable worker instances
    for worker in "${WORKER_INSTANCES[@]}"; do
        log_info "Enabling $worker..."
        run_sudo systemctl enable "$worker"
    done

    log_info "Services installed and enabled!"
    echo ""
    echo "To start all services: $0 start"
    echo "To check status: $0 status"
}

start_services() {
    log_info "Starting VietVoice TTS services..."

    # Start in order: Redis -> Gateway -> Workers -> Frontend
    log_info "Starting Redis..."
    run_sudo systemctl start vietvoice-redis.service
    sleep 2

    log_info "Starting Gateway..."
    run_sudo systemctl start vietvoice-gateway.service
    sleep 2

    log_info "Starting Workers..."
    for worker in "${WORKER_INSTANCES[@]}"; do
        log_info "Starting $worker..."
        run_sudo systemctl start "$worker"
        sleep 10  # Stagger worker starts for GPU
    done

    log_info "Starting Frontend..."
    run_sudo systemctl start vietvoice-frontend.service

    log_info "All services started!"
    show_status
}

stop_services() {
    log_info "Stopping VietVoice TTS services..."

    # Stop in reverse order
    run_sudo systemctl stop vietvoice-frontend.service 2>/dev/null || true

    for worker in "${WORKER_INSTANCES[@]}"; do
        run_sudo systemctl stop "$worker" 2>/dev/null || true
    done

    run_sudo systemctl stop vietvoice-gateway.service 2>/dev/null || true
    run_sudo systemctl stop vietvoice-redis.service 2>/dev/null || true

    log_info "All services stopped."
}

show_status() {
    echo ""
    echo "=== VietVoice TTS Services Status ==="
    echo ""

    for service in "vietvoice-redis" "vietvoice-gateway" "vietvoice-frontend"; do
        if systemctl is-active --quiet "$service.service" 2>/dev/null; then
            echo -e "$service: ${GREEN}Running${NC}"
        else
            echo -e "$service: ${RED}Stopped${NC}"
        fi
    done

    # Check workers
    for worker in "${WORKER_INSTANCES[@]}"; do
        if systemctl is-active --quiet "$worker" 2>/dev/null; then
            echo -e "$worker: ${GREEN}Running${NC}"
        else
            echo -e "$worker: ${RED}Stopped${NC}"
        fi
    done

    echo ""
    echo "Ports:"
    echo "  Frontend: http://localhost:3341"
    echo "  Backend:  http://localhost:17603"
    echo ""
}

uninstall_services() {
    log_info "Uninstalling VietVoice TTS services..."

    # Stop all services first
    stop_services

    # Disable services
    run_sudo systemctl disable vietvoice-redis.service 2>/dev/null || true
    run_sudo systemctl disable vietvoice-gateway.service 2>/dev/null || true
    run_sudo systemctl disable vietvoice-frontend.service 2>/dev/null || true

    for worker in "${WORKER_INSTANCES[@]}"; do
        run_sudo systemctl disable "$worker" 2>/dev/null || true
    done

    # Remove service files
    for service in "${SERVICES[@]}"; do
        run_sudo rm -f "/etc/systemd/system/$service"
    done

    # Reload systemd
    run_sudo systemctl daemon-reload

    log_info "Services uninstalled."
}

# Main
case "$1" in
    install)
        install_services
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    uninstall)
        uninstall_services
        ;;
    *)
        echo "Usage: $0 {install|start|stop|status|uninstall}"
        echo ""
        echo "Commands:"
        echo "  install   - Install and enable all services (requires sudo)"
        echo "  start     - Start all services"
        echo "  stop      - Stop all services"
        echo "  status    - Show status of all services"
        echo "  uninstall - Remove all services"
        exit 1
        ;;
esac
