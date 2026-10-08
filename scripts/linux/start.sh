#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Uso: bash scripts/linux/start.sh [--build] [--logs]"
}
build=0
logs=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --build) build=1 ;;
        --logs) logs=1 ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
    shift
done
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd -- "$repo_root"
env_file="$repo_root/conn/.env"
[[ -f "$env_file" ]] || { echo "Falta conn/.env." >&2; exit 1; }
command -v docker >/dev/null || { echo "Instale Docker y el plugin Compose." >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker no esta activo o este usuario no tiene acceso al daemon." >&2; exit 1; }
docker compose version >/dev/null || { echo "Falta el plugin Docker Compose." >&2; exit 1; }
arguments=(compose --env-file "$env_file" up -d)
if [[ "$build" == 1 ]]; then arguments+=(--build); fi
docker "${arguments[@]}"
docker compose --env-file "$env_file" ps
printf '%s\n' 'Frontend: http://localhost:8083' 'Backend: http://localhost:8080/api' \
    'La impresion requiere el agente en el equipo Windows conectado a la Zebra.'
if [[ "$logs" == 1 ]]; then docker compose --env-file "$env_file" logs -f; fi
