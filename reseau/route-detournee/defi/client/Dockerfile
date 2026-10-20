FROM frrouting/frr:latest
RUN apk add --no-cache curl
COPY frr.conf /frr.conf
COPY heartbeat.sh /heartbeat.sh
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh","client"]
