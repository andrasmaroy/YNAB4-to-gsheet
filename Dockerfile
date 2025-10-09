FROM python:3.12-alpine

COPY requirements.txt /
RUN pip install -r requirements.txt

WORKDIR /app
COPY \
    config.py \
    dbx.py \
    gsheet.py \
    ksh.py \
    main.py \
    mnb.py \
    portfolio.py \
    stocks.py \
    .

CMD python main.py
