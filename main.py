import glob
import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from pynput import keyboard, mouse
except ImportError:
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "MattisClicker saknar paket",
        "Paketet pynput saknas. Installera det med:\n\n"
        "    pip install -r requirements.txt\n",
    )
    sys.exit(1)

try:
    import evdev
    from evdev import ecodes
except ImportError:
    evdev = None

MODIFIER_NAMES = {"ctrl", "alt", "shift"}

CPS_MIN = 1
CPS_MAX = 250

OUTPUT_OPTIONS = ["Left", "Right", "Middle"]

# ---- Moderna UI-färger (mörkt tema) ----
BG = "#0f1115"
CARD = "#171a21"
CARD2 = "#1d212b"
FIELD = "#232733"
BORDER = "#2e3342"
TEXT = "#eef1f8"
MUTED = "#8b93a7"
ACCENT = "#4f8cff"
ACCENT_HOVER = "#6ba2ff"
ACCENT_PRESS = "#3971e0"
OK = "#4ade80"
IDLE = "#525a6b"
FONT_FAMILY = "Cantarell"


def hex_blend(color1, color2, t):
    """Interpolerar mellan två hex-färger. t=0 ger color1, t=1 ger color2."""
    t = max(0.0, min(1.0, t))

    def parse(hex_color):
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return r, g, b

    r1, g1, b1 = parse(color1)
    r2, g2, b2 = parse(color2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"

MODIFIER_DISPLAY = {
    "ctrl": "Ctrl",
    "alt": "Alt",
    "shift": "Shift",
}

KEY_DISPLAY = {
    "space": "Space",
    "enter": "Enter",
    "tab": "Tab",
    "esc": "Esc",
    "left": "Vänster musknapp",
    "right": "Höger musknapp",
    "middle": "Mitten musknapp",
    "mouse4": "Musknapp 4 (sidoknapp)",
    "mouse5": "Musknapp 5 (sidoknapp)",
}

PYNPUT_BUTTON_TO_NAME = {
    "left": "left",
    "right": "right",
    "middle": "middle",
    "x1": "mouse4",
    "x2": "mouse5",
}

MOUSE_NAME_TO_PYNPUT = {
    "left": mouse.Button.left,
    "right": mouse.Button.right,
    "middle": mouse.Button.middle,
}


def _build_evdev_name_code_map():
    if evdev is None:
        return {}
    code_to_name = {}

    def add(name, code):
        if code is not None:
            code_to_name[code] = name

    for i in range(1, 13):
        add(f"f{i}", getattr(ecodes, f"KEY_F{i}", None))
    for c in "abcdefghijklmnopqrstuvwxyz":
        add(c, getattr(ecodes, f"KEY_{c.upper()}", None))
    for d in "1234567890":
        add(d, getattr(ecodes, f"KEY_{d}", None))
    for name, attr in [
        ("space", "KEY_SPACE"),
        ("enter", "KEY_ENTER"),
        ("shift", "KEY_LEFTSHIFT"),
        ("ctrl", "KEY_LEFTCTRL"),
        ("alt", "KEY_LEFTALT"),
        ("tab", "KEY_TAB"),
        ("esc", "KEY_ESC"),
    ]:
        add(name, getattr(ecodes, attr, None))
    add("shift", getattr(ecodes, "KEY_RIGHTSHIFT", None))
    add("ctrl", getattr(ecodes, "KEY_RIGHTCTRL", None))
    add("alt", getattr(ecodes, "KEY_RIGHTALT", None))
    for name, code in [
        ("left", getattr(ecodes, "BTN_LEFT", None)),
        ("right", getattr(ecodes, "BTN_RIGHT", None)),
        ("middle", getattr(ecodes, "BTN_MIDDLE", None)),
        ("mouse4", getattr(ecodes, "BTN_SIDE", None)),
        ("mouse5", getattr(ecodes, "BTN_EXTRA", None)),
    ]:
        add(name, code)
    return code_to_name


EVDEV_NAME_TO_CODE = {}


def parse_binding(binding):
    """Delar upp en binding som 'ctrl+alt+shift+f5' i (modifierare, tangent)."""
    if not binding:
        return set(), None
    parts = binding.split("+")
    mods = {p for p in parts[:-1] if p in MODIFIER_NAMES}
    return mods, parts[-1].lower()


def display_binding(binding):
    if not binding:
        return ""
    mods, key = parse_binding(binding)
    text = "+".join(MODIFIER_DISPLAY.get(m, m) for m in sorted(mods))
    if key:
        name = KEY_DISPLAY.get(key, key.upper() if len(key) == 1 or key.startswith("f") or key.isdigit() else key.title())
        text = f"{text}+{name}" if text else name
    return text


class PynputBackend:
    """Backend X11/XWayland via pynput. Ser att man trycker på tangentbordet
    och musen (inklusive sidoknappar 4 och 5)."""

    def __init__(self, app):
        self.app = app
        self.controller = mouse.Controller()
        self.key_listener = None
        self.mouse_listener = None

    def start(self):
        self.key_listener = keyboard.Listener(
            on_press=lambda k: self._on_key(k, True),
            on_release=lambda k: self._on_key(k, False),
        )
        self.mouse_listener = mouse.Listener(on_click=self._on_mouse)
        self.key_listener.start()
        self.mouse_listener.start()

    def stop(self):
        for listener in (self.key_listener, self.mouse_listener):
            if listener:
                listener.stop()

    def _key_to_name(self, key):
        if hasattr(key, "char") and key.char:
            return key.char.lower()
        name = getattr(key, "name", None)
        if name:
            return name
        return None

    def _on_key(self, key, pressed):
        name = self._key_to_name(key)
        if name:
            self.app.on_input(name, pressed)

    def _on_mouse(self, x, y, button, pressed):
        name = getattr(button, "name", None)
        mapped = PYNPUT_BUTTON_TO_NAME.get(name, name)
        if mapped:
            self.app.on_input(mapped, pressed)

    def click(self, output_name):
        button = MOUSE_NAME_TO_PYNPUT[output_name]
        self.controller.press(button)
        self.controller.release(button)


class EvdevBackend:
    """Backend för Wayland/KDE Plasma via /dev/input.
    Med den här ser appen ALLT som händer med hårdvaran, oavsett vilket
    fönster som har fokus - perfekt för spel och alla möss/kängor."""

    def __init__(self, app):
        if evdev is None:
            raise RuntimeError(
                "Paketet 'evdev' saknas. Installera det med:\n"
                "    pip install evdev"
            )
        self.app = app
        self.threads = []
        self.devices = []
        self.uinput = None
        global EVDEV_NAME_TO_CODE
        EVDEV_NAME_TO_CODE = {name: code for code, name in _build_evdev_name_code_map().items()}

    def start(self):
        code_to_name = _build_evdev_name_code_map()
        if not code_to_name:
            raise RuntimeError("Hittade inga tangentbord/musenheter.")
        for path in sorted(glob.glob("/dev/input/event*")):
            try:
                device = evdev.InputDevice(path)
                caps = device.capabilities()
                if 1 in caps and any(c in caps[1] for c in code_to_name):
                    self.devices.append(device)
            except (PermissionError, OSError):
                continue
        if not self.devices:
            raise RuntimeError(
                "Wayland kräver tillgång till /dev/input.\n\n"
                "Kör appen som sudo:\n"
                "    sudo ./run.sh\n\n"
                "Eller lägg dig i gruppen 'input':\n"
                "    sudo usermod -aG input $USER\n"
                "logga sedan ut och in igen."
            )
        try:
            self.uinput = evdev.UInput(
                {evdev.ecodes.EV_KEY: list(code_to_name)},
                name="MattisClicker",
            )
        except Exception:
            raise RuntimeError(
                "Kunde inte skapa virtuell mus (UInput).\n"
                "Du behöver sudo eller gruppen 'uinput':\n\n"
                "    sudo usermod -aG uinput $USER\n"
                "logga sedan ut och in igen."
            )
        for device in self.devices:
            thread = threading.Thread(target=self._read_loop, args=(device,), daemon=True)
            thread.start()
            self.threads.append(thread)

    def stop(self):
        for device in self.devices:
            try:
                device.close()
            except Exception:
                pass
        if self.uinput:
            self.uinput.close()

    def _read_loop(self, device):
        code_to_name = _build_evdev_name_code_map()
        try:
            for event in device.read_loop():
                if event.type != evdev.ecodes.EV_KEY:
                    continue
                name = code_to_name.get(event.code)
                if name is None:
                    continue
                self.app.on_input(name, event.value == 1)
        except OSError:
            pass

    def click(self, output_name):
        button = EVDEV_NAME_TO_CODE[output_name]
        self.uinput.write(evdev.ecodes.EV_KEY, button, 1)
        self.uinput.syn()
        self.uinput.write(evdev.ecodes.EV_KEY, button, 0)
        self.uinput.syn()


class MattisClickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MattisClicker")
        self.root.geometry("460x540")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self._setup_style()

        config = self._load_config()

        self.cps_var = tk.IntVar(value=config.get("cps", 10))
        self.output_var = tk.StringVar(value=config.get("output", "Left"))
        self.hold_mode_var = tk.BooleanVar(value=config.get("hold", True))
        self.status_var = tk.StringVar(value="Inaktiv")
        self.info_var = tk.StringVar(value="")

        self.binding = config.get("binding", "f6")
        self.held_mods = set()
        self.active_key = None
        self.clicking = threading.Event()
        self.click_thread = None
        self.backend = None
        self.recording = False
        self.record_mods = set()
        self.record_timer = None

        self._build_ui()
        self._start_backend()

    def _config_path(self):
        cfg_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        return os.path.join(cfg_dir, "MattisClicker", "config.json")

    def _load_config(self):
        try:
            with open(self._config_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_config(self):
        try:
            path = self._config_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "binding": self.binding,
                        "cps": self.cps_var.get(),
                        "output": self.output_var.get(),
                        "hold": bool(self.hold_mode_var.get()),
                    },
                    f,
                    indent=2,
                )
        except Exception:
            pass

    def _setup_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", font=(FONT_FAMILY, 10), background=BG, foreground=TEXT)

        # Rubriker
        style.configure("Brand.TLabel", background=BG, foreground=TEXT, font=(FONT_FAMILY, 20, "bold"))
        style.configure("Tagline.TLabel", background=BG, foreground=MUTED, font=(FONT_FAMILY, 9))
        style.configure("Section.TLabel", background=CARD, foreground=TEXT, font=(FONT_FAMILY, 10, "bold"))
        style.configure("Field.TLabel", background=CARD, foreground=MUTED, font=(FONT_FAMILY, 9))
        style.configure("Value.TLabel", background=CARD, foreground=ACCENT_HOVER, font=(FONT_FAMILY, 18, "bold"))
        style.configure("Status.TLabel", background=CARD, foreground=TEXT, font=(FONT_FAMILY, 10, "bold"))

        # Primär knapp (binda/nu)
        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground=BG,
            bordercolor=ACCENT,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            padding=(14, 9),
            font=(FONT_FAMILY, 13, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("pressed", ACCENT_PRESS), ("active", ACCENT_HOVER)],
            bordercolor=[("pressed", ACCENT_PRESS), ("active", ACCENT_HOVER)],
            lightcolor=[("pressed", ACCENT_PRESS), ("active", ACCENT_HOVER)],
            darkcolor=[("pressed", ACCENT_PRESS), ("active", ACCENT_HOVER)],
        )

        # Liten accent-knapp (kör-knapp under status)
        style.configure(
            "Go.TButton",
            background=CARD2,
            foreground=OK,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=(12, 8),
            font=(FONT_FAMILY, 11, "bold"),
        )
        style.map(
            "Go.TButton",
            background=[("pressed", FIELD), ("active", CARD2)],
            bordercolor=[("pressed", ACCENT_PRESS), ("active", ACCENT_HOVER)],
            lightcolor=[("active", BORDER)],
            darkcolor=[("active", BORDER)],
            foreground=[("disabled", MUTED), ("pressed", "#8bf7b0"), ("active", "#8bf7b0")],
        )

        # Reglage
        style.configure(
            "Accent.Horizontal.TScale",
            background=CARD,
            troughcolor=FIELD,
            bordercolor=BORDER,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            sliderlength=22,
            sliderrelief="flat",
        )
        style.map(
            "Accent.Horizontal.TScale",
            background=[("active", CARD)],
            troughcolor=[("active", FIELD)],
        )

        # Spinbox
        style.configure(
            "TSpinbox",
            fieldbackground=CARD2,
            background=CARD2,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            arrowcolor=MUTED,
            insertcolor=TEXT,
            padding=5,
        )
        style.map(
            "TSpinbox",
            fieldbackground=[("focus", CARD2)],
            bordercolor=[("focus", ACCENT)],
            arrowcolor=[("active", ACCENT_HOVER)],
        )

        # Karta (kort)
        style.configure("TK_Frame_Card", background=CARD)

    def _build_card(self, parent, title):
        card = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=BORDER, highlightcolor=BORDER)
        card.pack(fill="x", pady=(0, 10))
        ttk.Label(card, text=title, style="Section.TLabel").pack(anchor="w", padx=14, pady=(10, 2))
        return card

    def _build_ui(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="both", expand=True)

        # Header med accentlist
        tk.Frame(frame, bg=ACCENT, height=3).pack(fill="x")
        header = tk.Frame(frame, bg=BG)
        header.pack(fill="x", padx=16, pady=(14, 12))
        ttk.Label(header, text="MattisClicker", style="Brand.TLabel").pack(anchor="w")
        ttk.Label(header, text="Autoclicker för Windows & Linux", style="Tagline.TLabel").pack(anchor="w", pady=(2, 0))

        # ---- CPS-kort ----
        cps_card = self._build_card(frame, "KLICKHASTIGHET")
        cps_top = tk.Frame(cps_card, bg=CARD)
        cps_top.pack(fill="x", padx=14, pady=(0, 2))
        ttk.Label(cps_top, text="klick per sekund", style="Field.TLabel").pack(side="left")
        self.cps_value_label = ttk.Label(cps_top, text=f"{self.cps_var.get()} CPS", style="Value.TLabel")
        self.cps_value_label.pack(side="right")
        slider_row = tk.Frame(cps_card, bg=CARD)
        slider_row.pack(fill="x", padx=14, pady=(4, 6))
        self.cps_slider = ttk.Scale(slider_row, variable=self.cps_var, from_=CPS_MIN, to=CPS_MAX, orient="horizontal", style="Accent.Horizontal.TScale", command=self._on_slider_cps)
        self.cps_slider.pack(side="left", fill="x", expand=True, pady=(6, 0))
        self.cps_spin = ttk.Spinbox(slider_row, from_=CPS_MIN, to=CPS_MAX, increment=1, textvariable=self.cps_var, width=6, command=self._sync_cps_from_entry)
        self.cps_spin.pack(side="left", padx=(10, 0), pady=(0, 6))
        self.cps_spin.bind("<Return>", lambda event: self._sync_cps_from_entry())
        self.cps_spin.bind("<FocusOut>", lambda event: self._sync_cps_from_entry())

        # ---- Aktivering-kort ----
        bind_card = self._build_card(frame, "AKTIVERING")
        ttk.Label(bind_card, text="Klicka för att spela in en tangent, musknapp eller kombination (t.ex. Ctrl+Alt+Shift+F5).", style="Field.TLabel", wraplength=400).pack(anchor="w", padx=14, pady=(4, 10))
        self.bind_button = ttk.Button(bind_card, text=display_binding(self.binding), style="Accent.TButton", command=self._start_recording)
        self.bind_button.pack(fill="x", padx=14, pady=(0, 12))

        # ---- Klickknapp-kort ----
        out_card = self._build_card(frame, "KLICKKNAPP")
        self._add_option(out_card, "Vilken knapp ska klickas:", self.output_var, OUTPUT_OPTIONS)

        # ---- Läge-kort ----
        mode_card = self._build_card(frame, "LÄGE")
        mode_row = tk.Frame(mode_card, bg=CARD)
        mode_row.pack(fill="x", padx=14, pady=(4, 12))
        ttk.Label(mode_row, text="Håll ned för att klicka", style="Field.TLabel").pack(side="left")
        self._make_switch(mode_row, self.hold_mode_var).pack(side="right")

        # ---- Status ----
        status_card = self._build_card(frame, "STATUS")
        status_row = tk.Frame(status_card, bg=CARD)
        status_row.pack(fill="x", padx=14, pady=(4, 2))
        self.status_lamp = tk.Canvas(status_row, width=14, height=14, bg=CARD, highlightthickness=0)
        self.status_lamp.pack(side="left")
        self._status_lamp_item = self.status_lamp.create_oval(2, 2, 12, 12, fill=IDLE, outline="")
        self.status_label = ttk.Label(status_row, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.pack(side="left", padx=(8, 0))
        self.info_label = ttk.Label(status_card, textvariable=self.info_var, style="Field.TLabel", wraplength=400, justify="left")
        self.info_label.pack(anchor="w", padx=14, pady=(0, 10))

        ttk.Button(frame, text="Avsluta", style="Go.TButton", command=self._on_close).pack(anchor="e", padx=16, pady=(0, 14))

        # Spara ALLA inställningar när de ändras (cps, knappval, läge)
        for var in (self.cps_var, self.output_var, self.hold_mode_var):
            var.trace_add("write", lambda *a: self._save_config())

    def bind_button_text(self):
        text = display_binding(self.binding)
        self.bind_button.config(text=text or "Klicka för att spela in")

    def _make_switch(self, parent, variable):
        """Modern toggle (canvas-switch) – omedelbar, med hover/press-feedback."""
        knob_diameter = 20
        switch = tk.Canvas(parent, width=44, height=24, bg=CARD, highlightthickness=0, cursor="hand2")

        state = {"hover": False, "pressed": False}
        KNOB_OFF = "#b6bece"
        KNOB_ON = "#ffffff"
        SHADOW = "#0c0e13"
        TRACK_IN = "#3b78d9"

        def draw_track(on):
            base = ACCENT if on else FIELD
            inner = TRACK_IN if on else "#1b1f29"
            switch.delete("track")
            switch.create_oval(2, 4, 22, 24, fill=base, outline=base, tags="track")
            switch.create_oval(24, 4, 44, 24, fill=base, outline=base, tags="track")
            switch.create_rectangle(12, 4, 32, 24, fill=base, outline=base, tags="track")
            switch.create_oval(5, 7, 21, 21, fill=inner, outline="", tags="track")
            switch.create_oval(25, 7, 41, 21, fill=inner, outline="", tags="track")
            switch.create_rectangle(15, 7, 31, 21, fill=inner, outline="", tags="track")

        def draw_knob(x, on):
            base = KNOB_ON if on else KNOB_OFF
            if state["hover"]:
                base = hex_blend(base, "#ffffff", 0.30)
            if state["pressed"]:
                base = hex_blend(base, "#000000", 0.25)
            shadow_y = 6 if state["pressed"] else 5
            dy = 1 if state["pressed"] else 0
            switch.delete("knob")
            switch.create_oval(x + 1, shadow_y, x + knob_diameter + 1, shadow_y + knob_diameter, fill=SHADOW, outline="", tags="knob")
            switch.create_oval(x, 4 + dy, x + knob_diameter, 24 + dy, fill=base, outline="", tags="knob")
            gloss = hex_blend(base, "#ffffff", 0.45)
            switch.create_oval(x + 5, 6 + dy, x + 15, 13 + dy, fill=gloss, outline="", tags="knob")

        def redraw(*_args):
            on = bool(variable.get())
            x = knob_diameter if on else 0.0
            draw_track(on)
            draw_knob(x, on)

        def on_enter(event):
            state["hover"] = True
            redraw()

        def on_leave(event):
            state["hover"] = False
            state["pressed"] = False
            redraw()

        def on_press(event):
            state["pressed"] = True
            redraw()

        def on_release(event):
            state["pressed"] = False
            redraw()

        switch.bind("<Enter>", on_enter)
        switch.bind("<Leave>", on_leave)
        switch.bind("<ButtonPress-1>", on_press)
        switch.bind("<ButtonRelease-1>", on_release)
        switch.bind("<Button-1>", lambda event: variable.set(not bool(variable.get())))
        variable.trace_add("write", redraw)
        redraw()
        return switch

    def _add_option(self, row, label_text, variable, values):
        """Segmenterad kontroll för vilken musknapp som ska klickas."""
        subrow = tk.Frame(row, bg=CARD)
        subrow.pack(fill="x", pady=(0, 10))
        ttk.Label(subrow, text=label_text, style="Field.TLabel").pack(side="left")

        seg = tk.Frame(subrow, bg=CARD)
        seg.pack(side="right")

        buttons = {}
        for index, value in enumerate(values):
            btn = tk.Label(
                seg,
                text=value,
                width=6,
                padx=6,
                pady=3,
                bg=FIELD,
                fg=MUTED,
                font=(FONT_FAMILY, 10, "bold"),
                cursor="hand2",
            )
            btn.grid(row=0, column=index, padx=(0 if index == 0 else 1, 0))
            btn.bind("<Button-1>", lambda e, v=value: self._set_output(seg, buttons, v))
            buttons[value] = btn
        self._set_output(seg, buttons, variable.get(), render_only=True)

    def _set_output(self, seg, buttons, value, render_only=False):
        if not render_only:
            self.output_var.set(value)
        for name, btn in buttons.items():
            if name == value:
                btn.config(bg=ACCENT, fg=BG)
            else:
                btn.config(bg=FIELD, fg=MUTED)

    def _on_slider_cps(self, value):
        self.cps_var.set(max(CPS_MIN, min(CPS_MAX, int(float(value)))))
        self._cps_label_update()

    def _cps_label_update(self):
        if hasattr(self, "cps_value_label"):
            self.cps_value_label.config(text=f"{self.cps_var.get()} CPS")

    def _sync_cps_from_entry(self):
        try:
            value = int(self.cps_spin.get())
            self.cps_var.set(max(CPS_MIN, min(CPS_MAX, value)))
        except ValueError:
            pass
        self._cps_label_update()

    def _start_backend(self):
        errors = []
        if sys.platform.startswith("linux"):
            try:
                self.backend = EvdevBackend(self)
            except Exception as error:
                errors.append(str(error))
            else:
                try:
                    self.backend.start()
                    self._on_backend_ready()
                    return
                except Exception as error:
                    errors.append(str(error))
        try:
            self.backend = PynputBackend(self)
        except Exception as error:
            errors.append(str(error))
        else:
            try:
                self.backend.start()
                self._on_backend_ready()
                return
            except Exception as error:
                errors.append(str(error))
        self.status_var.set("Ingen åtkomst till enheter!")
        self.info_var.set("")
        messagebox.showerror("MattisClicker", "\n\n".join(errors))

    def _on_backend_ready(self):
        self.status_var.set("Tryck på " + display_binding(self.binding))
        if isinstance(self.backend, EvdevBackend):
            self.info_var.set("Global (läser hela systemet – fungerar i alla appar/spel)")
        else:
            self.info_var.set("X11-läge: aktiveringen hörs bara när fönstret är i fokus")

    # ---- Inspelning av aktiveringsknapp ----

    def _start_recording(self):
        self.recording = True
        self.record_mods = set()
        self.status_var.set("Tryck på ny aktiveringsknapp... (Esc avbryter)")
        self.bind_button.config(text="Lyssnar...")
        self.record_timer = self.root.after(20000, self._stop_recording)

    def _stop_recording(self, cancelled=True):
        if not self.recording:
            return
        self.recording = False
        if self.record_timer:
            self.root.after_cancel(self.record_timer)
            self.record_timer = None
        self.bind_button_text()
        if cancelled:
            self.status_var.set("Inspelning avbruten")
        else:
            self._on_backend_ready()

    def _capture_binding(self, key_name, mods):
        if mods:
            self.binding = "+".join(sorted(mods)) + "+" + key_name
        else:
            self.binding = key_name
        self._save_config()
        self._stop_recording(cancelled=False)
        self.status_var.set(f"Bunden: {display_binding(self.binding)}")

    def on_input(self, name, pressed):
        """Alla tangent- och musevenighter från backenden hamnar här."""
        if name is None:
            return
        if self.recording:
            if not pressed:
                return
            if name == "esc":
                self._stop_recording(cancelled=True)
            elif name in MODIFIER_NAMES:
                self.record_mods.add(name)
            else:
                self._capture_binding(name, self.record_mods)
            return

        if name in MODIFIER_NAMES:
            if pressed:
                self.held_mods.add(name)
            else:
                self.held_mods.discard(name)
                self._maybe_stop_due_to_combo()
            return

        if self._combo_matches(name):
            self._on_activation(pressed)
            self.active_key = name if pressed else None
        elif not pressed and self.active_key == name:
            self.active_key = None
            self._maybe_stop_due_to_combo()

    def _combo_matches(self, key):
        if not self.binding:
            return False
        mods, bind_key = parse_binding(self.binding)
        return bind_key == key and set(mods) <= set(self.held_mods)

    def _maybe_stop_due_to_combo(self):
        """I håll-ned-läge: stoppa klicka om kombinationen inte matchar längre.
        I toggle-läge (gångväxla) får modifier-lyssning aldrig avbryta."""
        if not self.hold_mode_var.get():
            return
        mods, bind_key = parse_binding(self.binding)
        if self.clicking.is_set() and bind_key:
            if self.active_key is None or not self._combo_matches(self.active_key):
                self._stop_clicking()

    def _on_activation(self, pressed):
        if self.hold_mode_var.get():
            if pressed and not self.clicking.is_set():
                self._start_clicking()
            elif not pressed and self.clicking.is_set():
                self._stop_clicking()
        else:
            if pressed:
                if self.clicking.is_set():
                    self._stop_clicking()
                else:
                    self._start_clicking()

    def _start_clicking(self):
        if self.clicking.is_set() or not self.backend:
            return
        self.clicking.set()
        self.status_var.set(f"Klickar... ({self.cps_var.get()} CPS)")
        self._set_lamp(OK)
        self.click_thread = threading.Thread(target=self._click_loop, daemon=True)
        self.click_thread.start()

    def _click_loop(self):
        output = self.output_var.get().lower()
        while self.clicking.is_set():
            interval = max(1.0 / max(self.cps_var.get(), 1), 0.002)
            self.backend.click(output)
            time.sleep(interval)

    def _stop_clicking(self):
        self.clicking.clear()
        self.status_var.set("Inaktiv")
        self._set_lamp(IDLE)

    def _set_lamp(self, color):
        if hasattr(self, "_status_lamp_item"):
            self.status_lamp.itemconfig(self._status_lamp_item, fill=color)
            self.status_lamp.config(bg=CARD)

    def _on_close(self):
        self._stop_clicking()
        self._save_config()
        if self.backend:
            try:
                self.backend.stop()
            except Exception:
                pass
        self.root.quit()


if __name__ == "__main__":
    root = tk.Tk()
    app = MattisClickerApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app._on_close()
    finally:
        sys.exit(0)