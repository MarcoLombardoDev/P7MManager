#!/usr/bin/env bash
# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Run P7M Manager from a source checkout, creating the virtual environment on
# first use. Nothing is installed system-wide.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv="$here/.venv"
python="${PYTHON:-python3}"

if [ ! -d "$venv" ]; then
    echo "Creating the virtual environment in .venv …"
    "$python" -m venv "$venv"
    "$venv/bin/pip" install --upgrade pip >/dev/null
    "$venv/bin/pip" install -r "$here/requirements.txt"
fi

exec "$venv/bin/python" -m p7mmanager "$@"
