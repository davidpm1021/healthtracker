#!/bin/bash
# HealthTracker System Health Monitor
# Runs periodically to check system health and trigger recovery if needed

LOG_DIR="/var/log/healthtracker"
RECOVERY_MARKER="$LOG_DIR/needs_recovery"
HEALTH_LOG="$LOG_DIR/health-check.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_health() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$HEALTH_LOG"
}

check_service() {
    service_name=$1
    if systemctl is-active --quiet "$service_name"; then
        echo -e "${GREEN}✓${NC} $service_name is running"
        return 0
    else
        echo -e "${RED}✗${NC} $service_name is not running"
        log_health "ERROR: $service_name is not running"
        return 1
    fi
}

check_api_health() {
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} API is responding"
        
        # Check database connectivity
        if curl -s http://localhost:8000/api/health/db | grep -q "healthy"; then
            echo -e "${GREEN}✓${NC} Database is healthy"
            return 0
        else
            echo -e "${YELLOW}⚠${NC} Database issues detected"
            log_health "WARNING: Database connectivity issues"
            return 1
        fi
    else
        echo -e "${RED}✗${NC} API is not responding"
        log_health "ERROR: API not responding"
        return 1
    fi
}

check_disk_space() {
    threshold=90  # Alert if disk usage > 90%
    usage=$(df /home | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$usage" -lt "$threshold" ]; then
        echo -e "${GREEN}✓${NC} Disk usage: ${usage}%"
        return 0
    else
        echo -e "${RED}✗${NC} Disk usage critical: ${usage}%"
        log_health "ERROR: Disk usage at ${usage}%"
        
        # Try to free space
        echo "Cleaning old logs..."
        find "$LOG_DIR" -name "*.log.*" -mtime +7 -delete
        
        return 1
    fi
}

check_memory() {
    # Get memory usage percentage
    mem_total=$(free | grep Mem | awk '{print $2}')
    mem_used=$(free | grep Mem | awk '{print $3}')
    mem_percent=$((mem_used * 100 / mem_total))
    
    if [ "$mem_percent" -lt 85 ]; then
        echo -e "${GREEN}✓${NC} Memory usage: ${mem_percent}%"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} High memory usage: ${mem_percent}%"
        log_health "WARNING: Memory usage at ${mem_percent}%"
        
        # Clear caches if memory is critical
        if [ "$mem_percent" -gt 95 ]; then
            echo "Clearing system caches..."
            sync && echo 3 > /proc/sys/vm/drop_caches
        fi
        
        return 1
    fi
}

check_database_integrity() {
    db_path="/home/pi/healthtracker/healthtracker.db"
    
    if [ -f "$db_path" ]; then
        result=$(sqlite3 "$db_path" "PRAGMA integrity_check;" 2>&1)
        if [ "$result" = "ok" ]; then
            echo -e "${GREEN}✓${NC} Database integrity check passed"
            return 0
        else
            echo -e "${RED}✗${NC} Database integrity issues found"
            log_health "ERROR: Database integrity check failed: $result"
            
            # Attempt repair
            echo "Attempting database repair..."
            cp "$db_path" "${db_path}.backup.$(date +%Y%m%d_%H%M%S)"
            sqlite3 "$db_path" "VACUUM;"
            sqlite3 "$db_path" "REINDEX;"
            
            return 1
        fi
    else
        echo -e "${RED}✗${NC} Database file not found"
        log_health "ERROR: Database file not found at $db_path"
        return 1
    fi
}

check_network() {
    # Check if we can reach the local network
    if ping -c 1 -W 2 192.168.1.1 > /dev/null 2>&1 || \
       ping -c 1 -W 2 192.168.0.1 > /dev/null 2>&1 || \
       ping -c 1 -W 2 10.0.0.1 > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Network connectivity OK"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} Network connectivity issues"
        log_health "WARNING: Cannot reach local network"
        return 1
    fi
}

perform_recovery() {
    echo -e "${YELLOW}Performing system recovery...${NC}"
    log_health "Starting recovery procedure"
    
    # Stop services
    systemctl stop healthtracker-kiosk
    systemctl stop healthtracker-server
    
    # Clear caches
    rm -rf /home/pi/.cache/healthtracker/*
    rm -rf /home/pi/.config/chromium-kiosk/Default/Cache/*
    
    # Database maintenance
    db_path="/home/pi/healthtracker/healthtracker.db"
    if [ -f "$db_path" ]; then
        sqlite3 "$db_path" "VACUUM;"
        sqlite3 "$db_path" "ANALYZE;"
    fi
    
    # Restart services
    systemctl start healthtracker-server
    sleep 5
    systemctl start healthtracker-kiosk
    
    # Remove recovery marker
    rm -f "$RECOVERY_MARKER"
    
    echo -e "${GREEN}Recovery complete${NC}"
    log_health "Recovery procedure completed"
}

# Main health check
echo "======================================"
echo "HealthTracker System Health Check"
echo "$(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================"

errors=0

# Run all checks
check_service "healthtracker-server" || ((errors++))
check_service "healthtracker-kiosk" || ((errors++))
check_api_health || ((errors++))
check_disk_space || ((errors++))
check_memory || ((errors++))
check_database_integrity || ((errors++))
check_network || ((errors++))

echo "======================================"

# Check if recovery is needed
if [ -f "$RECOVERY_MARKER" ]; then
    echo -e "${YELLOW}Recovery marker found${NC}"
    perform_recovery
elif [ "$errors" -gt 3 ]; then
    echo -e "${RED}Multiple issues detected ($errors errors)${NC}"
    echo "Creating recovery marker..."
    touch "$RECOVERY_MARKER"
    log_health "Multiple errors detected, recovery scheduled"
elif [ "$errors" -gt 0 ]; then
    echo -e "${YELLOW}$errors issue(s) detected${NC}"
    log_health "Health check completed with $errors issues"
else
    echo -e "${GREEN}All systems healthy${NC}"
    log_health "Health check passed - all systems healthy"
fi

# Cleanup old health logs (keep last 30 days)
find "$LOG_DIR" -name "health-check.log.*" -mtime +30 -delete

exit $errors