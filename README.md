# MattisClicker

En cross-platform autoclicker byggd för Linux (KDE Plasma/Wayland) och Windows.

## Fungerar den på Windows?

**Ja.** Samma kod kör på Windows, Linux och macOS (GUI är tkinter som följer med
Python). Appen väljer automatiskt rätt backend:
- **Linux/Wayland:** `evdev` (läser hårdvaran globalt, fungerar i spel).
- **Windows/macOS/X11:** `pynput`.

## Funktioner

- Justera CPS från 1 till 250, antingen med reglaget **eller** genom att skriva
  ett exakt antal i textrutan bredvid.
- **Rebinda aktiveringsknappen**: klicka på knappen "Aktivering" i appen och
  tryck sedan på tangenten eller musknappen du vill använda (Esc avbryter).
- Stöd för **kombinationer** som t.ex. `Ctrl+Alt+Shift+F5` - håll ned alla
  knapparna när du spelar in.
- Stöd för **alla musknappar**, inklusive sidoknapparna **Musknapp 4** och
  **Musknapp 5** på spelmöss.
- Håll ned aktiveringsknappen för att klicka, släpp för att stoppa (eller gångväxla).
- Inställningar sparas i `~/.config/MattisClicker/config.json`.
- GUI byggt med Tkinter.

---

## Windows-användare (skicka till kompisar!)

Det finns två sätt att dela med sig:

### Alternativ 1: Färdig `.exe` (enklast, inget Python behövs)

1. Bygg `.exe` **på en Windows-dator** (PyInstaller kan bara bygga för samma OS):
   ```
   pip install -r requirements.txt pyinstaller
   build_windows.bat
   ```
2. Filen `dist\MattisClicker.exe` dyker upp.
3. Skicka bara den filen till kompisarna. De **dubbelklickar på den** och den
   bara funkar – ingen installation behövs.
   > OBS: Windows och antivirus kan varna för okända exe-filer. Det är normalt
   > för egenkompilerade program; kompisen väljer "Kör ändå".

### Alternativ 2: Skicka koden (kräver Python hos kompisen)

1. Skicka hela mappen (eller zip:a den, ta bort `venv`/`dist`).
2. Kompisen installerar Python från https://www.python.org/downloads/ (markera
   **"Add Python to PATH"**).
3. I mappen:
   ```
   pip install -r requirements.txt
   run.bat
   ```

---

## Linux / KDE Plasma

```bash
./install.sh
```

Det installerar appen i applikationsmenyn (tryck på Super-tangenten och sök efter
"MattisClicker"). Ikonen skapas med:

```bash
python3 gen_icon.py
```

## Installera beroenden

```bash
pip install -r requirements.txt
```

## Kör

```bash
./run.sh
```

## Wayland (KDE Plasma)

- Appen föredrar evdev (`/dev/input`), som läser tangentbord och mus **globalt** –
  alltså funkar aktiveringen i webbläsare och helskärmspel, även Wayland-spel.
  Det kräver att din användare har rätt att läsa hårdvaran.

  Kör en gång (med lösenord):
  ```bash
  sudo ./setup_permissions.sh
  ```
  ...eller manuellt: `sudo usermod -aG input $USER` och logga ut/in igen.

- Utan det faller appen tillbaka till X11-läge. Då visas varningen
  "X11-läge" i appen och aktiveringsknappen hörs **bara när fönstret är i fokus**
  – inte i webbläsare eller Wayland-spel.
- `/dev/uinput` (att *klicka*) fungerar här direkt via systemets ACL.

## Bygga en fristående binär (Linux)

```bash
./build_app.sh
```

Det installeras sedan i `~/.local/share/MattisClicker` och dyker upp i
applikationsmenyn.