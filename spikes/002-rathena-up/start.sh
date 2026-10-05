#!/usr/bin/env bash
# Spike 002: boot mysqld (local datadir) + rAthena login/char/map servers, all localhost.
# Usage: ./start.sh          (idempotent: skips what's already running)
#        ./start.sh stop     (stops everything)
# Run inside the flake devShell:  nix develop ../spikes/002-rathena-up  (then ./start.sh)
# or:    nix develop ../spikes/002-rathena-up -c ../start.sh   (from rathena/ dir parent)
set -u

PROJ="$HOME/dev/ro-bots"
RA="$PROJ/rathena"
RUN="$PROJ/run"
DATADIR="$PROJ/mysql-data"
LOG="$RUN"

mkdir -p "$RUN" "$LOG"

srv_running() { # pidfile, name
  [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null
}

start_mysql() {
  if srv_running "$RUN/mysql.pid" mysqld; then
    echo "[start.sh] mysqld already running (pid $(cat "$RUN/mysql.pid"))"
    return 0
  fi
  if [ ! -d "$DATADIR/mysql" ]; then
    echo "[start.sh] initializing MariaDB datadir at $DATADIR ..."
    mysql_install_db --no-defaults --basedir="$MYSQL_BASEDIR" --datadir="$DATADIR" \
      --auth-root-authentication-method=normal --skip-test-db >/dev/null
    # fresh datadir: recreate DBs and import schemas
    local FRESH=1
  else
    local FRESH=0
  fi
  echo "[start.sh] starting mysqld (localhost:3306, socket $RUN/mysql.sock) ..."
  mysqld --no-defaults \
    --basedir="$MYSQL_BASEDIR" \
    --datadir="$DATADIR" \
    --socket="$RUN/mysql.sock" \
    --pid-file="$RUN/mysql.pid" \
    --bind-address=127.0.0.1 \
    --port=3306 \
    --console >>"$LOG/mysqld.log" 2>&1 &
  echo $! > "$RUN/mysql.pid"
  # wait for socket
  for i in $(seq 1 30); do
    [ -S "$RUN/mysql.sock" ] && break
    sleep 1
  done
  if [ ! -S "$RUN/mysql.sock" ]; then echo "[start.sh] ERROR: mysqld did not come up; see $LOG/mysqld.log"; return 1; fi
  if [ "$FRESH" = 1 ]; then
    echo "[start.sh] creating ragnarok DBs + user, importing main.sql/logs.sql ..."
    mysql --no-defaults -h 127.0.0.1 -u root -e "CREATE DATABASE ragnarok; CREATE DATABASE ragnarok_logs; CREATE USER 'ragnarok'@'localhost' IDENTIFIED BY 'ragnarok'; CREATE USER 'ragnarok'@'127.0.0.1' IDENTIFIED BY 'ragnarok'; GRANT ALL ON ragnarok.* TO 'ragnarok'@'localhost'; GRANT ALL ON ragnarok.* TO 'ragnarok'@'127.0.0.1'; GRANT ALL ON ragnarok_logs.* TO 'ragnarok'@'localhost'; GRANT ALL ON ragnarok_logs.* TO 'ragnarok'@'127.0.0.1'; FLUSH PRIVILEGES;"
    mysql --no-defaults -h 127.0.0.1 -u root ragnarok < "$RA/sql-files/main.sql"
    mysql --no-defaults -h 127.0.0.1 -u root ragnarok_logs < "$RA/sql-files/logs.sql"
  fi
}

start_ra() { # binary
  local bin="$1"
  if srv_running "$RA/.$bin.pid" "$bin"; then
    echo "[start.sh] $bin already running"
    return 0
  fi
  cd "$RA"
  "./$bin" >>"$LOG/$bin.log" 2>&1 &
  echo $! > "$RA/.$bin.pid"
  echo "[start.sh] started $bin (pid $(cat "$RA/.$bin.pid"))"
}

stop_ra() { # binary
  local bin="$1"
  if srv_running "$RA/.$bin.pid" "$bin"; then
    kill "$(cat "$RA/.$bin.pid")"
    echo "[start.sh] stopped $bin"
  fi
  rm -f "$RA/.$bin.pid"
}

case "${1:-start}" in
  start)
    start_mysql || exit 1
    start_ra login-server
    start_ra char-server
    start_ra map-server
    echo "[start.sh] all started; logs in $LOG/, ports 6900/6121/5121"
    ;;
  stop)
    stop_ra map-server
    stop_ra char-server
    stop_ra login-server
    if srv_running "$RUN/mysql.pid" mysqld; then
      mysqladmin --no-defaults -h 127.0.0.1 -u root shutdown 2>/dev/null || kill "$(cat "$RUN/mysql.pid")"
      echo "[start.sh] stopped mysqld"
    fi
    rm -f "$RUN/mysql.pid"
    ;;
  status)
    for s in mysqld login-server char-server map-server; do
      if [ "$s" = mysqld ]; then f="$RUN/mysql.pid"; else f="$RA/.$s.pid"; fi
      srv_running "$f" "$s" && echo "$s: RUNNING ($(cat "$f"))" || echo "$s: DOWN"
    done
    ;;
  *) echo "usage: $0 {start|stop|status}"; exit 1 ;;
esac
