#!/bin/sh
cd /root/mnt/sata1-5/emby_notifier
export WEB_PORT=8080
python3 main.py > emby.log 2>&1 &
echo "Emby Notifier 已启动，访问 http://192.168.2.2:8080"
