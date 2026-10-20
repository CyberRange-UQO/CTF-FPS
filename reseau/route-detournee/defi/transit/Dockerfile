FROM frrouting/frr:latest
COPY frr.conf /frr.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh","transit"]
