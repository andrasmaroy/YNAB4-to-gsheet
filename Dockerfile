FROM python:3.12-alpine

COPY requirements.txt /
RUN pip install -r requirements.txt

WORKDIR /app
COPY \
    main.py \
    config.py \
    .

CMD python main.py
