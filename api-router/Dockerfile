FROM nginx:1.27-alpine

COPY default.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 8080

CMD ["/bin/sh", "-c", "envsubst '$AUTH_SERVICE_URL $UPLOAD_SERVICE_URL $INGESTION_SERVICE_URL $RAG_SERVICE_URL' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'"]
