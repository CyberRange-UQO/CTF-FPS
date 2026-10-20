FROM frrouting/frr:latest
RUN apk add --no-cache openssh curl tcpdump python3 \
 && ssh-keygen -A \
 && echo 'root:Hijack2026' | chpasswd \
 && sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
COPY frr.conf /frr.conf
COPY mitm.py /root/mitm.py
COPY home/LISEZMOI.txt /root/LISEZMOI.txt
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh","attaquant"]
