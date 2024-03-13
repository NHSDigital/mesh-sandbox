#!/usr/bin/env bash

SSL="${SSL-no}"
SSL_CRTFILE="${SSL_CRTFILE-/tmp/server-cert.pem}"
SSL_KEYFILE="${SSL_KEYFILE-/tmp/server-cert.key}"
MUTUAL_TLS_CA="${MUTUAL_TLS_CA/tmp/ca.crt}"

if [[ -z "${PORT}" ]]; then
  if [[ "${SSL}" == "yes" ]]; then
    PORT="443"
  else
    PORT="80"
  fi
fi

if [[ "${SSL}" == "yes" ]]; then

  if [ ! -f "${SSL_CRTFILE}" ] && [ ! -f "${SSL_KEYFILE}" ]; then
    openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 -keyout "${SSL_KEYFILE}" -out "${SSL_CRTFILE}"  -subj "/C=GB/O=nhs/OU=local/CN=localhost"
  fi

  if [ -f "${MUTUAL_TLS_CA}" ] && [ -f "${SSL_CRTFILE}" ] && [ -f "${SSL_KEYFILE}" ]; then
    exec uvicorn mesh_sandbox.api:app --host "0.0.0.0" --port "${PORT}" --workers 1 --ssl-certfile "${SSL_CRTFILE}" --ssl-keyfile "${SSL_KEYFILE}" --ssl-ca-certs "${MUTUAL_TLS_CA}" --ssl-cert-reqs 2
  else
    exec uvicorn mesh_sandbox.api:app --host "0.0.0.0" --port "${PORT}" --workers 1 --ssl-certfile "${SSL_CRTFILE}" --ssl-keyfile "${SSL_KEYFILE}"
  fi

else
  exec uvicorn mesh_sandbox.api:app --host "0.0.0.0" --port "${PORT}" --workers 1
fi