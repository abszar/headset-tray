#!/bin/sh
set -eu

# Runs the test suite with the C locale pinned so that assertions on the
# English strings hold on a translated desktop.

project_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"

LANGUAGE=en
LC_ALL=C
LANG=C
export LANGUAGE LC_ALL LANG

exec python3 -m unittest discover "$@"
