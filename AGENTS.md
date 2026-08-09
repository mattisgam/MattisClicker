# AGENTS.md — Regler för MattisClicker

## Git-regel (VIKTIG – gör alltid detta)

- Efter varje avslutad uppgift/ändring: **commita och pusha**.
- Commitmeddelande på svenska, kort och beskrivande.
- Kör alltid: `git add -A && git commit -m "<meddelande>" && git push`
- Pusha till `origin` (repo: `mattisgam/MattisClicker`).

## Kod

- Ett huvudprogram: `main.py` (tkinter + pynput/evdev).
- Ändra inte `venv/` – den är ignorerad av git.

## Verifiering

- Kör `venv/bin/python -m py_compile main.py` efter ändringar.