FROM python:3.12-alpine
RUN apk add --no-cache iproute2
COPY run.sh /run.sh
RUN chmod +x /run.sh
CMD ["/run.sh"]
