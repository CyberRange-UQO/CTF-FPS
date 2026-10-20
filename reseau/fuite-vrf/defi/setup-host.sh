#!/bin/sh
# Prerequis hote (FRR), a lancer apres `docker compose up -d --build`.
sysctl -w vm.overcommit_memory=1 >/dev/null
sysctl -w net.bridge.bridge-nf-call-iptables=0 >/dev/null
echo "setup hote OK (convergence ~15-20s)"
