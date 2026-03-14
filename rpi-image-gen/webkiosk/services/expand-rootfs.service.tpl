[Unit]
Description=Expand root filesystem to fill disk
After=local-fs.target
ConditionPathExists=/var/lib/flowy/.expand-rootfs

[Service]
Type=oneshot
ExecStart=/usr/local/bin/expand-rootfs.sh
RemainAfterExit=true

[Install]
WantedBy=multi-user.target
