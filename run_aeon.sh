#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$(dirname "$0")" || exit 1
printf '\nAEON Termux launcher\nRepository: %s\n\n' "$PWD"
exec python -u -m civilizations.command_center "$@"
