#!/bin/bash

install -m 755 -o root -g root jetson_fan_control.py /usr/local/bin
install -m 644 -o root -g root fan-control.service /lib/systemd/system/
systemctl daemon-reload
systemctl start fan-control.service
systemctl enable fan-control.service
echo "Installation complete."
