#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd -- "${HERE}/.." && pwd -P)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is not installed." >&2
    exit 1
fi

exec python3 "${ROOT}/source/nuxpad.py" "$@"
