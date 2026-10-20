FROM python:3.12-alpine
RUN apk add --no-cache tcpdump openssh iproute2 libpcap \
 && pip install --no-cache-dir scapy \
 && ssh-keygen -A \
 && echo 'root:MplsSpoof2026' | chpasswd \
 && sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
COPY inject.py /root/inject.py
COPY LISEZMOI.txt /root/LISEZMOI.txt
COPY atk-entrypoint.sh /atk-entrypoint.sh
RUN chmod +x /atk-entrypoint.sh
ENTRYPOINT ["/atk-entrypoint.sh"]
