#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/windows-agent-common.sh"
run_windows_agent_script run-print-agent "$@"
