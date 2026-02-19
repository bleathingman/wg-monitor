"""
WG Monitor — System Resource Monitor
• Theme Manager  (Dark / Light / Midnight / Red)
• Sauvegarde config.json
• Températures CPU/GPU
• Mini widget flottant
• System Tray (pystray)
"""

import customtkinter as ctk
import psutil
import platform
import time
import threading
import json
import os
from datetime import datetime

# ── Optional deps ──────────────────────────
import sys as _sys_module
try:
    import pystray
    from PIL import Image, ImageDraw
    # Sur macOS, pystray nécessite d'être sur le thread principal
    # On le désactive si on est sur macOS et que rumps n'est pas dispo
    if platform.system() == "Darwin":
        try:
            import rumps  # noqa – vérifie juste la présence
            TRAY_OK = True
        except ImportError:
            TRAY_OK = False  # pip install rumps pour activer
    else:
        TRAY_OK = True
except ImportError:
    TRAY_OK = False

UPDATE_INTERVAL = 1000
HISTORY_POINTS  = 60
CONFIG_PATH     = os.path.join(os.path.expanduser("~"), ".wgmonitor_config.json")

# ─────────────────────────────────────────────
#  CONFIG  (save / load)
# ─────────────────────────────────────────────
def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(data: dict):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[config] save error: {e}")

# ─────────────────────────────────────────────
#  THEMES
# ─────────────────────────────────────────────
THEMES = {
    "Dark": {
        "mode": "dark", "accent": "#b76eff", "accent2": "#7c3aed",
        "bg_main": "#0d0d0f", "bg_card": "#141418", "bg_card2": "#1a1a20",
        "bg_border": "#2a2a35", "text_pri": "#ffffff", "text_sec": "#c8c3d8",
        "text_mut": "#8a85a0", "green": "#3dff9a", "orange": "#ff9d3d",
        "red": "#ff4d6a", "blue": "#3dabff", "icon": "🌙",
    },
    "Light": {
        "mode": "light", "accent": "#8b3dff", "accent2": "#6920d4",
        "bg_main": "#f0f0f5", "bg_card": "#ffffff", "bg_card2": "#eaeaf2",
        "bg_border": "#d0cfe8", "text_pri": "#0d0d1a", "text_sec": "#3d3860",
        "text_mut": "#7a76a0", "green": "#00b86b", "orange": "#e07000",
        "red": "#d63050", "blue": "#1a7fe0", "icon": "☀️",
    },
    "Midnight": {
        "mode": "dark", "accent": "#00d4ff", "accent2": "#0099cc",
        "bg_main": "#050a14", "bg_card": "#0a1628", "bg_card2": "#0f1e38",
        "bg_border": "#1a2d4a", "text_pri": "#e0f4ff", "text_sec": "#90bcd8",
        "text_mut": "#4a7090", "green": "#00ffcc", "orange": "#ffaa00",
        "red": "#ff4466", "blue": "#00d4ff", "icon": "🌊",
    },
    "Red": {
        "mode": "dark", "accent": "#ff3355", "accent2": "#cc1133",
        "bg_main": "#0f0508", "bg_card": "#1a0a0d", "bg_card2": "#220d12",
        "bg_border": "#3a1520", "text_pri": "#fff0f2", "text_sec": "#d8a0aa",
        "text_mut": "#8a5060", "green": "#ff6b35", "orange": "#ffaa00",
        "red": "#ff3355", "blue": "#ff7096", "icon": "🔥",
    },
}
THEME_NAMES = list(THEMES.keys())
T = dict(THEMES["Dark"])


# ─────────────────────────────────────────────
#  TEMPERATURE HELPER
# ─────────────────────────────────────────────
_temp_cache: dict = {}
_temp_lock = threading.Lock()

def _fetch_temps_thread():
    """Tourne en background pour ne pas bloquer l'UI."""
    global _temp_cache
    while True:
        result = {}
        _sys = platform.system()

        # Linux — psutil natif
        if _sys == "Linux":
            try:
                sensors = psutil.sensors_temperatures()
                if sensors:
                    for chip, entries in sensors.items():
                        for e in entries[:2]:
                            lbl = (e.label or chip)[:20]
                            result[lbl] = round(e.current, 1)
            except Exception:
                pass

        # macOS — osx-cpu-temp si installé, sinon N/A
        elif _sys == "Darwin":
            try:
                import subprocess
                out = subprocess.check_output(
                    ["osx-cpu-temp"], stderr=subprocess.DEVNULL).decode().strip()
                val = float(out.replace("°C", "").replace(",", ".").strip())
                result["CPU"] = round(val, 1)
            except Exception:
                pass

        # Windows — WMI thermal zones
        elif _sys == "Windows":
            try:
                import wmi
                w = wmi.WMI(namespace="root\\wmi")
                for zone in w.MSAcpi_ThermalZoneTemperature():
                    temp_c = round((zone.CurrentTemperature / 10) - 273.15, 1)
                    lbl = zone.InstanceName.split("\\")[-1][:16]
                    result[lbl] = temp_c
            except Exception:
                pass

        with _temp_lock:
            _temp_cache = result
        time.sleep(3)   # refresh toutes les 3s

def get_temps() -> dict:
    with _temp_lock:
        return dict(_temp_cache)


