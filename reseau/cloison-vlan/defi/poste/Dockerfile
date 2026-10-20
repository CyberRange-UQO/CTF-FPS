FROM alpine:3.20
RUN apk add --no-cache openssh iproute2 curl tcpdump \
 && ssh-keygen -A \
 && echo 'root:Depannage2026' | chpasswd \
 && sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
COPY notes /root/notes
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
