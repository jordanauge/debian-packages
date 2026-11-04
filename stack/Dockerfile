FROM debian:forky-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    reprepro gnupg python3 ca-certificates apache2-utils \
    && rm -r /var/lib/apt/lists
COPY manage.sh catalogue.py credentials.py /usr/local/bin/
COPY synaxe_repository_ui /usr/local/bin/synaxe_repository_ui
RUN chmod 755 /usr/local/bin/manage.sh
ENV GNUPGHOME=/repository/gnupg
ENTRYPOINT ["/usr/local/bin/manage.sh"]
