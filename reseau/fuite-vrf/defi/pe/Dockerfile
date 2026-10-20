FROM frrouting/frr:latest
RUN apk add --no-cache iproute2
COPY frr.conf /frr.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
