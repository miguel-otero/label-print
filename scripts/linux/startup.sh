#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo 'Uso: bash scripts/linux/startup.sh -t docker [-t jq] [-t unzip] [-t zip] [-t gcloud]'
    echo 'Instala herramientas para Ubuntu/Debian. Docker incluye Compose y Buildx.'
    echo 'Use sudo si el usuario no puede instalar paquetes.'
}
tools=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--tool)
            [[ $# -ge 2 ]] || { usage >&2; exit 2; }
            case "$2" in docker|jq|unzip|zip|gcloud) tools+=("$2") ;; *) usage >&2; exit 2 ;; esac
            shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done
[[ ${#tools[@]} -gt 0 ]] || { usage >&2; exit 2; }
[[ -f /etc/os-release ]] || { echo 'Se requiere Ubuntu o Debian.' >&2; exit 1; }
source /etc/os-release
case "$ID" in ubuntu|debian) ;; *) echo 'Solo se soportan Ubuntu y Debian.' >&2; exit 1 ;; esac
command -v apt-get >/dev/null || { echo 'Falta apt-get.' >&2; exit 1; }
elevate=()
if [[ "$EUID" -ne 0 ]]; then
    command -v sudo >/dev/null || { echo 'Ejecute como root o instale sudo.' >&2; exit 1; }
    elevate=(sudo)
fi
as_root() { "${elevate[@]}" env DEBIAN_FRONTEND=noninteractive "$@"; }
install_docker() {
    if command -v docker >/dev/null && docker compose version >/dev/null 2>&1 && docker buildx version >/dev/null 2>&1; then
        echo 'Docker, Compose y Buildx ya estan disponibles.'
        return
    fi
    as_root apt-get update
    as_root apt-get install -y ca-certificates curl gnupg
    as_root install -m 0755 -d /etc/apt/keyrings
    # ASCII key avoids interactive gpg overwrite prompts on repeated runs.
    curl -fsSL "https://download.docker.com/linux/$ID/gpg" | as_root tee /etc/apt/keyrings/docker.asc >/dev/null
    as_root chmod a+r /etc/apt/keyrings/docker.asc
    printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/%s %s stable\n' \
        "$(dpkg --print-architecture)" "$ID" "$VERSION_CODENAME" | as_root tee /etc/apt/sources.list.d/docker.list >/dev/null
    as_root apt-get update
    as_root apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    as_root systemctl enable --now docker
    docker compose version
    echo 'Si el usuario no tiene permisos sobre Docker, use sudo o solicite acceso al administrador.'
}
install_gcloud() {
    if command -v gcloud >/dev/null && command -v gsutil >/dev/null; then return; fi
    as_root apt-get update
    as_root apt-get install -y ca-certificates curl gnupg
    as_root install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
        | as_root gpg --batch --yes --dearmor -o /etc/apt/keyrings/cloud.google.gpg
    as_root chmod a+r /etc/apt/keyrings/cloud.google.gpg
    echo 'deb [signed-by=/etc/apt/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main' \
        | as_root tee /etc/apt/sources.list.d/google-cloud-sdk.list >/dev/null
    as_root apt-get update
    as_root apt-get install -y google-cloud-cli
}
for tool in "${tools[@]}"; do
    case "$tool" in
        docker) install_docker ;;
        gcloud) install_gcloud ;;
        jq|unzip|zip)
            if ! command -v "$tool" >/dev/null; then
                as_root apt-get update
                as_root apt-get install -y "$tool"
            fi ;;
    esac
done
