#!/usr/bin/env bash
# Launch the KDE edition. Also used as:
#   ./run.sh --raise     # pop the capture frame over the game
#   ./run.sh --capture
# from a Plasma custom shortcut.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv --system-site-packages .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
fi

KEY_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/ujt-kde/keys.env"
if [[ -f "$KEY_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$KEY_FILE"
  set +a
fi

# Same config layout as the Wayland app but separate folder so the two
# installs do not fight over settings.  Point it at the shared one:
if [[ -f "${XDG_CONFIG_HOME:-$HOME/.config}/ujt/keys.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${XDG_CONFIG_HOME:-$HOME/.config}/ujt/keys.env"
  set +a
fi

# X11 is the native session here; pass through if the user already set one.
if [[ -z "${QT_QPA_PLATFORM:-}" ]]; then
  export QT_QPA_PLATFORM=xcb
fi

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec .venv/bin/python -m ujt "$@"
