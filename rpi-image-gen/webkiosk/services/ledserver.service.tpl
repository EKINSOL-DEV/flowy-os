[Unit]
Description=Flowy LED Server Session
After=sysinit.target
Wants=sysinit.target

[Service]
User=root
Restart=always
WorkingDirectory=<SERVER_DIR>
ExecStart=<PYTHON_EXEC> led_api.py
StandardError=journal

[Install]
WantedBy=basic.target