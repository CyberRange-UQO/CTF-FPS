FROM frrouting/frr:latest
RUN apk add --no-cache python3
COPY frr.conf /frr.conf
COPY service.py /service.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh","victime"]
