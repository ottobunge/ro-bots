#!/usr/bin/env bash
# ADR-010: rAthena container entry point (login|char|map).
# Containerized rAthena is a documented follow-up: this script exists, but
# the SQL host/creds rewrite needs a live validation pass against a booted
# mariadb service before the image can be trusted (see docker/README.md).
set -eu
BIN="${1:?usage: rathena-entry.sh login-server|char-server|map-server}"
cd /rathena

# point the inter-server conf at the compose mariadb service
if grep -q '^login_server_ip:' conf/inter_athena.conf; then
  sed -i "s/^login_server_ip:.*/login_server_ip: ${MARIA_ADDR}/" conf/inter_athena.conf
  sed -i "s/^char_server_ip:.*/char_server_ip: ${MARIA_ADDR}/"   conf/inter_athena.conf
  sed -i "s/^map_server_ip:.*/map_server_ip: ${MARIA_ADDR}/"     conf/inter_athena.conf
  sed -i "s/^web_server_ip:.*/web_server_ip: ${MARIA_ADDR}/"     conf/inter_athena.conf
  sed -i "s/^login_server_id:.*/login_server_id: ${SQL_USER:-ragnarok}/" conf/inter_athena.conf
  sed -i "s/^login_server_pw:.*/login_server_pw: ${SQL_PASS:-ragnarok}/" conf/inter_athena.conf
  sed -i "s/^char_server_id:.*/char_server_id: ${SQL_USER:-ragnarok}/" conf/inter_athena.conf
  sed -i "s/^char_server_pw:.*/char_server_pw: ${SQL_PASS:-ragnarok}/" conf/inter_athena.conf
  sed -i "s/^map_server_id:.*/map_server_id: ${SQL_USER:-ragnarok}/" conf/inter_athena.conf
  sed -i "s/^map_server_pw:.*/map_server_pw: ${SQL_PASS:-ragnarok}/" conf/inter_athena.conf
  sed -i "s/^log_db_id:.*/log_db_id: ${SQL_USER:-ragnarok}/" conf/inter_athena.conf
  sed -i "s/^log_db_pw:.*/log_db_pw: ${SQL_PASS:-ragnarok}/" conf/inter_athena.conf
fi

echo "[rathena-entry] starting $BIN (SQL host ${MARIA_ADDR:-unset})"
exec "./$BIN"
