#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$(dirname "$0")" || exit 1
printf '\nAEON Termux launcher\nRepository: %s\n\n' "$PWD"
# Run the current worker in the foreground. This avoids an old detached daemon
# surviving a source update and continuing to write stale world telemetry.
export AEON_FOREGROUND=1
exec python -u aeon.py "$@"
