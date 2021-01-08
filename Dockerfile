FROM tiangolo/uwsgi-nginx-flask:python3.6-alpine3.7
RUN apk --update add bash nano
ENV STATIC_URL /static
ENV STATIC_PATH /app/plex-upload/static
RUN echo "client_body_buffer_size 2M;" > /etc/nginx/conf.d/buffer.conf
COPY . /app
RUN pip install -r /app/requirements.txt