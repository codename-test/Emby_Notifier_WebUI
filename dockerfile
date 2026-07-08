FROM python:3.11-alpine3.18

LABEL maintainer="Emby Notifier"

ENV TZ=Asia/Shanghai LANG=zh_CN.UTF-8 PYTHONUNBUFFERED=1

EXPOSE 5000

RUN set -eux && \
    apk --no-cache update && \
    apk -U --no-cache add git tzdata && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    mkdir -p /usr/src/myapp/ /data

WORKDIR /usr/src/myapp/

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt -q

COPY . .

VOLUME ["/data"]

ENV DB_PATH=/data/emby_notifier.db

ENTRYPOINT ["python3"]
CMD ["main.py"]
