#!/usr/bin/env bash
# Install the app-menu launcher (Super menu) and, optionally, global shortcuts.
# Re-run it after moving this folder: every path is written from where it lives now.
#   Super+Shift+U -> raise the frame   Super+Shift+J -> capture
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$APPS"

write() { # file name comment extra-args hidden
  cat > "$APPS/$1" <<EOT
[Desktop Entry]
Type=Application
Name=$2
Comment=$3
Exec=$ROOT/run.sh$4
Icon=$ROOT/media/Icon1.ico
Terminal=false
Categories=Utility;Education;
StartupWMClass=ujt-kde
NoDisplay=$5
EOT
}

write ujt-kde.desktop "Japanese Translator" "Japanese game and visual novel translator with RemNote flashcards" "" false
write ujt-kde-raise.desktop "Raise Japanese Translator" "Bring the capture frame over the game" " --raise" true
write ujt-kde-capture.desktop "Capture with Japanese Translator" "Translate what is inside the frame" " --capture" true
chmod +x "$ROOT/run.sh"
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true
echo "Launchers written to $APPS (point at $ROOT)."

if [[ "${1:-}" == "--shortcuts" ]]; then
  KW="${KWRITECONFIG:-kwriteconfig5}"
  command -v "$KW" >/dev/null || { echo "kwriteconfig5 not found"; exit 1; }
  "$KW" --file kglobalshortcutsrc --group services \
    --key "ujt-kde-raise.desktop" "Meta+Shift+U,none,Raise Japanese Translator"
  "$KW" --file kglobalshortcutsrc --group services \
    --key "ujt-kde-capture.desktop" "Meta+Shift+J,none,Capture with Japanese Translator"
  command -v qdbus >/dev/null && qdbus org.kde.kglobalaccel /kglobalaccel org.kde.KGlobalAccel.rereadConfiguration 2>/dev/null || true
  echo "Registered Super+Shift+U (raise) and Super+Shift+J (capture)."
fi
