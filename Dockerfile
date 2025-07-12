FROM python:3.13-alpine3.22 AS builder
RUN apk update
RUN pip install poetry
COPY . /app
WORKDIR /app
RUN poetry build --format=wheel


FROM python:3.13-alpine3.22
LABEL org.opencontainers.image.source=https://github.com/kmille/zammad-pgp-auto-import
LABEL org.opencontainers.image.description="Zammad webhook that automatically imports PGP keys using Zammad's API"
LABEL org.opencontainers.image.licenses=MIT

COPY --from=builder /app/dist/*.whl .
RUN apk add gpg
RUN adduser -D webhook && \
    pip install *.whl && \
    rm *.whl

ENV PYTHONUNBUFFERED=TRUE
ENV LISTEN_HOST=0.0.0.0
ENV LISTEN_PORT=22000
ENV DEBUG=0

USER webhook
EXPOSE 22000

ENTRYPOINT ["/usr/local/bin/zammad-pgp-autoimport-webhook"]
