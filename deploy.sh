#!/usr/bin/env bash
#
# deploy.sh - Despliega el agente analitico (backend + frontend) en el nodo
# master del cluster EMR y gestiona el servidor Flask de forma remota.
#
# Configuracion: copia deploy.env.example a deploy.env y rellenalo.
#
# Uso:
#   ./deploy.sh up        Sube backend/ y frontend/ al master (rsync incremental)
#   ./deploy.sh install   Crea venv + instala requirements en el master
#   ./deploy.sh run       Arranca el servidor Flask en segundo plano
#   ./deploy.sh stop      Detiene el servidor
#   ./deploy.sh logs      Muestra el log del servidor en vivo (tail -f)
#   ./deploy.sh tunnel    Abre un tunel SSH local -> master para ver la web
#   ./deploy.sh ssh       Abre una sesion SSH al master
#   ./deploy.sh all       up + install + run
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Cargar configuracion ────────────────────────────────────────────────────
if [[ ! -f "$SCRIPT_DIR/deploy.env" ]]; then
  echo "ERROR: no existe deploy.env" >&2
  echo "       Crealo con:  cp deploy.env.example deploy.env  y rellenalo." >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$SCRIPT_DIR/deploy.env"

: "${SSH_KEY:?Falta SSH_KEY en deploy.env}"
: "${MASTER_HOST:?Falta MASTER_HOST en deploy.env}"
REMOTE_USER="${REMOTE_USER:-hadoop}"
REMOTE_DIR="${REMOTE_DIR:-/mnt/agente_retail}"
APP_PORT="${APP_PORT:-5000}"

# Expandir ~ en la ruta de la llave
SSH_KEY="${SSH_KEY/#\~/$HOME}"
eval SSH_KEY="$SSH_KEY"   # expandir $HOME u otras variables del .env

if [[ ! -f "$SSH_KEY" ]]; then
  echo "ERROR: no encuentro la llave SSH: $SSH_KEY" >&2
  exit 1
fi
chmod 600 "$SSH_KEY" 2>/dev/null || true

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)
REMOTE="${REMOTE_USER}@${MASTER_HOST}"

run_ssh() { ssh "${SSH_OPTS[@]}" "$REMOTE" "$@"; }

# ── Subcomandos ─────────────────────────────────────────────────────────────
cmd_up() {
  echo ">> Subiendo backend/ y frontend/ a ${REMOTE}:${REMOTE_DIR}"
  run_ssh "mkdir -p '$REMOTE_DIR'"
  rsync -az --delete \
    -e "ssh ${SSH_OPTS[*]}" \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude 'venv/' \
    --exclude '.env' \
    --exclude '*.log' \
    "$SCRIPT_DIR/backend" "$SCRIPT_DIR/frontend" \
    "${REMOTE}:${REMOTE_DIR}/"
  echo ">> Codigo sincronizado."
}

cmd_install() {
  echo ">> Instalando dependencias en el python del sistema (el que usa spark-submit)"
  run_ssh bash -s <<'REMOTE_SCRIPT'
set -euo pipefail
# Esenciales para el servidor (si fallan, abortamos):
sudo python3 -m pip install --quiet flask flask-cors
# Opcionales: Gemini (skills 1-3) y graficos. Si fallan, el agente funciona igual
# (las skills caen al catalogo local; el server no usa matplotlib).
sudo python3 -m pip install --quiet google-generativeai pandas matplotlib \
  || echo ">> WARN: deps opcionales no instaladas (Gemini/plots); el agente funciona igual."
echo ">> Dependencias listas."
REMOTE_SCRIPT
}

