#!/bin/sh
ip route replace default via 192.168.2.1 2>/dev/null
exec busybox-extras httpd -f -p 80 -h /www
