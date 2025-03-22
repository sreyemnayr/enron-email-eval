FROM alpine:latest

WORKDIR /data
VOLUME /data

RUN apk add --no-cache wget

RUN wget https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz

RUN tar -xzf enron_mail_20150507.tar.gz

RUN rm enron_mail_20150507.tar.gz