# ─────────────────────────────────────────────
#  WIDGETS
# ─────────────────────────────────────────────
class AnimatedBar(ctk.CTkFrame):
    def __init__(self, master, label="", color=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._color = color or T["accent"]
        self._current = self._target = 0.0

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(0, 3))
        self._lbl = ctk.CTkLabel(row, text=label, font=("Consolas", 11),
                                  text_color=T["text_sec"], anchor="w")
        self._lbl.pack(side="left")
        self._pct = ctk.CTkLabel(row, text="0%", font=("Consolas", 11, "bold"),
                                  text_color=self._color, anchor="e")
        self._pct.pack(side="right")

        self._track = ctk.CTkFrame(self, fg_color=T["bg_border"], corner_radius=4, height=8)
        self._track.pack(fill="x")
        self._track.pack_propagate(False)
        self._fill = ctk.CTkFrame(self._track, fg_color=self._color,
                                   corner_radius=4, height=8, width=0)
        self._fill.place(x=0, y=0, relheight=1.0, relwidth=0.0)
        self._animate()

    def set_value(self, pct: float):
        self._target = max(0.0, min(100.0, pct))
        col = T["red"] if pct >= 85 else T["orange"] if pct >= 65 else self._color
        self._fill.configure(fg_color=col)
        self._pct.configure(text=f"{pct:.1f}%", text_color=col)

    def _animate(self):
        diff = self._target - self._current
        self._current += diff * 0.18 if abs(diff) > 0.3 else diff
        self._fill.place(relwidth=self._current / 100)
        self.after(16, self._animate)


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title, icon, **kwargs):
        super().__init__(master, fg_color=T["bg_card"],
                          border_width=1, border_color=T["bg_border"],
                          corner_radius=12, **kwargs)
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(hdr, text=f"{icon}  {title}", font=("Consolas", 12, "bold"),
                     text_color=T["text_sec"]).pack(side="left")

    def body(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        return f


class HistoryGraph(ctk.CTkCanvas):
    def __init__(self, master, color=None, points=60, label="", **kwargs):
        self._color = color or T["accent"]
        self._label = label
        self._points = points
        self._data = [0.0] * points
        super().__init__(master, bg=T["bg_card2"], highlightthickness=0, **kwargs)
        self.bind("<Configure>", lambda e: self._draw())

    def push(self, value: float):
        self._data.append(max(0.0, min(100.0, value)))
        if len(self._data) > self._points:
            self._data.pop(0)
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        for pct in (25, 50, 75):
            y = h - (pct / 100) * (h - 6) - 3
            self.create_line(0, y, w, y, fill=T["bg_border"], width=1, dash=(4, 4))
            self.create_text(4, y - 6, text=f"{pct}%",
                             font=("Consolas", 8), fill=T["text_mut"], anchor="w")
        step = w / max(len(self._data) - 1, 1)
        pts = []
        for i, v in enumerate(self._data):
            pts.extend([i * step, h - (v / 100) * (h - 6) - 3])
        if len(pts) >= 4:
            self.create_polygon([0, h] + pts + [w, h], fill=self._color,
                                outline="", smooth=True, stipple="gray25")
            self.create_line(pts, fill=self._color, width=2, smooth=True)
        cur = self._data[-1] if self._data else 0
        col = T["red"] if cur >= 85 else T["orange"] if cur >= 65 else self._color
        self.create_text(w - 6, 6, text=f"{cur:.0f}%",
                         font=("Consolas", 9, "bold"), fill=col, anchor="ne")
        if self._label:
            self.create_text(6, 6, text=self._label,
                             font=("Consolas", 8), fill=T["text_mut"], anchor="nw")


class MiniGraph(ctk.CTkCanvas):
    def __init__(self, master, color=None, points=60, **kwargs):
        self._color = color or T["accent"]
        self._points = points
        self._data = [0.0] * points
        self._max = 1.0
        super().__init__(master, bg=T["bg_card2"], highlightthickness=0, **kwargs)
        self.bind("<Configure>", lambda e: self._draw())

    def push(self, value: float):
        self._data.append(value)
        if len(self._data) > self._points:
            self._data.pop(0)
        self._max = max(max(self._data), 1.0)
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2 or h < 2:
            return
        step = w / max(len(self._data) - 1, 1)
        pts = []
        for i, v in enumerate(self._data):
            pts.extend([i * step, h - (v / self._max) * (h - 4) - 2])
        if len(pts) >= 4:
            self.create_polygon([0, h] + pts + [w, h], fill=self._color,
                                outline="", smooth=True, stipple="gray25")
            self.create_line(pts, fill=self._color, width=1.5, smooth=True)


# ─────────────────────────────────────────────
#  THEME POPUP
# ─────────────────────────────────────────────
class ThemePopup(ctk.CTkToplevel):
    def __init__(self, master, current, on_select):
        super().__init__(master)
        self.title("")
        self.resizable(False, False)
        self.configure(fg_color=T["bg_card"])
        self.overrideredirect(True)
        x = master.winfo_rootx() + master.winfo_width() - 185
        y = master.winfo_rooty() + 56
        self.geometry(f"175x{len(THEME_NAMES)*52+40}+{x}+{y}")
        ctk.CTkLabel(self, text="CHOISIR UN THÈME",
                     font=("Consolas", 9, "bold"),
                     text_color=T["text_mut"]).pack(pady=(10, 4))
        for name in THEME_NAMES:
            th = THEMES[name]
            active = name == current
            ctk.CTkButton(
                self, text=f"{th['icon']}  {name}",
                font=("Consolas", 12, "bold" if active else "normal"),
                fg_color=T["bg_card2"] if active else "transparent",
                hover_color=T["bg_card2"],
                text_color=T["accent"] if active else T["text_sec"],
                border_width=1 if active else 0, border_color=T["accent"],
                corner_radius=8, height=38,
                command=lambda n=name: self._pick(n, on_select),
            ).pack(fill="x", padx=10, pady=4)
        self.after(200, lambda: self.bind("<FocusOut>", lambda e: self.destroy()))
        self.focus_force()

    def _pick(self, name, on_select):
        self.destroy()
        on_select(name)


# ─────────────────────────────────────────────
#  MINI WIDGET FLOTTANT
# ─────────────────────────────────────────────
class MiniWidget(ctk.CTkToplevel):
    """Petit widget draggable, toujours au premier plan."""
    def __init__(self, master):
        super().__init__(master)
        self.title("")
        self.geometry("220x140")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.configure(fg_color=T["bg_card"])
        self._drag_x = self._drag_y = 0

        # Drag
        self.bind("<ButtonPress-1>",   self._drag_start)
        self.bind("<B1-Motion>",       self._drag_move)

        # Bordure accent
        ctk.CTkFrame(self, fg_color=T["accent"], height=2, corner_radius=0).pack(fill="x")

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent", height=28)
        hdr.pack(fill="x", padx=8, pady=(4, 0))
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="⬡ WG", font=("Consolas", 10, "bold"),
                     text_color=T["accent"]).pack(side="left")
        ctk.CTkButton(hdr, text="✕", font=("Consolas", 10),
                      fg_color="transparent", hover_color=T["bg_card2"],
                      text_color=T["text_mut"], width=24, height=20,
                      command=self.withdraw).pack(side="right")

        # Stats
        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="both", expand=True, padx=10, pady=6)

        self._rows = {}
        items = [
            ("cpu",  "⚙️  CPU",  T["accent"]),
            ("ram",  "🧠  RAM",  T["blue"]),
            ("net",  "📡  NET",  T["green"]),
            ("temp", "🌡️  TEMP", T["orange"]),
        ]
        for key, label, color in items:
            row = ctk.CTkFrame(stats, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=label, font=("Consolas", 10),
                          text_color=T["text_mut"], width=80, anchor="w").pack(side="left")
            val = ctk.CTkLabel(row, text="—", font=("Consolas", 11, "bold"),
                                text_color=color)
            val.pack(side="left")
            self._rows[key] = val

    def update_stats(self, cpu, ram, net_rx, net_tx, temp):
        try:
            cpu_col = T["red"] if cpu >= 85 else T["orange"] if cpu >= 65 else T["accent"]
            ram_col = T["red"] if ram >= 85 else T["orange"] if ram >= 65 else T["blue"]
            self._rows["cpu"].configure(text=f"{cpu:.0f}%",  text_color=cpu_col)
            self._rows["ram"].configure(text=f"{ram:.0f}%",  text_color=ram_col)
            self._rows["net"].configure(text=f"▼{_fmt(net_rx)}/s  ▲{_fmt(net_tx)}/s",
                                         text_color=T["green"])
            if temp:
                best = max(temp.values())
                t_col = T["red"] if best >= 80 else T["orange"] if best >= 65 else T["orange"]
                self._rows["temp"].configure(text=f"{best:.0f}°C", text_color=t_col)
            else:
                self._rows["temp"].configure(text="N/A", text_color=T["text_mut"])
        except Exception:
            pass

    def _drag_start(self, e):
        self._drag_x = e.x
        self._drag_y = e.y

    def _drag_move(self, e):
        x = self.winfo_x() + e.x - self._drag_x
        y = self.winfo_y() + e.y - self._drag_y
        self.geometry(f"+{x}+{y}")


