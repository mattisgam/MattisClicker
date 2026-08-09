#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$HOME/.local/share/MattisClicker"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

mkdir -p "$APP_DIR" "$HOME/.local/share/applications" "$ICON_DIR"

cp -f "$DIR/main.py" "$DIR/requirements.txt" "$DIR/run.sh" "$DIR/setup_permissions.sh" "$DIR/run.bat" "$DIR/build_windows.bat" "$APP_DIR/"
if [ -d "$DIR/venv" ]; then
  cp -rf "$DIR/venv" "$APP_DIR/venv"
fi
cp -f "$DIR/assets/mattisclicker.png" "$ICON_DIR/mattisclicker.png"
chmod +x "$APP_DIR/run.sh"

cat > "$APP_DIR/MattisClicker.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=MattisClicker
GenericName=Autoclicker
Comment=Autoclicker för KDE Plasma (Wayland och X11)
Exec=$APP_DIR/run.sh
Icon=mattisclicker
Terminal=false
Categories=Utility;Game;Accessibility;
Keywords=click;autoclick;auto-click;macro;
StartupNotify=false
EOF

cp -f "$APP_DIR/MattisClicker.desktop" "$HOME/.local/share/applications/"
# Ta bort gamla/VSCode-skapade poster som pekar på fel sökväg.
rm -f "$HOME/.local/share/applications/mattisclicker.desktop"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo "MattisClicker är installerad!"
echo "Sök efter 'MattisClicker' i applikationsmenyn (Super-tangenten)."