cmd_run() {
  echo ">> Arrancando el agente vía spark-submit (yarn) en 0.0.0.0:${APP_PORT}"
  run_ssh bash -s <<REMOTE_SCRIPT
set -euo pipefail
cd "$REMOTE_DIR/backend"
export APP_HOST=0.0.0.0
export APP_PORT="$APP_PORT"
export MPLBACKEND=Agg
export PYSPARK_PYTHON=python3
# matar instancia previa si existe
if [ -f ../server.pid ] && kill -0 \$(cat ../server.pid) 2>/dev/null; then
  kill \$(cat ../server.pid) 2>/dev/null || true
  sleep 2
fi
pkill -f AgenteAnaliticoRetail 2>/dev/null || true
# Liberar el puerto por si un arranque anterior quedó pegado: el python hijo de
# spark-submit no lleva "AgenteAnaliticoRetail" en su cmdline, asi que pkill no
# lo agarra; lo matamos por puerto. Tambien cubre el cambio de REMOTE_DIR.
if command -v fuser >/dev/null 2>&1; then
  sudo fuser -k "${APP_PORT}/tcp" 2>/dev/null || true
elif command -v lsof >/dev/null 2>&1; then
  PORT_PIDS=\$(sudo lsof -t -i :"${APP_PORT}" 2>/dev/null || true)
  [ -n "\$PORT_PIDS" ] && sudo kill -9 \$PORT_PIDS 2>/dev/null || true
fi
sleep 2
nohup spark-submit --master yarn --deploy-mode client --name AgenteAnaliticoRetail \
  server.py > ../server.log 2>&1 &
echo \$! > ../server.pid
sleep 6
if kill -0 \$(cat ../server.pid) 2>/dev/null; then
  echo ">> Proceso vivo. PID \$(cat ../server.pid)."
  echo "   (Spark tarda ~20-40s en levantar la sesión; la 1a consulta es la lenta)"
else
  echo ">> ERROR: no arrancó. Ultimas lineas del log:" >&2
  tail -n 30 ../server.log >&2
  exit 1
fi
REMOTE_SCRIPT
  echo ">> Log remoto: ${REMOTE_DIR}/server.log   (./deploy.sh logs)"
  echo ">> Para verlo en tu navegador (recomendado):  ./deploy.sh tunnel"
}

cmd_stop() {
  run_ssh bash -s <<REMOTE_SCRIPT
set -euo pipefail
cd "$REMOTE_DIR"
if [ -f server.pid ] && kill -0 \$(cat server.pid) 2>/dev/null; then
  PID=\$(cat server.pid)
  kill "\$PID" && echo ">> Servidor detenido (PID \$PID)"
  rm -f server.pid
else
  echo ">> No hay PID activo."
fi
pkill -f AgenteAnaliticoRetail 2>/dev/null && echo ">> Proceso Spark limpiado." || true
# Asegurar que el puerto queda libre (el python hijo no lo agarra pkill)
if command -v fuser >/dev/null 2>&1; then
  sudo fuser -k "${APP_PORT}/tcp" 2>/dev/null && echo ">> Puerto ${APP_PORT} liberado." || true
elif command -v lsof >/dev/null 2>&1; then
  PORT_PIDS=\$(sudo lsof -t -i :"${APP_PORT}" 2>/dev/null || true)
  [ -n "\$PORT_PIDS" ] && sudo kill -9 \$PORT_PIDS 2>/dev/null && echo ">> Puerto ${APP_PORT} liberado." || true
fi
REMOTE_SCRIPT
}

cmd_logs() {
  echo ">> tail -f ${REMOTE_DIR}/server.log  (Ctrl-C para salir)"
  run_ssh "tail -n 100 -f '$REMOTE_DIR/server.log'"
}

cmd_tunnel() {
  echo ">> Tunel:  http://localhost:${APP_PORT}  ->  master:${APP_PORT}"
  echo "   Deja esta terminal abierta y abre esa URL en tu navegador. Ctrl-C para cerrar."
  ssh "${SSH_OPTS[@]}" -N -L "${APP_PORT}:localhost:${APP_PORT}" "$REMOTE"
}

cmd_ssh() { ssh "${SSH_OPTS[@]}" "$REMOTE"; }

# ── Dispatch ────────────────────────────────────────────────────────────────
case "${1:-}" in
  up)      cmd_up ;;
  install) cmd_install ;;
  run)     cmd_run ;;
  stop)    cmd_stop ;;
  logs)    cmd_logs ;;
  tunnel)  cmd_tunnel ;;
  ssh)     cmd_ssh ;;
  all)     cmd_up; cmd_install; cmd_run ;;
  *)
    echo "Uso: $0 {up|install|run|stop|logs|tunnel|ssh|all}" >&2
    exit 1
    ;;
esac
