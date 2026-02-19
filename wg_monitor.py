"""
WG Monitor — System Resource Monitor
Theme Manager: Dark | Light | Midnight
"""

import customtkinter as ctk
import psutil
import platform
import time
from datetime import datetime

UPDATE_INTERVAL = 1000  # ms

# ─────────────────────────────────────────────
#  THEMES
# ─────────────────────────────────────────────
THEMES = {
    "Dark": {
        "mode":      "dark",
        "accent":    "#b76eff",
        "accent2":   "#7c3aed",
        "bg_main":   "#0d0d0f",
        "bg_card":   "#141418",
        "bg_card2":  "#1a1a20",
        "bg_border": "#2a2a35",
        "text_pri":  "#ffffff",
        "text_sec":  "#c8c3d8",
        "text_mut":  "#8a85a0",
        "green":     "#3dff9a",
        "orange":    "#ff9d3d",
        "red":       "#ff4d6a",
        "blue":      "#3dabff",
        "icon":      "🌙",
    },
    "Light": {
        "mode":      "light",
        "accent":    "#8b3dff",
        "accent2":   "#6920d4",
        "bg_main":   "#f0f0f5",
        "bg_card":   "#ffffff",
        "bg_card2":  "#eaeaf2",
        "bg_border": "#d0cfe8",
        "text_pri":  "#0d0d1a",
        "text_sec":  "#3d3860",
        "text_mut":  "#7a76a0",
        "green":     "#00b86b",
        "orange":    "#e07000",
        "red":       "#d63050",
        "blue":      "#1a7fe0",
        "icon":      "☀️",
    },
    "Midnight": {
        "mode":      "dark",
        "accent":    "#00d4ff",
        "accent2":   "#0099cc",
        "bg_main":   "#050a14",
        "bg_card":   "#0a1628",
        "bg_card2":  "#0f1e38",
        "bg_border": "#1a2d4a",
        "text_pri":  "#e0f4ff",
        "text_sec":  "#90bcd8",
        "text_mut":  "#4a7090",
        "green":     "#00ffcc",
        "orange":    "#ffaa00",
        "red":       "#ff4466",
        "blue":      "#00d4ff",
        "icon":      "🌊",
    },
    "Red": {
        "mode":      "dark",
        "accent":    "#ff3355",
        "accent2":   "#cc1133",
        "bg_main":   "#0f0508",
        "bg_card":   "#1a0a0d",
        "bg_card2":  "#220d12",
        "bg_border": "#3a1520",
        "text_pri":  "#fff0f2",
        "text_sec":  "#d8a0aa",
        "text_mut":  "#8a5060",
        "green":     "#ff6b35",
        "orange":    "#ffaa00",
        "red":       "#ff3355",
        "blue":      "#ff7096",
        "icon":      "🔥",
    },
}

THEME_NAMES = list(THEMES.keys())

# Thème actif (mutable)
T = dict(THEMES["Dark"])


# ─────────────────────────────────────────────
#  ANIMATED BAR WIDGET
# ─────────────────────────────────────────────
class AnimatedBar(ctk.CTkFrame):
    def __init__(self, master, label="", color=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._color   = color or T["accent"]
        self._current = 0.0
        self._target  = 0.0

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(0, 3))
        self._label_w = ctk.CTkLabel(row, text=label, font=("Consolas", 11),
                                      text_color=T["text_sec"], anchor="w")
        self._label_w.pack(side="left")
        self._pct_w = ctk.CTkLabel(row, text="0%", font=("Consolas", 11, "bold"),
                                    text_color=self._color, anchor="e")
        self._pct_w.pack(side="right")

        self._track = ctk.CTkFrame(self, fg_color=T["bg_border"],
                                    corner_radius=4, height=8)
        self._track.pack(fill="x")
        self._track.pack_propagate(False)

        self._fill = ctk.CTkFrame(self._track, fg_color=self._color,
                                   corner_radius=4, height=8, width=0)
        self._fill.place(x=0, y=0, relheight=1.0, relwidth=0.0)

        self._animate()

    def set_value(self, pct: float):
        self._target = max(0.0, min(100.0, pct))
        if pct >= 85:
            col = T["red"]
        elif pct >= 65:
            col = T["orange"]
        else:
            col = self._color
        self._fill.configure(fg_color=col)
        self._pct_w.configure(text=f"{pct:.1f}%", text_color=col)

    def _animate(self):
        diff = self._target - self._current
        if abs(diff) > 0.3:
            self._current += diff * 0.18
        else:
            self._current = self._target
        self._fill.place(relwidth=self._current / 100)
        self.after(16, self._animate)


