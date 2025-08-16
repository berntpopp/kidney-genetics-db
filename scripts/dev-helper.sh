#!/bin/bash
# Development Helper Script for Kidney Genetics Database

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if services are running
check_services() {
    echo "Checking services..."
    
    # Check backend
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        print_status "Backend is running on port 8000"
    else
        print_error "Backend is not running"
    fi
    
    # Check frontend
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        print_status "Frontend is running on port 5173"
    else
        print_error "Frontend is not running"
    fi
    
    # Check database
    cd backend && uv run python -c "
from app.core.database import get_db
from sqlalchemy import text
try:
    db = next(get_db())
    db.execute(text('SELECT 1'))
    print('Database connection OK')
except Exception as e:
    print(f'Database error: {e}')
    exit(1)
" && print_status "Database is accessible" || print_error "Database connection failed"
}

# Clean and restart for testing
clean_restart() {
    print_warning "This will delete all data and restart services"
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        make fresh-start
    fi
}

# Run specific data source
run_source() {
    source=$1
    if [ -z "$source" ]; then
        echo "Usage: $0 run-source [PubTator|PanelApp|HPO|ClinGen|GenCC]"
        exit 1
    fi
    
    print_status "Triggering $source..."
    curl -X POST "http://localhost:8000/api/progress/trigger/$source" \
        -H "Content-Type: application/json" \
        -s | python3 -m json.tool
}

# Monitor progress in real-time
monitor_progress() {
    echo "Monitoring data source progress (Ctrl+C to stop)..."
    while true; do
        clear
        date
        echo "================================"
        make status
        sleep 2
    done
}

# Quick test run with minimal data
quick_test() {
    print_status "Setting up quick test environment..."
    
    # Update config for minimal testing
    cd backend
    python3 -c "
import fileinput
import sys

# Temporarily set minimal config values
replacements = {
    'PUBTATOR_MAX_PAGES: int = 200': 'PUBTATOR_MAX_PAGES: int = 5',
    'PUBTATOR_MIN_PUBLICATIONS: int = 3': 'PUBTATOR_MIN_PUBLICATIONS: int = 2',
}

with open('app/core/config.py', 'r') as f:
    content = f.read()

for old, new in replacements.items():
    content = content.replace(old, new)

with open('app/core/config.py', 'w') as f:
    f.write(content)

print('Config updated for quick testing')
"
    
    cd ..
    make fresh-start
    
    print_status "Quick test environment ready!"
    print_warning "Config set to minimal values for testing"
}

# Main menu
case "$1" in
    check)
        check_services
        ;;
    clean-restart)
        clean_restart
        ;;
    run-source)
        run_source "$2"
        ;;
    monitor)
        monitor_progress
        ;;
    quick-test)
        quick_test
        ;;
    *)
        echo "Kidney Genetics Database - Development Helper"
        echo "============================================="
        echo "Usage: $0 {check|clean-restart|run-source|monitor|quick-test}"
        echo ""
        echo "Commands:"
        echo "  check         - Check status of all services"
        echo "  clean-restart - Clean database and restart all services"
        echo "  run-source    - Trigger a specific data source"
        echo "  monitor       - Monitor progress in real-time"
        echo "  quick-test    - Set up minimal test environment"
        echo ""
        echo "Or use Make commands directly:"
        echo "  make help     - Show all available make commands"
        ;;
esac