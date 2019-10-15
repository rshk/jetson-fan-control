# NVIDIA Jetson fan control

![](/.screenshot.png)

Automatically control the fan speed on a Jetson board.

Tested on a Jetson Nano, but should work on other boards as well.


## Installation

Requires Python 3. Simply run the ``install.sh`` script to install the
Python script and systemd units in your system.


## Inspect the logs

To check the logs:

```
journalctl -f -u fan-control.service
```


## Configure

Edit the ``Environment`` setting in ``/lib/systemd/system/fan-control.service``:

```
Environment=FAN_CONTROL_MIN_TEMP=10 FAN_CONTROL_MAX_TEMP=50 FAN_CONTROL_EXCLUDE_ZONES=thermal_zone4
```

Reload & restart the service:

```
sudo systemctl daemon-reload
sudo systemctl restart fan-control.service
```
