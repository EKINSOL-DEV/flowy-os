[Unit]
Description=Flowy Unified API Server
After=multi-user.target

[Service]
User=root
Restart=always
WorkingDirectory=<SERVER_DIR>
ExecStart=<PYTHON_EXEC> main_api.py
StandardError=journal

[Install]
WantedBy=default.target