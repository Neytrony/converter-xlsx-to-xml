# pull official base image
#FROM python:3.9.6-alpine
FROM python:3.9-buster

# set work directory
RUN mkdir -p /usr/src/app && mkdir -p /usr/src/app/mediafiles && mkdir -p /usr/src/app/mediafiles/logs

WORKDIR /usr/src/app

# install dependencies
RUN apt-get update && apt-get install -y nano iputils-ping

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install psycopg2 dependencies
RUN apt-get update \
    && apt-get install -y \
    gcc

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# copy entrypoint.sh
COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g' /usr/src/app/entrypoint.sh
RUN chmod +x /usr/src/app/entrypoint.sh

# copy project
COPY . /usr/src/app

#ENTRYPOINT ["/usr/src/app/entrypoint.sh"]