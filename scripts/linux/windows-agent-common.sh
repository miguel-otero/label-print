#!/usr/bin/env bash
# Shared WSL bridge. Windows spooler/service and Windows binaries cannot run natively on Linux.
run_windows_agent_script() {
    local script_name="$1"
    shift
    local script_dir script_path arg expect_path=0
    if ! command -v powershell.exe >/dev/null || ! command -v wslpath >/dev/null; then
        echo 'Esta tarea requiere Windows. Desde WSL habilite interoperabilidad con powershell.exe y use una terminal Windows elevada para instalar/desinstalar.' >&2
        echo 'En Ubuntu nativo use start.sh para el servidor; compile el instalador en GitHub Actions (windows-agent.yml) o en Windows.' >&2
        return 1
    fi
    script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../powershell" && pwd)"
    script_path="$(wslpath -w "$script_dir/$script_name.ps1")" || return
    local arguments=()
    for arg in "$@"; do
        if [[ "$expect_path" == 1 ]]; then
            # Path-valued options accept WSL paths or existing Windows paths.
            if [[ "$arg" == /* || "$arg" == ./* || "$arg" == ../* ]]; then
                arg="$(wslpath -w "$arg")" || return
            fi
            expect_path=0
        fi
        arguments+=("$arg")
        case "${arg,,}" in
            -innocompilerpath) expect_path=1 ;;
        esac
    done
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$script_path" "${arguments[@]}"
}
