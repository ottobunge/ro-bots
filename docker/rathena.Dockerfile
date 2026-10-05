# ADR-010: rAthena server image (login + char + map, one build).
#
# Compiles rAthena from the repo checkout with the SAME flags the native
# spike uses (spikes/002-rathena-up): PACKETVER 20180704, pre-renewal,
# packet obfuscation off, PIN off — so the clientless BotClient (spike 003)
# speaks the same protocol against the containerized stack.
#
# STATUS: documented follow-up (ADR-010). The e2e runs rAthena NATIVELY via
# spikes/002-rathena-up/start.sh today; this Dockerfile exists so the
# container path can be finished without redesign:
#   docker compose -f docker-compose.worlds.yml --profile rathena up -d
#
# The build applies the same conf tweaks as the spike by patching at build
# time (no committed config fork): packet version / renewal / obfuscation /
# pincode / SQL host, via sed on rAthena's conf + src defaults.
FROM gcc:13-bookworm AS builder

ARG PACKETVER=20180704
ARG PRERE=yes

WORKDIR /rathena
COPY rathena/ /rathena/

# Build-time configuration == spike configuration.
RUN set -eux; \
    sed -i "s/^#define PACKETVER .*/#define PACKETVER ${PACKETVER}/" \
      src/common/mmo.hpp; \
    if [ "$PRERE" = "yes" ]; then \
      sed -i "s|^//#define PRERE|#define PRERE|" src/common/mmo.hpp; \
    fi; \
    sed -i "s/^//#define PACKET_OBFUSCATION /#define PACKET_OBFUSCATION /" \
      src/common/mmo.hpp 2>/dev/null || true; \
    sed -i "s/^pincode_enabled: .*/pincode_enabled: no/" conf/char_athena.conf; \
    sed -i "s/^userid: .*/userid: ragnarok/;s/^passwd: .*/passwd: ragnarok/" \
      conf/inter_athena.conf || true; \
    ./configure --enable-prere=$PRERE --disable-manager --disable-db-debug \
      2>&1 | tail -5; \
    make -j"$(nproc)" server 2>&1 | tail -5

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      mariadb-client libmariadb3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /rathena
COPY --from=builder /rathena/ /rathena/
# MARIA_ADDR (service name of the compose mariadb) overrides the SQL host.
ENV MARIA_ADDR=mariadb \
    SQL_USER=ragnarok SQL_PASS=ragnarok
COPY docker/rathena-entry.sh /rathena-entry.sh
RUN chmod +x /rathena-entry.sh
ENTRYPOINT ["/rathena-entry.sh"]
CMD ["login-server"]
