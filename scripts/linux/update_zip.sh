#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo 'Uso: bash scripts/linux/update_zip.sh [--no-upload] [--bucket gs://label-print-cv/deploy.zip]'
    echo 'Genera artifacts/deploy/deploy.zip (incluye conn/ y logos) y opcionalmente lo sube a GCS.'
}
upload=1
bucket='gs://label-print-cv/deploy.zip'
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-upload) upload=0; shift ;;
        --bucket) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; bucket="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done
[[ "$bucket" == gs://* ]] || { echo 'El destino debe comenzar por gs://.' >&2; exit 2; }
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd -- "$repo_root"
command -v zip >/dev/null || { echo 'Falta zip. Use startup.sh -t zip.' >&2; exit 1; }
if [[ "$upload" == 1 ]]; then command -v gsutil >/dev/null || { echo 'Falta gsutil. Instale Google Cloud CLI y autentiquese.' >&2; exit 1; }; fi
paths=()
while IFS= read -r entry || [[ -n "$entry" ]]; do
    entry="${entry%$'\r'}"
    [[ -n "$entry" ]] || continue
    [[ -e "$entry" ]] || { echo "Falta un archivo/directorio requerido: $entry" >&2; exit 1; }
    paths+=("$entry")
done < scripts/deploy-files.txt
linked_path="$(find "${paths[@]}" \
    \( -type d \( -name node_modules -o -name __pycache__ -o -name .venv -o -name venv \
        -o -name build -o -name dist -o -name .vite -o -name .nitro -o -name .output \
        -o -name .git -o -name .build -o -name artifacts -o -name logs -o -name '*.egg-info' \) -prune \) \
    -o -type l -print -quit)"
[[ -z "$linked_path" ]] || { echo "No se empaquetan enlaces simbolicos: $linked_path" >&2; exit 1; }
mkdir -p artifacts/deploy
# zip -r otherwise retains deleted entries from a previous archive.
archive="$repo_root/artifacts/deploy/deploy.zip"
if [[ -e "$archive" ]]; then rm -- "$archive"; fi
zip -q -r "$archive" "${paths[@]}" -x \
    '*/node_modules/*' '*/__pycache__/*' '*/.venv/*' '*/venv/*' '*/build/*' \
    '*/dist/*' '*/.vite/*' '*/.nitro/*' '*/.output/*' '*/.git/*' '*/.build/*' \
    '*/artifacts/*' '*/logs/*' '*.egg-info/*' '*.pyc' '*.pyo' '*.log'
echo "ZIP creado: $archive"
echo 'Incluye conn/ deliberadamente. No es un respaldo del volumen PostgreSQL.'
if [[ "$upload" == 1 ]]; then gsutil cp "$archive" "$bucket"; fi
