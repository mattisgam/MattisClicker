#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 krävs för att bygga appen."
  exit 1
fi

if ! command -v pip >/dev/null 2>&1; then
  echo "Pip krävs för att installera beroenden."
  exit 1
fi

pip install -r requirements.txt

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "Installerar pyinstaller..."
  pip install pyinstaller
fi

pyinstaller --onefile --noconsole --name MattisClicker main.py

APP_DIR="$HOME/.local/share/MattisClicker"
mkdir -p "$APP_DIR" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/256x256/apps"
cp -f "$DIR/dist/MattisClicker" "$APP_DIR/MattisClicker"
cp -f "$DIR/assets/mattisclicker.png" "$HOME/.local/share/icons/hicolor/256x256/apps/mattisclicker.png"
chmod +x "$APP_DIR/MattisClicker"

cat > "$APP_DIR/MattisClicker.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=MattisClicker
GenericName=Autoclicker
Comment=Autoclicker för KDE Plasma (Wayland och X11)
Exec=$APP_DIR/MattisClicker
Icon=mattisclicker
Terminal=false
Categories=Utility;Game;Accessibility;
Keywords=click;autoclick;auto-click;macro;
StartupNotify=false
EOF

cp -f "$APP_DIR/MattisClicker.desktop" "$HOME/.local/share/applications/"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo "Byggt och installerat: $APP_DIR/MattisClicker"
echo "Appen finns nu i applikationsmenyn som 'MattisClicker'."