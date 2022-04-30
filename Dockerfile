FROM python:3.9-buster
COPY . /app
WORKDIR /app

RUN apt update && apt install -y build-essential wget git protobuf-compiler python3-opencv tesseract-ocr

ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

RUN pip install -r requirements.txt
RUN python setup.py install
ENV PYTHONPATH="${PYTHONPATH}:/app"

RUN patch /usr/local/lib/python3.9/site-packages/firefly_iii_client/model/account.py patches/ff_api_none_bug.patch

CMD dockerize -template config.yml.tmpl:config.yml && python firefly_bot/__init__.py