# ─────────────────────────────────────────────
#  SYSTEM TRAY HELPER
# ─────────────────────────────────────────────
def _make_tray_icon(accent_hex: str) -> "Image":
    """Crée une icône 64×64 colorée pour le system tray."""
    r = int(accent_hex[1:3], 16)
    g = int(accent_hex[3:5], 16)
    b = int(accent_hex[5:7], 16)
    img  = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=(r, g, b, 255))
    draw.text((18, 18), "WG", fill=(255, 255, 255, 255))
    return img


# ─────────────────────────────────────────────
#  GLOBAL FORMAT HELPER
# ─────────────────────────────────────────────
def _fmt(b: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────
class WGMonitor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WG Monitor")
        self.geometry("1100x820")
        self.minsize(900, 680)

        self._cfg          = load_config()
        self._current_theme= self._cfg.get("theme", "Dark")
        self._current_tab  = "dashboard"
        self._prev_net     = psutil.net_io_counters()
        self._prev_time    = time.time()
        self._net_rx       = 0.0
        self._net_tx       = 0.0
        self._refresh_job  = None
        self._proc_sort    = "cpu"
        self._mini_widget  = None
        self._tray_icon    = None
        self._tray_thread  = None

        # Thread températures
        t = threading.Thread(target=_fetch_temps_thread, daemon=True)
        t.start()

        self._apply_theme(self._current_theme, first=True)
        self._start_tray()

        # Sauvegarder position avant fermeture
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── CLOSE ─────────────────────────────────
    def _on_close(self):
        save_config({"theme": self._current_theme})
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
        self.destroy()

    # ── SYSTEM TRAY ───────────────────────────
    def _start_tray(self):
        if not TRAY_OK:
            return
        try:
            icon_img = _make_tray_icon(T["accent"])
            menu = pystray.Menu(
                pystray.MenuItem("⬡  WG Monitor", None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Afficher",  lambda: self.after(0, self.deiconify)),
                pystray.MenuItem("Mini widget",
                                 lambda: self.after(0, self._toggle_mini)),
                pystray.Menu.SEPARATOR,
                *[pystray.MenuItem(
                    f"{THEMES[n]['icon']}  {n}",
                    lambda _, nm=n: self.after(0, lambda: self._apply_theme(nm))
                  ) for n in THEME_NAMES],
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quitter", lambda: self.after(0, self._on_close)),
            )
            self._tray_icon = pystray.Icon("WGMonitor", icon_img,
                                            "WG Monitor", menu)
            self._tray_thread = threading.Thread(
                target=self._tray_icon.run, daemon=True)
            self._tray_thread.start()
        except Exception as e:
            print(f"[tray] {e}")

    def _update_tray_icon(self):
        if self._tray_icon and TRAY_OK:
            try:
                self._tray_icon.icon = _make_tray_icon(T["accent"])
            except Exception:
                pass

    # ── MINI WIDGET ───────────────────────────
    def _toggle_mini(self):
        if self._mini_widget and self._mini_widget.winfo_exists():
            if self._mini_widget.winfo_viewable():
                self._mini_widget.withdraw()
            else:
                self._mini_widget.deiconify()
        else:
            self._mini_widget = MiniWidget(self)

    # ── THEME ─────────────────────────────────
    def _apply_theme(self, name: str, first=False):
        global T
        self._current_theme = name
        T.update(THEMES[name])
        ctk.set_appearance_mode(T["mode"])
        self.configure(fg_color=T["bg_main"])
        save_config({"theme": name})
        self._update_tray_icon()

        if self._refresh_job:
            self.after_cancel(self._refresh_job)
            self._refresh_job = None

        for w in self.winfo_children():
            w.destroy()
        self._mini_widget = None
        self._build_ui()
        self._refresh()

    def _open_theme_popup(self):
        ThemePopup(self, self._current_theme, self._apply_theme)

    # ── UI BUILD ──────────────────────────────
    def _build_ui(self):
        # TOP BAR
        topbar = ctk.CTkFrame(self, fg_color=T["bg_card"], height=52,
                               corner_radius=0, border_width=0)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        ctk.CTkLabel(topbar, text="⬡  WG MONITOR",
                     font=("Consolas", 15, "bold"),
                     text_color=T["accent"]).pack(side="left", padx=20)

        # Bouton thème
        th = THEMES[self._current_theme]
        ctk.CTkButton(
            topbar, text=f"{th['icon']}  {self._current_theme}",
            font=("Consolas", 11), fg_color=T["bg_card2"],
            hover_color=T["bg_border"], text_color=T["text_sec"],
            corner_radius=8, height=32, width=140,
            command=self._open_theme_popup,
        ).pack(side="right", padx=(4, 16), pady=10)

        # Copier config
        self._copy_btn = ctk.CTkButton(
            topbar, text="📋  Config",
            font=("Consolas", 11), fg_color=T["bg_card2"],
            hover_color=T["bg_border"], text_color=T["text_sec"],
            corner_radius=8, height=32, width=110,
            command=self._copy_config,
        )
        self._copy_btn.pack(side="right", padx=4, pady=10)

        # Mini widget toggle
        ctk.CTkButton(
            topbar, text="🪟  Mini",
            font=("Consolas", 11), fg_color=T["bg_card2"],
            hover_color=T["bg_border"], text_color=T["text_sec"],
            corner_radius=8, height=32, width=90,
            command=self._toggle_mini,
        ).pack(side="right", padx=4, pady=10)

        ctk.CTkLabel(topbar, text="● LIVE",
                     font=("Consolas", 10, "bold"),
                     text_color=T["green"]).pack(side="right", padx=(0, 6))

        self._clock = ctk.CTkLabel(topbar, text="",
                                    font=("Consolas", 11), text_color=T["text_sec"])
        self._clock.pack(side="right", padx=(0, 12))

        ctk.CTkFrame(self, fg_color=T["accent"], height=2).pack(fill="x")

        # ONGLETS
        tab_bar = ctk.CTkFrame(self, fg_color=T["bg_card"], height=40,
                                corner_radius=0)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)

        self._tab_btns = {}
        for tab_id, label, icon in [("dashboard", "Dashboard", "📊"),
                                     ("processes",  "Processus",  "⚡")]:
            active = self._current_tab == tab_id
            btn = ctk.CTkButton(
                tab_bar, text=f"{icon}  {label}",
                font=("Consolas", 12, "bold" if active else "normal"),
                fg_color=T["bg_main"] if active else "transparent",
                hover_color=T["bg_card2"],
                text_color=T["accent"] if active else T["text_sec"],
                corner_radius=6, height=28, width=150, border_width=0,
                command=lambda t=tab_id: self._switch_tab(t),
            )
            btn.pack(side="left", padx=(10 if tab_id == "dashboard" else 4, 0), pady=6)
            self._tab_btns[tab_id] = btn

        # BOTTOM
        bot = ctk.CTkFrame(self, fg_color=T["bg_card"], height=28, corner_radius=0)
        bot.pack(fill="x", side="bottom")
        bot.pack_propagate(False)
        self._uptime_lbl = ctk.CTkLabel(bot, text="", font=("Consolas", 11),
                                         text_color=T["text_sec"])
        self._uptime_lbl.pack(side="left", padx=16, pady=6)

        # Tray status
        if TRAY_OK:
            tray_txt, tray_col = "● Tray actif", T["green"]
        elif platform.system() == "Darwin":
            tray_txt, tray_col = "⚠ pip install pystray pillow rumps", T["orange"]
        else:
            tray_txt, tray_col = "⚠ pip install pystray pillow", T["orange"]
        ctk.CTkLabel(bot, text=tray_txt, font=("Consolas", 9),
                      text_color=tray_col).pack(side="right", padx=16)

        # CONTENT
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

        self._dash_frame = ctk.CTkFrame(self._content, fg_color="transparent")
        self._proc_frame = ctk.CTkFrame(self._content, fg_color="transparent")

        self._build_dashboard(self._dash_frame)
        self._build_processes(self._proc_frame)

        if self._current_tab == "dashboard":
            self._dash_frame.pack(fill="both", expand=True)
        else:
            self._proc_frame.pack(fill="both", expand=True)

    def _switch_tab(self, tab_id):
        self._current_tab = tab_id
        for tid, btn in self._tab_btns.items():
            active = tid == tab_id
            btn.configure(
                font=("Consolas", 12, "bold" if active else "normal"),
                fg_color=T["bg_main"] if active else "transparent",
                text_color=T["accent"] if active else T["text_sec"],
            )
        self._dash_frame.pack_forget()
        self._proc_frame.pack_forget()
        if tab_id == "dashboard":
            self._dash_frame.pack(fill="both", expand=True)
        else:
            self._proc_frame.pack(fill="both", expand=True)

    # ── DASHBOARD ─────────────────────────────
    def _build_dashboard(self, parent):
        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=12)
        body.rowconfigure(0, weight=3)
        body.rowconfigure(1, weight=2)
        body.rowconfigure(2, weight=1)
        body.columnconfigure(0, weight=1)

        # ROW 1 : CPU + RAM
        row1 = ctk.CTkFrame(body, fg_color="transparent")
        row1.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        row1.columnconfigure(0, weight=1)
        row1.columnconfigure(1, weight=1)
        row1.rowconfigure(0, weight=1)

        # ── CPU ──
        cpu_card = StatCard(row1, "CPU", "🔲")
        cpu_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        cb = cpu_card.body()

        top = ctk.CTkFrame(cb, fg_color="transparent")
        top.pack(fill="x")
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=2)

        lc = ctk.CTkFrame(top, fg_color="transparent")
        lc.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._cpu_big = ctk.CTkLabel(lc, text="0%",
                                      font=("Consolas", 38, "bold"),
                                      text_color=T["accent"])
        self._cpu_big.pack(anchor="w")
        ctk.CTkLabel(lc, text=self._short_cpu(),
                     font=("Consolas", 11), text_color=T["text_mut"],
                     wraplength=220, justify="left").pack(anchor="w", pady=(0, 4))

        # Températures
        self._temp_lbl = ctk.CTkLabel(lc, text="🌡️  —",
                                       font=("Consolas", 11, "bold"),
                                       text_color=T["orange"])
        self._temp_lbl.pack(anchor="w", pady=(0, 6))

        self._core_bars = []
        cgrid = ctk.CTkFrame(lc, fg_color="transparent")
        cgrid.pack(fill="x")
        cgrid.columnconfigure(0, weight=1)
        cgrid.columnconfigure(1, weight=1)
        for i in range(min(psutil.cpu_count(logical=True), 16)):
            bar = AnimatedBar(cgrid, label=f"Core {i}", color=T["accent"])
            bar.grid(row=i // 2, column=i % 2, sticky="ew",
                     padx=(0, 4) if i % 2 == 0 else (4, 0), pady=2)
            self._core_bars.append(bar)
        self._cpu_freq = ctk.CTkLabel(lc, text="", font=("Consolas", 11),
                                       text_color=T["text_mut"])
        self._cpu_freq.pack(anchor="w", pady=(6, 0))

        rc = ctk.CTkFrame(top, fg_color=T["bg_card2"], corner_radius=8)
        rc.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(rc, text="Historique CPU  (60s)",
                     font=("Consolas", 11), text_color=T["text_mut"]).pack(anchor="w", padx=10, pady=(8, 4))
        self._cpu_graph = HistoryGraph(rc, color=T["accent"],
                                        points=HISTORY_POINTS, label="CPU")
        self._cpu_graph.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # ── RAM ──
        ram_card = StatCard(row1, "MEMORY", "▦")
        ram_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        rb = ram_card.body()

        top2 = ctk.CTkFrame(rb, fg_color="transparent")
        top2.pack(fill="x")
        top2.columnconfigure(0, weight=1)
        top2.columnconfigure(1, weight=2)

        lr = ctk.CTkFrame(top2, fg_color="transparent")
        lr.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._ram_big = ctk.CTkLabel(lr, text="0%",
                                      font=("Consolas", 38, "bold"),
                                      text_color=T["blue"])
        self._ram_big.pack(anchor="w")
        self._ram_detail = ctk.CTkLabel(lr, text="", font=("Consolas", 11),
                                         text_color=T["text_mut"])
        self._ram_detail.pack(anchor="w", pady=(0, 8))
        self._ram_bar  = AnimatedBar(lr, label="RAM",  color=T["blue"])
        self._ram_bar.pack(fill="x", pady=2)
        self._swap_bar = AnimatedBar(lr, label="SWAP", color=T["accent2"])
        self._swap_bar.pack(fill="x", pady=2)

        mg = ctk.CTkFrame(lr, fg_color=T["bg_card2"], corner_radius=8)
        mg.pack(fill="x", pady=(10, 0))
        self._mem_stats = {}
        for i, key in enumerate(["Available", "Cached", "Buffers"]):
            mg.columnconfigure(i, weight=1)
            fr = ctk.CTkFrame(mg, fg_color="transparent")
            fr.grid(row=0, column=i, padx=10, pady=8, sticky="nsew")
            lbl = ctk.CTkLabel(fr, text="—", font=("Consolas", 13, "bold"),
                                text_color=T["text_pri"])
            lbl.pack()
            ctk.CTkLabel(fr, text=key, font=("Consolas", 11),
                          text_color=T["text_mut"]).pack()
            self._mem_stats[key] = lbl

        rr = ctk.CTkFrame(top2, fg_color=T["bg_card2"], corner_radius=8)
        rr.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(rr, text="Historique RAM  (60s)",
                     font=("Consolas", 11), text_color=T["text_mut"]).pack(anchor="w", padx=10, pady=(8, 4))
        self._ram_graph = HistoryGraph(rr, color=T["blue"],
                                        points=HISTORY_POINTS, label="RAM")
        self._ram_graph.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # ROW 2 : DISK + NETWORK
        row2 = ctk.CTkFrame(body, fg_color="transparent")
        row2.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        row2.columnconfigure(0, weight=1)
        row2.columnconfigure(1, weight=1)
        row2.rowconfigure(0, weight=1)

        disk_card = StatCard(row2, "DISK", "💾")
        disk_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        disk_body = disk_card.body()
        self._disk_bars = {}
        for p in psutil.disk_partitions()[:4]:
            try:
                psutil.disk_usage(p.mountpoint)
                letter = p.device.strip().rstrip("\\").rstrip("/").rstrip(":").upper()
                letter = letter[-1] if letter else "?"
                if letter == "C":   lbl = "C:  —  Windows"
                elif letter == "D": lbl = "D:  —  Linux"
                else:               lbl = f"{letter}:  —  Disque externe"
                bar = AnimatedBar(disk_body, label=lbl, color=T["green"])
                bar.pack(fill="x", pady=3)
                self._disk_bars[p.mountpoint] = bar
            except Exception:
                pass
        self._disk_rw = ctk.CTkLabel(disk_body, text="R: — W: —",
                                      font=("Consolas", 11), text_color=T["text_sec"])
        self._disk_rw.pack(anchor="w", pady=(8, 0))

        net_card = StatCard(row2, "NETWORK", "📡")
        net_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        net_body = net_card.body()
        nv = ctk.CTkFrame(net_body, fg_color="transparent")
        nv.pack(fill="x", pady=(0, 6))
        nv.columnconfigure(0, weight=1)
        nv.columnconfigure(1, weight=1)
        df = ctk.CTkFrame(nv, fg_color="transparent")
        df.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(df, text="▼ DOWN", font=("Consolas", 11),
                      text_color=T["blue"]).pack(anchor="w")
        self._net_down_lbl = ctk.CTkLabel(df, text="0 B/s",
                                           font=("Consolas", 18, "bold"),
                                           text_color=T["blue"])
        self._net_down_lbl.pack(anchor="w")
        uf = ctk.CTkFrame(nv, fg_color="transparent")
        uf.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(uf, text="▲ UP", font=("Consolas", 11),
                      text_color=T["accent"]).pack(anchor="w")
        self._net_up_lbl = ctk.CTkLabel(uf, text="0 B/s",
                                         font=("Consolas", 18, "bold"),
                                         text_color=T["accent"])
        self._net_up_lbl.pack(anchor="w")
        graphs = ctk.CTkFrame(net_body, fg_color=T["bg_card2"], corner_radius=8, height=80)
        graphs.pack(fill="x", pady=(6, 0))
        graphs.pack_propagate(False)
        self._graph_down = MiniGraph(graphs, color=T["blue"])
        self._graph_down.place(relx=0, rely=0, relwidth=0.5, relheight=1)
        self._graph_up = MiniGraph(graphs, color=T["accent"])
        self._graph_up.place(relx=0.5, rely=0, relwidth=0.5, relheight=1)
        self._net_totals = ctk.CTkLabel(net_body, text="", font=("Consolas", 11),
                                         text_color=T["text_sec"])
        self._net_totals.pack(anchor="w", pady=(6, 0))

        # ROW 3 : SYSTEM
        info_card = StatCard(body, "SYSTEM", "🖥")
        info_card.grid(row=2, column=0, sticky="nsew")
        info_body = info_card.body()
        info_grid = ctk.CTkFrame(info_body, fg_color="transparent")
        info_grid.pack(fill="x")
        info = self._get_sysinfo()
        accent_cols = [T["accent"], T["blue"], T["green"], T["orange"], T["text_sec"]]
        for i, (k, v) in enumerate(info.items()):
            info_grid.columnconfigure(i, weight=1)
            fr = ctk.CTkFrame(info_grid, fg_color=T["bg_card2"], corner_radius=8)
            fr.grid(row=0, column=i, padx=3, pady=4, sticky="nsew")
            ctk.CTkLabel(fr, text=k, font=("Consolas", 11),
                          text_color=T["text_sec"]).pack(pady=(8, 2))
            ctk.CTkLabel(fr, text=v, font=("Consolas", 12, "bold"),
                          text_color=accent_cols[i],
                          wraplength=180, justify="center").pack(pady=(0, 8), padx=6)

    # ── PROCESSES ─────────────────────────────
    def _build_processes(self, parent):
        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=12)

        hdr = ctk.CTkFrame(body, fg_color=T["bg_card"], corner_radius=10,
                            border_width=1, border_color=T["bg_border"])
        hdr.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(hdr, text="⚡  TOP PROCESSUS",
                     font=("Consolas", 13, "bold"),
                     text_color=T["text_sec"]).pack(side="left", padx=16, pady=12)

        sf = ctk.CTkFrame(hdr, fg_color="transparent")
        sf.pack(side="right", padx=16, pady=8)
        ctk.CTkLabel(sf, text="Trier par :", font=("Consolas", 11),
                      text_color=T["text_mut"]).pack(side="left", padx=(0, 8))
        self._sort_cpu_btn = ctk.CTkButton(
            sf, text="⚙️ CPU", font=("Consolas", 11, "bold"),
            fg_color=T["accent"], hover_color=T["accent2"],
            text_color=T["bg_main"], corner_radius=6, height=28, width=80,
            command=lambda: self._set_proc_sort("cpu"))
        self._sort_cpu_btn.pack(side="left", padx=2)
        self._sort_ram_btn = ctk.CTkButton(
            sf, text="🧠 RAM", font=("Consolas", 11),
            fg_color=T["bg_card2"], hover_color=T["bg_border"],
            text_color=T["text_sec"], corner_radius=6, height=28, width=80,
            command=lambda: self._set_proc_sort("ram"))
        self._sort_ram_btn.pack(side="left", padx=2)

        cols = [("PID", 80), ("Processus", 300), ("CPU %", 100),
                ("RAM", 110), ("Statut", 100)]
        col_frame = ctk.CTkFrame(body, fg_color=T["bg_card2"],
                                  corner_radius=8, height=34)
        col_frame.pack(fill="x", pady=(0, 4))
        col_frame.pack_propagate(False)
        for cname, cw in cols:
            ctk.CTkLabel(col_frame, text=cname,
                         font=("Consolas", 11, "bold"),
                         text_color=T["accent"], width=cw, anchor="w").pack(
                side="left", padx=10, pady=6)

        self._proc_rows = []
        scroll = ctk.CTkScrollableFrame(body, fg_color="transparent",
                                         scrollbar_fg_color=T["bg_card2"])
        scroll.pack(fill="both", expand=True)
        for i in range(15):
            row_bg = T["bg_card"] if i % 2 == 0 else T["bg_card2"]
            row_fr = ctk.CTkFrame(scroll, fg_color=row_bg,
                                   corner_radius=6, height=38)
            row_fr.pack(fill="x", pady=2)
            row_fr.pack_propagate(False)
            cells = {}
            for cname, cw in cols:
                lbl = ctk.CTkLabel(row_fr, text="—", font=("Consolas", 11),
                                    text_color=T["text_sec"], width=cw, anchor="w")
                lbl.pack(side="left", padx=10)
                cells[cname] = lbl
            self._proc_rows.append(cells)

    def _set_proc_sort(self, mode):
        self._proc_sort = mode
        if mode == "cpu":
            self._sort_cpu_btn.configure(fg_color=T["accent"],
                                          text_color=T["bg_main"],
                                          font=("Consolas", 11, "bold"))
            self._sort_ram_btn.configure(fg_color=T["bg_card2"],
                                          text_color=T["text_sec"],
                                          font=("Consolas", 11))
        else:
            self._sort_ram_btn.configure(fg_color=T["blue"],
                                          text_color=T["bg_main"],
                                          font=("Consolas", 11, "bold"))
            self._sort_cpu_btn.configure(fg_color=T["bg_card2"],
                                          text_color=T["text_sec"],
                                          font=("Consolas", 11))

    def _update_processes(self):
        try:
            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent",
                                           "memory_info", "status"]):
                try:
                    info = p.info
                    ram  = info["memory_info"].rss if info["memory_info"] else 0
                    procs.append({"pid": info["pid"], "name": info["name"] or "—",
                                  "cpu": info["cpu_percent"] or 0.0,
                                  "ram": ram, "status": info["status"] or "—"})
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            procs.sort(key=lambda x: x["cpu" if self._proc_sort == "cpu" else "ram"],
                       reverse=True)
            for i, cells in enumerate(self._proc_rows):
                if i < len(procs):
                    p = procs[i]
                    cpu_col = (T["red"] if p["cpu"] >= 50
                               else T["orange"] if p["cpu"] >= 20
                               else T["text_sec"])
                    cells["PID"].configure(text=str(p["pid"]), text_color=T["text_mut"])
                    cells["Processus"].configure(text=p["name"][:38], text_color=T["text_pri"])
                    cells["CPU %"].configure(text=f"{p['cpu']:.1f}%", text_color=cpu_col)
                    cells["RAM"].configure(text=_fmt(p["ram"]), text_color=T["blue"])
                    cells["Statut"].configure(
                        text=p["status"],
                        text_color=T["green"] if p["status"] == "running" else T["text_mut"])
                else:
                    for lbl in cells.values():
                        lbl.configure(text="—", text_color=T["text_mut"])
        except Exception as e:
            print(f"[processes] {e}")

    # ── REFRESH ───────────────────────────────
    def _refresh(self):
        try:
            self._update_cpu()
            self._update_ram()
            self._update_disk()
            self._update_network()
            self._update_temps()
            self._update_clock()
            if self._current_tab == "processes":
                self._update_processes()
            if self._mini_widget and self._mini_widget.winfo_exists():
                self._mini_widget.update_stats(
                    psutil.cpu_percent(interval=None),
                    psutil.virtual_memory().percent,
                    self._net_rx, self._net_tx,
                    get_temps())
        except Exception as e:
            print(f"[refresh] {e}")
        self._refresh_job = self.after(UPDATE_INTERVAL, self._refresh)

    def _update_cpu(self):
        overall  = psutil.cpu_percent(interval=None)
        per_core = psutil.cpu_percent(interval=None, percpu=True)
        freq     = psutil.cpu_freq()
        self._cpu_big.configure(text=f"{overall:.0f}%",
                                 text_color=self._pct_color(overall, T["accent"]))
        for i, bar in enumerate(self._core_bars):
            if i < len(per_core):
                bar.set_value(per_core[i])
        if freq:
            self._cpu_freq.configure(
                text=f"Fréquence: {freq.current:.0f} MHz  •  Max: {freq.max:.0f} MHz")
        self._cpu_graph.push(overall)

    def _update_ram(self):
        mem  = psutil.virtual_memory()
        swap = psutil.swap_memory()
        self._ram_big.configure(text=f"{mem.percent:.0f}%",
                                 text_color=self._pct_color(mem.percent, T["blue"]))
        self._ram_detail.configure(
            text=f"{_fmt(mem.used)} / {_fmt(mem.total)}  ({_fmt(mem.available)} libre)")
        self._ram_bar.set_value(mem.percent)
        self._swap_bar.set_value(swap.percent)
        self._mem_stats["Available"].configure(text=_fmt(mem.available))
        self._mem_stats["Cached"].configure(text=_fmt(getattr(mem, "cached", 0) or 0))
        self._mem_stats["Buffers"].configure(text=_fmt(getattr(mem, "buffers", 0) or 0))
        self._ram_graph.push(mem.percent)

    def _update_disk(self):
        for mp, bar in self._disk_bars.items():
            try:
                bar.set_value(psutil.disk_usage(mp).percent)
            except Exception:
                pass
        try:
            dio = psutil.disk_io_counters()
            self._disk_rw.configure(
                text=f"Read: {_fmt(dio.read_bytes)}  •  Write: {_fmt(dio.write_bytes)}")
        except Exception:
            pass

    def _update_network(self):
        now = time.time()
        net = psutil.net_io_counters()
        dt  = now - self._prev_time
        if dt <= 0:
            return
        self._net_rx = (net.bytes_recv - self._prev_net.bytes_recv) / dt
        self._net_tx = (net.bytes_sent - self._prev_net.bytes_sent) / dt
        self._prev_net  = net
        self._prev_time = now
        self._net_down_lbl.configure(text=f"{_fmt(self._net_rx)}/s")
        self._net_up_lbl.configure(text=f"{_fmt(self._net_tx)}/s")
        self._graph_down.push(self._net_rx)
        self._graph_up.push(self._net_tx)
        self._net_totals.configure(
            text=f"Total ▼ {_fmt(net.bytes_recv)}  ▲ {_fmt(net.bytes_sent)}")

    def _update_temps(self):
        temps = get_temps()
        if temps:
            vals = list(temps.values())
            cpu_temp = max(vals)
            col = T["red"] if cpu_temp >= 80 else T["orange"] if cpu_temp >= 65 else T["green"]
            entries = "  ".join(f"{k}: {v}°C" for k, v in list(temps.items())[:3])
            self._temp_lbl.configure(text=f"🌡️  {entries}", text_color=col)
        else:
            self._temp_lbl.configure(text="🌡️  N/A  (wmi requis sur Windows)",
                                      text_color=T["text_mut"])

    def _update_clock(self):
        self._clock.configure(text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        up = time.time() - psutil.boot_time()
        h, r = divmod(int(up), 3600)
        m, s = divmod(r, 60)
        self._uptime_lbl.configure(text=f"Uptime: {h}h {m:02d}m {s:02d}s")

    # ── COPY CONFIG ───────────────────────────
    def _copy_config(self):
        try:
            uname   = platform.uname()
            mem     = psutil.virtual_memory()
            swap    = psutil.swap_memory()
            freq    = psutil.cpu_freq()
            cores_p = psutil.cpu_count(logical=False)
            cores_l = psutil.cpu_count(logical=True)
            os_name = uname.system + " " + uname.release
            if uname.system == "Windows":
                try:
                    import winreg
                    key   = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                           r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                    build = int(winreg.QueryValueEx(key, "CurrentBuildNumber")[0])
                    ed    = winreg.QueryValueEx(key, "ProductName")[0]
                    winreg.CloseKey(key)
                    if build >= 22000:
                        ed = ed.replace("Windows 10", "Windows 11")
                    os_name = f"{ed} (build {build})"
                except Exception:
                    pass
            disk_lines = []
            for p in psutil.disk_partitions()[:4]:
                try:
                    u      = psutil.disk_usage(p.mountpoint)
                    letter = p.device.strip().rstrip("\\").rstrip("/").rstrip(":").upper()
                    letter = (letter[-1] if letter else "?") + ":"
                    disk_lines.append(
                        f"  {letter}  {_fmt(u.used)} / {_fmt(u.total)} ({u.percent:.1f}%)")
                except Exception:
                    pass
            temps = get_temps()
            temp_str = "  ".join(f"{k}: {v}°C" for k, v in list(temps.items())[:3]) if temps else "N/A"
            net = psutil.net_io_counters()
            lines = [
                "╔══════════════════════════════════════╗",
                "║           WG Monitor — Config         ║",
                "╚══════════════════════════════════════╝",
                "",
                f"🖥  OS       : {os_name}",
                f"⚙️  CPU      : {self._short_cpu()}",
                f"   Cores    : {cores_p} physiques / {cores_l} logiques",
            ]
            if freq:
                lines.append(f"   Fréq.    : {freq.current:.0f} MHz (max {freq.max:.0f} MHz)")
            lines += [
                f"🌡️  Temp     : {temp_str}",
                f"🎮  GPU      : {self._get_gpu()}",
                "",
                f"🧠  RAM      : {_fmt(mem.total)} — {_fmt(mem.used)} utilisé ({mem.percent:.1f}%)",
                f"   SWAP     : {_fmt(swap.total)} — {_fmt(swap.used)} utilisé ({swap.percent:.1f}%)",
                "", "💾  Disques  :", *disk_lines, "",
                f"📡  Réseau   : ▼ {_fmt(net.bytes_recv)} reçus  ▲ {_fmt(net.bytes_sent)} envoyés",
                "",
                f"🐍  Python   : {platform.python_version()}",
                f"📅  Date     : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            ]
            self.clipboard_clear()
            self.clipboard_append("\n".join(lines))
            self._copy_btn.configure(text="✅  Copié !", text_color=T["green"])
            self.after(2000, lambda: self._copy_btn.configure(
                text="📋  Config", text_color=T["text_sec"]))
        except Exception as e:
            self._copy_btn.configure(text="❌  Erreur", text_color=T["red"])
            self.after(2000, lambda: self._copy_btn.configure(
                text="📋  Config", text_color=T["text_sec"]))
            print(f"[copy_config] {e}")

    # ── HELPERS ───────────────────────────────
    @staticmethod
    def _pct_color(pct, base):
        if pct >= 85: return T["red"]
        if pct >= 65: return T["orange"]
        return base

    @staticmethod
    def _short_cpu():
        import subprocess
        _sys = platform.system()
        try:
            if _sys == "Windows":
                out = subprocess.check_output(
                    ["powershell", "-NoProfile", "-Command",
                     "(Get-CimInstance Win32_Processor).Name"],
                    shell=False, stderr=subprocess.DEVNULL).decode().strip()
                return out[:52] if out else platform.processor()[:52]
            elif _sys == "Darwin":
                out = subprocess.check_output(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    stderr=subprocess.DEVNULL).decode().strip()
                return out[:52] if out else platform.processor()[:52]
            else:
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "model name" in line:
                            return line.split(":")[1].strip()[:52]
        except Exception:
            pass
        return platform.processor()[:52] or "Unknown CPU"

    @staticmethod
    def _get_gpu():
        import subprocess
        _sys = platform.system()
        try:
            if _sys == "Windows":
                out = subprocess.check_output(
                    ["powershell", "-NoProfile", "-Command",
                     "(Get-CimInstance Win32_VideoController | Where-Object {$_.Name -notlike '*Basic*' -and $_.Name -notlike '*Remote*'} | Select-Object -First 1).Name"],
                    shell=False, stderr=subprocess.DEVNULL).decode().strip()
                return out[:40] if out else "Unknown GPU"
            elif _sys == "Darwin":
                out = subprocess.check_output(
                    ["system_profiler", "SPDisplaysDataType"],
                    stderr=subprocess.DEVNULL).decode()
                for line in out.splitlines():
                    line = line.strip()
                    if "Chipset Model" in line or "Graphics" in line:
                        return line.split(":")[-1].strip()[:40]
            else:
                # Linux : lspci
                out = subprocess.check_output(
                    ["lspci"], stderr=subprocess.DEVNULL).decode()
                for line in out.splitlines():
                    if "VGA" in line or "3D" in line:
                        return line.split(":")[-1].strip()[:40]
        except Exception:
            pass
        return "Unknown GPU"

    @staticmethod
    def _get_sysinfo():
        uname   = platform.uname()
        _sys = uname.system
        os_name = _sys + " " + uname.release
        if _sys == "Windows":
            try:
                import winreg
                key     = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                         r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                build   = int(winreg.QueryValueEx(key, "CurrentBuildNumber")[0])
                edition = winreg.QueryValueEx(key, "ProductName")[0]
                winreg.CloseKey(key)
                if build >= 22000:
                    edition = edition.replace("Windows 10", "Windows 11")
                os_name = edition
            except Exception:
                pass
        elif _sys == "Darwin":
            try:
                import subprocess
                ver = subprocess.check_output(
                    ["sw_vers", "-productVersion"],
                    stderr=subprocess.DEVNULL).decode().strip()
                name = subprocess.check_output(
                    ["sw_vers", "-productName"],
                    stderr=subprocess.DEVNULL).decode().strip()
                os_name = f"{name} {ver}"
            except Exception:
                mac_ver = platform.mac_ver()[0]
                os_name = f"macOS {mac_ver}" if mac_ver else os_name
        cpu_brand = "Unknown CPU"
        try:
            if platform.system() == "Windows":
                import subprocess
                out = subprocess.check_output(
                    ["powershell", "-NoProfile", "-Command",
                     "(Get-CimInstance Win32_Processor).Name"],
                    shell=False, stderr=subprocess.DEVNULL).decode().strip()
                cpu_brand = out[:38] if out else platform.processor()[:38]
            else:
                cpu_brand = platform.processor()[:38] or "Unknown CPU"
        except Exception:
            cpu_brand = platform.processor()[:38] or "Unknown CPU"
        return {
            "OS":     os_name,
            "CPU":    cpu_brand,
            "GPU":    WGMonitor._get_gpu(),
            "Cores":  f"{psutil.cpu_count(logical=False)}P / {psutil.cpu_count(logical=True)}L",
            "Python": platform.python_version(),
        }


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = WGMonitor()
    app.mainloop()