# ─────────────────────────────────────────────
#  STAT CARD
# ─────────────────────────────────────────────
class StatCard(ctk.CTkFrame):
    def __init__(self, master, title, icon, **kwargs):
        super().__init__(master, fg_color=T["bg_card"],
                          border_width=1, border_color=T["bg_border"],
                          corner_radius=12, **kwargs)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(hdr, text=icon + "  " + title,
                     font=("Consolas", 12, "bold"),
                     text_color=T["text_sec"]).pack(side="left")

    def body(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        return f


# ─────────────────────────────────────────────
#  MINI GRAPH
# ─────────────────────────────────────────────
class MiniGraph(ctk.CTkCanvas):
    def __init__(self, master, color=None, points=40, **kwargs):
        self._color = color or T["accent"]
        super().__init__(master, bg=T["bg_card2"], highlightthickness=0, **kwargs)
        self._points = points
        self._data   = [0.0] * points
        self._max    = 1.0
        self.bind("<Configure>", lambda e: self._draw())

    def push(self, value: float):
        self._data.append(value)
        if len(self._data) > self._points:
            self._data.pop(0)
        self._max = max(max(self._data), 1.0)
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 2:
            return
        step = w / max(len(self._data) - 1, 1)
        pts = []
        for i, v in enumerate(self._data):
            pts.extend([i * step, h - (v / self._max) * (h - 4) - 2])
        if len(pts) >= 4:
            fill_pts = [0, h] + pts + [w, h]
            self.create_polygon(fill_pts, fill=self._color,
                                outline="", smooth=True, stipple="gray25")
            self.create_line(pts, fill=self._color, width=1.5, smooth=True)


# ─────────────────────────────────────────────
#  THEME SELECTOR POPUP
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
        popup_h = len(THEME_NAMES) * 52 + 40
        self.geometry(f"175x{popup_h}+{x}+{y}")

        ctk.CTkLabel(self, text="CHOISIR UN THÈME",
                     font=("Consolas", 9, "bold"),
                     text_color=T["text_mut"]).pack(pady=(10, 4))

        for name in THEME_NAMES:
            th = THEMES[name]
            is_active = (name == current)
            btn = ctk.CTkButton(
                self,
                text=f"{th['icon']}  {name}",
                font=("Consolas", 12, "bold" if is_active else "normal"),
                fg_color=T["bg_card2"] if is_active else "transparent",
                hover_color=T["bg_card2"],
                text_color=T["accent"] if is_active else T["text_sec"],
                border_width=1 if is_active else 0,
                border_color=T["accent"],
                corner_radius=8,
                height=38,
                command=lambda n=name: self._pick(n, on_select),
            )
            btn.pack(fill="x", padx=10, pady=4)

        # Délai pour laisser le clic s'enregistrer avant de fermer
        self.after(200, lambda: self.bind("<FocusOut>", lambda e: self.destroy()))
        self.focus_force()

    def _pick(self, name, on_select):
        self.destroy()
        on_select(name)


# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────
class WGMonitor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WG Monitor")
        self.geometry("1100x780")
        self.minsize(900, 640)

        self._current_theme = "Dark"
        self._prev_net  = psutil.net_io_counters()
        self._prev_time = time.time()
        self._refresh_job = None   # pour annuler la boucle précédente

        self._apply_theme("Dark", first=True)

    # ── THEME ────────────────────────────────
    def _apply_theme(self, name: str, first=False):
        global T
        self._current_theme = name
        T.update(THEMES[name])
        ctk.set_appearance_mode(T["mode"])
        self.configure(fg_color=T["bg_main"])

        # Annuler l'ancienne boucle refresh
        if self._refresh_job is not None:
            self.after_cancel(self._refresh_job)
            self._refresh_job = None

        for w in self.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh()

    def _copy_config(self):
        """Génère un résumé système et le copie dans le presse-papier."""
        try:
            uname   = platform.uname()
            cpu     = self._short_cpu()
            mem     = psutil.virtual_memory()
            swap    = psutil.swap_memory()
            freq    = psutil.cpu_freq()
            cores_p = psutil.cpu_count(logical=False)
            cores_l = psutil.cpu_count(logical=True)

            # OS avec détection Win11
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

            # Disques
            disk_lines = []
            for p in psutil.disk_partitions()[:4]:
                try:
                    u      = psutil.disk_usage(p.mountpoint)
                    letter = p.device.strip().rstrip("\\").rstrip("/").rstrip(":").upper()
                    letter = (letter[-1] if letter else "?") + ":"
                    disk_lines.append(
                        f"  {letter}  {self._fmt(u.used)} / {self._fmt(u.total)} "
                        f"({u.percent:.1f}%)"
                    )
                except Exception:
                    pass

            # Réseau
            net = psutil.net_io_counters()

            lines = [
                "╔══════════════════════════════════════╗",
                "║           WG Monitor — Config         ║",
                "╚══════════════════════════════════════╝",
                "",
                f"🖥  OS       : {os_name}",
                f"⚙️  CPU      : {cpu}",
                f"   Cores    : {cores_p} physiques / {cores_l} logiques",
            ]
            if freq:
                lines.append(f"   Fréq.    : {freq.current:.0f} MHz (max {freq.max:.0f} MHz)")
            lines += [
                "",
                f"🧠  RAM      : {self._fmt(mem.total)} total — {self._fmt(mem.used)} utilisé ({mem.percent:.1f}%)",
                f"   SWAP     : {self._fmt(swap.total)} total — {self._fmt(swap.used)} utilisé ({swap.percent:.1f}%)",
                "",
                "💾  Disques  :",
                *disk_lines,
                "",
                f"📡  Réseau   : ▼ {self._fmt(net.bytes_recv)} reçus — ▲ {self._fmt(net.bytes_sent)} envoyés",
                "",
                f"🐍  Python   : {platform.python_version()}",
                f"📅  Date     : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            ]

            text = "\n".join(lines)
            self.clipboard_clear()
            self.clipboard_append(text)

            # Feedback visuel
            self._copy_btn.configure(text="✅  Copié !", text_color=T["green"])
            self.after(2000, lambda: self._copy_btn.configure(
                text="📋  Copier config", text_color=T["text_sec"]))

        except Exception as e:
            self._copy_btn.configure(text="❌  Erreur", text_color=T["red"])
            self.after(2000, lambda: self._copy_btn.configure(
                text="📋  Copier config", text_color=T["text_sec"]))
            print(f"[copy_config] {e}")

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

        th = THEMES[self._current_theme]
        ctk.CTkButton(
            topbar,
            text=f"{th['icon']}  {self._current_theme}",
            font=("Consolas", 11),
            fg_color=T["bg_card2"],
            hover_color=T["bg_border"],
            text_color=T["text_sec"],
            corner_radius=8,
            height=32,
            width=140,
            command=self._open_theme_popup,
        ).pack(side="right", padx=(6, 16), pady=10)

        self._copy_btn = ctk.CTkButton(
            topbar,
            text="📋  Copier config",
            font=("Consolas", 11),
            fg_color=T["bg_card2"],
            hover_color=T["bg_border"],
            text_color=T["text_sec"],
            corner_radius=8,
            height=32,
            width=150,
            command=self._copy_config,
        )
        self._copy_btn.pack(side="right", padx=(0, 4), pady=10)

        ctk.CTkLabel(topbar, text="● LIVE",
                     font=("Consolas", 10, "bold"),
                     text_color=T["green"]).pack(side="right", padx=(0, 6))

        self._clock = ctk.CTkLabel(topbar, text="",
                                    font=("Consolas", 11),
                                    text_color=T["text_sec"])
        self._clock.pack(side="right", padx=(0, 12))

        # Séparateur
        ctk.CTkFrame(self, fg_color=T["accent"], height=2).pack(fill="x")

        # BOTTOM BAR
        bot = ctk.CTkFrame(self, fg_color=T["bg_card"], height=28, corner_radius=0)
        bot.pack(fill="x", side="bottom")
        bot.pack_propagate(False)
        self._uptime_lbl = ctk.CTkLabel(bot, text="",
                                         font=("Consolas", 9),
                                         text_color=T["text_sec"])
        self._uptime_lbl.pack(side="left", padx=16, pady=6)
        ctk.CTkLabel(bot, text="WG Monitor v1.0  •  Python + customtkinter",
                      font=("Consolas", 9),
                      text_color=T["text_mut"]).pack(side="right", padx=16)

        # BODY
        body = ctk.CTkFrame(self, fg_color="transparent")
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

        # CPU
        cpu_card = StatCard(row1, "CPU", "🔲")
        cpu_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        cpu_body = cpu_card.body()

        self._cpu_big = ctk.CTkLabel(cpu_body, text="0%",
                                      font=("Consolas", 38, "bold"),
                                      text_color=T["accent"])
        self._cpu_big.pack(anchor="w")

        ctk.CTkLabel(cpu_body, text=self._short_cpu(),
                     font=("Consolas", 9), text_color=T["text_mut"],
                     wraplength=300, justify="left").pack(anchor="w", pady=(0, 8))

        cores = psutil.cpu_count(logical=True)
        self._core_bars = []
        cgrid = ctk.CTkFrame(cpu_body, fg_color="transparent")
        cgrid.pack(fill="x")
        cgrid.columnconfigure(0, weight=1)
        cgrid.columnconfigure(1, weight=1)
        for i in range(min(cores, 16)):
            bar = AnimatedBar(cgrid, label=f"Core {i}", color=T["accent"])
            bar.grid(row=i // 2, column=i % 2, sticky="ew",
                     padx=(0, 6) if i % 2 == 0 else (6, 0), pady=2)
            self._core_bars.append(bar)

        self._cpu_freq = ctk.CTkLabel(cpu_body, text="",
                                       font=("Consolas", 9),
                                       text_color=T["text_mut"])
        self._cpu_freq.pack(anchor="w", pady=(8, 0))

        # RAM
        ram_card = StatCard(row1, "MEMORY", "▦")
        ram_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ram_body = ram_card.body()

        self._ram_big = ctk.CTkLabel(ram_body, text="0%",
                                      font=("Consolas", 38, "bold"),
                                      text_color=T["blue"])
        self._ram_big.pack(anchor="w")

        self._ram_detail = ctk.CTkLabel(ram_body, text="",
                                         font=("Consolas", 9),
                                         text_color=T["text_mut"])
        self._ram_detail.pack(anchor="w", pady=(0, 8))

        self._ram_bar  = AnimatedBar(ram_body, label="RAM",  color=T["blue"])
        self._ram_bar.pack(fill="x", pady=2)
        self._swap_bar = AnimatedBar(ram_body, label="SWAP", color=T["accent2"])
        self._swap_bar.pack(fill="x", pady=2)

        mem_grid = ctk.CTkFrame(ram_body, fg_color=T["bg_card2"], corner_radius=8)
        mem_grid.pack(fill="x", pady=(10, 0))
        self._mem_stats = {}
        for i, key in enumerate(["Available", "Cached", "Buffers"]):
            mem_grid.columnconfigure(i, weight=1)
            fr = ctk.CTkFrame(mem_grid, fg_color="transparent")
            fr.grid(row=0, column=i, padx=10, pady=8, sticky="nsew")
            lbl = ctk.CTkLabel(fr, text="—", font=("Consolas", 13, "bold"),
                                text_color=T["text_pri"])
            lbl.pack()
            ctk.CTkLabel(fr, text=key, font=("Consolas", 8),
                          text_color=T["text_mut"]).pack()
            self._mem_stats[key] = lbl

        # ROW 2 : DISK + NETWORK
        row2 = ctk.CTkFrame(body, fg_color="transparent")
        row2.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        row2.columnconfigure(0, weight=1)
        row2.columnconfigure(1, weight=1)
        row2.rowconfigure(0, weight=1)

        # DISK
        disk_card = StatCard(row2, "DISK", "💾")
        disk_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        disk_body = disk_card.body()

        self._disk_bars = {}
        for p in psutil.disk_partitions()[:4]:
            try:
                psutil.disk_usage(p.mountpoint)
                letter = p.device.strip().rstrip("\\").rstrip("/").rstrip(":").upper()
                letter = letter[-1] if letter else "?"
                if letter == "C":
                    label = "C:  —  Windows"
                elif letter == "D":
                    label = "D:  —  Linux"
                else:
                    label = f"{letter}:  —  Disque externe"
                bar = AnimatedBar(disk_body, label=label, color=T["green"])
                bar.pack(fill="x", pady=3)
                self._disk_bars[p.mountpoint] = bar
            except Exception:
                pass

        self._disk_rw = ctk.CTkLabel(disk_body, text="R: — W: —",
                                      font=("Consolas", 10),
                                      text_color=T["text_sec"])
        self._disk_rw.pack(anchor="w", pady=(8, 0))

        # NETWORK
        net_card = StatCard(row2, "NETWORK", "📡")
        net_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        net_body = net_card.body()

        net_vals = ctk.CTkFrame(net_body, fg_color="transparent")
        net_vals.pack(fill="x", pady=(0, 6))
        net_vals.columnconfigure(0, weight=1)
        net_vals.columnconfigure(1, weight=1)

        down_f = ctk.CTkFrame(net_vals, fg_color="transparent")
        down_f.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(down_f, text="▼ DOWN", font=("Consolas", 8),
                      text_color=T["blue"]).pack(anchor="w")
        self._net_down_lbl = ctk.CTkLabel(down_f, text="0 B/s",
                                           font=("Consolas", 18, "bold"),
                                           text_color=T["blue"])
        self._net_down_lbl.pack(anchor="w")

        up_f = ctk.CTkFrame(net_vals, fg_color="transparent")
        up_f.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(up_f, text="▲ UP", font=("Consolas", 8),
                      text_color=T["accent"]).pack(anchor="w")
        self._net_up_lbl = ctk.CTkLabel(up_f, text="0 B/s",
                                         font=("Consolas", 18, "bold"),
                                         text_color=T["accent"])
        self._net_up_lbl.pack(anchor="w")

        graphs = ctk.CTkFrame(net_body, fg_color=T["bg_card2"],
                               corner_radius=8, height=70)
        graphs.pack(fill="x", pady=(6, 0))
        graphs.pack_propagate(False)
        self._graph_down = MiniGraph(graphs, color=T["blue"])
        self._graph_down.place(relx=0, rely=0, relwidth=0.5, relheight=1)
        self._graph_up = MiniGraph(graphs, color=T["accent"])
        self._graph_up.place(relx=0.5, rely=0, relwidth=0.5, relheight=1)

        self._net_totals = ctk.CTkLabel(net_body, text="",
                                         font=("Consolas", 10),
                                         text_color=T["text_sec"])
        self._net_totals.pack(anchor="w", pady=(6, 0))

        # ROW 3 : SYSTEM
        info_card = StatCard(body, "SYSTEM", "🖥")
        info_card.grid(row=2, column=0, sticky="nsew")
        info_body = info_card.body()

        info_grid = ctk.CTkFrame(info_body, fg_color="transparent")
        info_grid.pack(fill="x")
        info = self._get_sysinfo()
        accent_cols = [T["accent"], T["blue"], T["green"], T["orange"]]
        for i, (k, v) in enumerate(info.items()):
            info_grid.columnconfigure(i, weight=1)
            fr = ctk.CTkFrame(info_grid, fg_color=T["bg_card2"], corner_radius=8)
            fr.grid(row=0, column=i, padx=3, pady=4, sticky="nsew")
            ctk.CTkLabel(fr, text=k, font=("Consolas", 9),
                          text_color=T["text_sec"]).pack(pady=(8, 2))
            ctk.CTkLabel(fr, text=v, font=("Consolas", 11, "bold"),
                          text_color=accent_cols[i],
                          wraplength=160, justify="center").pack(pady=(0, 8), padx=6)

    # ── REFRESH ───────────────────────────────
    def _refresh(self):
        try:
            self._update_cpu()
            self._update_ram()
            self._update_disk()
            self._update_network()
            self._update_clock()
        except Exception as e:
            print(f"[WGMonitor] Refresh error: {e}")
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

    def _update_ram(self):
        mem  = psutil.virtual_memory()
        swap = psutil.swap_memory()
        self._ram_big.configure(text=f"{mem.percent:.0f}%",
                                 text_color=self._pct_color(mem.percent, T["blue"]))
        self._ram_detail.configure(
            text=f"{self._fmt(mem.used)} / {self._fmt(mem.total)}  "
                 f"({self._fmt(mem.available)} libre)")
        self._ram_bar.set_value(mem.percent)
        self._swap_bar.set_value(swap.percent)
        self._mem_stats["Available"].configure(text=self._fmt(mem.available))
        self._mem_stats["Cached"].configure(
            text=self._fmt(getattr(mem, "cached", 0) or 0))
        self._mem_stats["Buffers"].configure(
            text=self._fmt(getattr(mem, "buffers", 0) or 0))

    def _update_disk(self):
        for mp, bar in self._disk_bars.items():
            try:
                bar.set_value(psutil.disk_usage(mp).percent)
            except Exception:
                pass
        try:
            dio = psutil.disk_io_counters()
            self._disk_rw.configure(
                text=f"Read: {self._fmt(dio.read_bytes)}  •  Write: {self._fmt(dio.write_bytes)}")
        except Exception:
            pass

    def _update_network(self):
        now = time.time()
        net = psutil.net_io_counters()
        dt  = now - self._prev_time
        if dt <= 0:
            return
        rx = (net.bytes_recv - self._prev_net.bytes_recv) / dt
        tx = (net.bytes_sent - self._prev_net.bytes_sent) / dt
        self._prev_net  = net
        self._prev_time = now
        self._net_down_lbl.configure(text=f"{self._fmt(rx)}/s")
        self._net_up_lbl.configure(text=f"{self._fmt(tx)}/s")
        self._graph_down.push(rx)
        self._graph_up.push(tx)
        self._net_totals.configure(
            text=f"Total ▼ {self._fmt(net.bytes_recv)}  ▲ {self._fmt(net.bytes_sent)}")

    def _update_clock(self):
        self._clock.configure(text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        up = time.time() - psutil.boot_time()
        h, r = divmod(int(up), 3600)
        m, s = divmod(r, 60)
        self._uptime_lbl.configure(text=f"Uptime: {h}h {m:02d}m {s:02d}s")

    # ── HELPERS ───────────────────────────────
    @staticmethod
    def _fmt(b: float) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} PB"

    @staticmethod
    def _pct_color(pct, base):
        if pct >= 85: return T["red"]
        if pct >= 65: return T["orange"]
        return base

    @staticmethod
    def _short_cpu():
        try:
            if platform.system() == "Windows":
                import subprocess
                out = subprocess.check_output(
                    ["powershell", "-NoProfile", "-Command",
                     "(Get-CimInstance Win32_Processor).Name"],
                    shell=False, stderr=subprocess.DEVNULL
                ).decode().strip()
                return out[:52] if out else platform.processor()[:52]
        except Exception:
            pass
        return platform.processor()[:52] or "Unknown CPU"

    @staticmethod
    def _get_sysinfo():
        uname = platform.uname()
        os_name = uname.system + " " + uname.release
        if uname.system == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                     r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                build   = int(winreg.QueryValueEx(key, "CurrentBuildNumber")[0])
                edition = winreg.QueryValueEx(key, "ProductName")[0]
                winreg.CloseKey(key)
                if build >= 22000:
                    edition = edition.replace("Windows 10", "Windows 11")
                os_name = edition
            except Exception:
                pass
        return {
            "OS":      os_name,
            "Machine": uname.machine,
            "Cores":   f"{psutil.cpu_count(logical=False)}P / {psutil.cpu_count(logical=True)}L",
            "Python":  platform.python_version(),
        }


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = WGMonitor()
    app.mainloop()