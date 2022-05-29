# syntax=docker/dockerfile:1

FROM python:3.10-buster

WORKDIR /optiplex

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY ./optiplex /optiplex

# create database
RUN python3 -m flask init-db

CMD ["uwsgi", "optiplex.ini"]
# CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
