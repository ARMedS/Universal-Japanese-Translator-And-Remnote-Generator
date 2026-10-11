#!/usr/bin/env bash
# Register Plasma bindings for the KDE edition.
#   Super+Shift+U -> raise   Super+Shift+J -> capture
# User-level: no sudo needed. Log out/in (or toggle a shortcut in System
# Settings) if a new binding does not fire.
set -euo pipefail
KW="${KWRITECONFIG:-kwriteconfig5}"
command -v "$KW" >/dev/null || { echo "kwriteconfig5 not found"; exit 1; }

GROUP="services"
ROOT="$(cd "$(dirname "$0")" && pwd)"

"$KW" --file kglobalshortcutsrc --group "$GROUP" \
  --key "ujt-kde-raise.desktop" "Meta+Shift+U,none,Raise Japanese Translator"
"$KW" --file kglobalshortcutsrc --group "$GROUP" \
  --key "ujt-kde-capture.desktop" "Meta+Shift+J,none,Capture with Japanese Translator"

cp "$ROOT/ujt.desktop" "$HOME/.local/share/applications/ujt-kde.desktop"
cp "$ROOT/ujt-raise.desktop" "$HOME/.local/share/applications/ujt-kde-raise.desktop"

cat > "$HOME/.local/share/applications/ujt-kde-capture.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Capture with Japanese Translator (KDE)
Exec=RUNSH --capture
Icon=ICONPATH
Terminal=false
NoDisplay=true
Categories=Utility;Education;
EOF
sed -i "s|RUNSH|$ROOT/run.sh|; s|ICONPATH|$ROOT/../media/Icon1.ico|" \
  "$HOME/.local/share/applications/ujt-kde-capture.desktop"

# kded5 reloads global shortcuts when kglobalshortcutsrc changes are saved via
# the kcm; from CLI a reload request usually works:
if command -v qdbus >/dev/null; then
  qdbus org.kde.kglobalaccel /kglobalaccel org.kde.KGlobalAccel.rereadConfiguration 2>/dev/null \
    || true
fi
echo "Installed ujt-kde launchers and Super+Shift+U / Super+Shift+J bindings."
echo "If a key does not fire, log out and back in once."
