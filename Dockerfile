# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

ENV USE_TEST_INSTANCE='False'

WORKDIR /neotab

# install poppler
RUN apt-get update
RUN apt-get install poppler-utils -y

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]