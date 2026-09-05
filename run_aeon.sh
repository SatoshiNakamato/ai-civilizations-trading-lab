#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$(dirname "$0")"
printf '\nAEON Termux launcher\n'
printf 'Repository: %s\n\n' "$PWD"
python -u aeon.py
status=$?
printf '\nAEON exited with status %s\n' "$status"
exit "$status"
