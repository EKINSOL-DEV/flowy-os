[Unit]
Description=Flowy Unified API Server
Documentation=https://github.com/your-repo/flowy-os
After=network.target
Wants=network-online.target
After=network-online.target

[Service]
Type=exec
User=<KIOSK_USER>
Group=<KIOSK_USER>
WorkingDirectory=<SERVER_DIR>
Environment=PYTHONPATH=<SERVER_DIR>
Environment=FLOWY_LOG_DIR=/flowy/logs
Environment=PATH=<PYTHON_DIR>:/usr/local/bin:/usr/bin:/bin
ExecStart=<PYTHON_EXEC> flowy_unified_api.py --host 0.0.0.0 --port 8000
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StartLimitInterval=0
TimeoutStartSec=300
TimeoutStopSec=30

# Resource limits
LimitNOFILE=65536
MemoryMax=512M
CPUQuota=50%

# Security settings - relaxed for GPIO/hardware access
NoNewPrivileges=yes
ProtectHome=yes
PrivateTmp=yes
RestrictRealtime=yes
LockPersonality=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX

# Allow access to logs and thermal monitoring
ReadWritePaths=/flowy/logs
ReadOnlyPaths=/sys/class/thermal

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=flowy-unified-api

# Watchdog settings disabled - FastAPI doesn't send notifications
# WatchdogSec=60
# NotifyAccess=main

[Install]
WantedBy=multi-user.target