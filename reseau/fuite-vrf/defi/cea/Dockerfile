FROM alpine:3.20
RUN apk add --no-cache openssh iproute2 curl \
 && ssh-keygen -A \
 && echo 'root:ClientA2026' | chpasswd \
 && sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
