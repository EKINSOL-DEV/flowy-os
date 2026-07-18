#!/bin/bash
# Kiosk update script

set -e

KIOSK_DIR="/opt/kiosk"
LOG_FILE="/var/log/kiosk-update.log"
BACKUP_DIR="/opt/kiosk-backup"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Create backup
create_backup() {
    log "Creating backup..."
    if [ -d "$BACKUP_DIR" ]; then
        rm -rf "$BACKUP_DIR.old"
        mv "$BACKUP_DIR" "$BACKUP_DIR.old"
    fi
    cp -r "$KIOSK_DIR" "$BACKUP_DIR"
    log "Backup created at $BACKUP_DIR"
}

# Restore backup
restore_backup() {
    log "Restoring from backup..."
    if [ -d "$BACKUP_DIR" ]; then
        rm -rf "$KIOSK_DIR"
        cp -r "$BACKUP_DIR" "$KIOSK_DIR"
        log "Backup restored"
    else
        log "ERROR: No backup found!"
        exit 1
    fi
}

# Check for updates
check_updates() {
    cd "$KIOSK_DIR"
    
    # Check if git repo exists
    if [ ! -d ".git" ]; then
        log "Not a git repository, initializing..."
        git init
        git remote add origin https://github.com/your-org/kiosk-config.git
        git fetch origin
        git checkout -b main origin/main
        return 0
    fi
    
    # Fetch latest changes
    git fetch origin
    
    # Check if updates available
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main)
    
    if [ "$LOCAL" = "$REMOTE" ]; then
        log "No updates available"
        return 1
    else
        log "Updates available: $LOCAL -> $REMOTE"
        return 0
    fi
}

# Apply updates
apply_updates() {
    log "Applying updates..."
    
    cd "$KIOSK_DIR"
    
    # Pull latest changes
    git pull origin main
    
    # Install Python dependencies if requirements changed
    if [ -f "requirements.txt" ]; then
        /opt/kiosk/venv/bin/pip install -r requirements.txt
    fi
    
    # Update Docker containers
    if [ -f "docker-compose.yml" ]; then
        docker-compose pull --quiet
        docker-compose up -d
    fi
    
    # Restart services if needed
    systemctl restart kiosk-nfc.service
    systemctl restart kiosk-network.service
    systemctl reload nginx
    
    log "Updates applied successfully"
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Check if services are running
    services=("kiosk-nfc.service" "kiosk-network.service" "nginx.service")
    
    for service in "${services[@]}"; do
        if ! systemctl is-active --quiet "$service"; then
            log "ERROR: Service $service is not running"
            return 1
        fi
    done
    
    # Check if frontend is accessible
    if ! curl -f http://localhost/health > /dev/null 2>&1; then
        log "ERROR: Frontend health check failed"
        return 1
    fi
    
    log "Health check passed"
    return 0
}

# Main update process
main() {
    log "Starting update process..."
    
    # Only proceed if we have internet connectivity
    if ! ping -c 1 8.8.8.8 > /dev/null 2>&1; then
        log "No internet connectivity, skipping update"
        exit 0
    fi
    
    # Check for updates
    if ! check_updates; then
        log "Update process completed (no updates)"
        exit 0
    fi
    
    # Create backup before updating
    create_backup
    
    # Apply updates
    if apply_updates; then
        # Verify everything is working
        sleep 10
        if health_check; then
            log "Update process completed successfully"
            # Clean old backup
            rm -rf "$BACKUP_DIR.old"
        else
            log "Health check failed, restoring backup"
            restore_backup
            systemctl restart kiosk-nfc.service
            systemctl restart kiosk-network.service
            systemctl reload nginx
            exit 1
        fi
    else
        log "Update failed, restoring backup"
        restore_backup
        exit 1
    fi
}

# Handle script arguments
case "${1:-update}" in
    "update")
        main
        ;;
    "check")
        check_updates && echo "Updates available" || echo "No updates available"
        ;;
    "backup")
        create_backup
        ;;
    "restore")
        restore_backup
        ;;
    "health")
        health_check && echo "System healthy" || echo "System unhealthy"
        ;;
    *)
        echo "Usage: $0 {update|check|backup|restore|health}"
        exit 1
        ;;
esac