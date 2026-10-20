FROM alpine:3.20
RUN apk add --no-cache busybox-extras
COPY www /www
CMD ["busybox-extras", "httpd", "-f", "-p", "80", "-h", "/www"]
