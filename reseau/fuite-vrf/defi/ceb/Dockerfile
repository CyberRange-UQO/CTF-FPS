FROM alpine:3.20
RUN apk add --no-cache busybox-extras iproute2
COPY www /www
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
