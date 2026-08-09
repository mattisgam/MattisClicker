#!/usr/bin/env bash
set -e

# Ger MattisClicker global åtkomst till tangentbord och mus på Linux.
# Utan detta kan evdev-backendet inte läsa /dev/input och appen faller
# tillbaka till X11-läge där tangenterna bara funkar när fönstret är i fokus.
#
# Kör som root:
#   sudo ./setup_permissions.sh
#
# En udev-regel sätts upp så att rattar i gruppen "input" får läsrätt,
# och din användare läggs till i gruppen.

if [ "$(id -u)" -ne 0 ]; then
  echo "Kör som root: sudo $0"
  exit 1
fi

echo "Skriver udev-regel för /dev/input..."
cat > /etc/udev/rules.d/99-mattisclicker-input.rules << 'EOF'
KERNEL=="event*", SUBSYSTEM=="input", GROUP="input", MODE="0660"
KERNEL=="uinput", SUBSYSTEM=="misc", MODE="0660", GROUP="input"
EOF

echo "Laddar om udev-regler och aktiverar dem..."
udevadm control --reload-rules
udevadm trigger

echo "Klar! Grupp 'input' ger nu tillgång till /dev/input."
echo
echo "Nu ska din användare läggas till i gruppen 'input':"
read -rp "Ange användarnamn: " USER
usermod -aG input "$USER"
echo "Klart! Logga ut och in (eller kör 'newgrp input') för att aktivera."