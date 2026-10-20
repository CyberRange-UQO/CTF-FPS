FROM frrouting/frr:latest
RUN apk add --no-cache iproute2
COPY router-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
