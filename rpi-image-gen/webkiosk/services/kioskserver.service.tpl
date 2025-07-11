[Unit]
Description=Flowy Server Session
After=multi-user.target

[Service]
User=<KIOSK_USER>
Restart=always
WorkingDirectory=<SERVER_DIR>
ExecStart=/usr/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8080
StandardError=journal

[Install]
WantedBy=default.target