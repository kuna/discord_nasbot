#!/bin/sh
# Starts the bundled SpoofDPI proxy (unless disabled), then runs the bot.
set -eu

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') INFO     entrypoint $*"
}

if [ "${SPOOFDPI_ENABLED:-1}" = "1" ]; then
    listen_addr="${SPOOFDPI_LISTEN_ADDR:-127.0.0.1:8080}"
    log "starting spoofdpi on ${listen_addr}"
    # --no-tui: spoofdpi defaults to an interactive TUI, which needs a TTY
    spoofdpi \
        --no-tui \
        --listen-addr "${listen_addr}" \
        --log-level "${SPOOFDPI_LOG_LEVEL:-info}" &
    spoofdpi_pid=$!

    # fail fast instead of letting the bot run with a dead proxy
    sleep 1
    if ! kill -0 "${spoofdpi_pid}" 2>/dev/null; then
        log "spoofdpi exited immediately, aborting"
        exit 1
    fi
    log "spoofdpi running (pid ${spoofdpi_pid})"

    # point the bot at the bundled proxy, unless it was told to use another one
    PROXY_HOST="${PROXY_HOST:-${listen_addr%:*}}"
    PROXY_PORT="${PROXY_PORT:-${listen_addr##*:}}"
    export PROXY_HOST PROXY_PORT
else
    # PROXY_HOST stays unset unless the user supplied an external proxy, so the
    # bot reports a clear error instead of dialing a dead port
    log "spoofdpi disabled, proxy is ${PROXY_HOST:-not configured}"
fi

# tini -g forwards signals to the process group, so spoofdpi stops with the bot
exec "$@"
