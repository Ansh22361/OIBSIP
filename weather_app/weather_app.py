"""
SkyCast — Graphical weather application (Tkinter).
Uses Open-Meteo (free, no API key) and IP-based location detection.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading

from weather_api import (
    WeatherAPIError,
    detect_location_by_ip,
    fetch_weather,
    geocode_location,
    weather_info,
    wind_direction,
)


# --- Theme ---
COLORS = {
    "bg": "#0d1b2a",
    "card": "#1b2838",
    "card_alt": "#243447",
    "accent": "#4cc9f0",
    "accent2": "#7209b7",
    "text": "#e0e6ed",
    "muted": "#8899a6",
    "success": "#06d6a0",
    "hourly_bg": "#1e3048",
}


class WeatherApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SkyCast Weather")
        self.geometry("920x680")
        self.minsize(800, 600)
        self.configure(bg=COLORS["bg"])

        self._location_label = "—"
        self._lat = None
        self._lon = None
        self._busy = False

        self._setup_styles()
        self._build_ui()
        self.bind("<Return>", lambda _: self._search_location())

    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Card.TFrame", background=COLORS["card"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=COLORS["card"], foreground=COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 14, "bold"))
        style.configure("BigTemp.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=("Segoe UI", 42, "bold"))
        style.configure("Icon.TLabel", background=COLORS["card"], font=("Segoe UI", 56))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", COLORS["accent"])])

    def _build_ui(self) -> None:
        # Top bar — search
        top = ttk.Frame(self, padding=(16, 12))
        top.pack(fill=tk.X)

        ttk.Label(top, text="🌤 SkyCast", style="Title.TLabel").pack(side=tk.LEFT)

        search_frame = ttk.Frame(top)
        search_frame.pack(side=tk.RIGHT)

        self.search_var = tk.StringVar()
        entry = ttk.Entry(search_frame, textvariable=self.search_var, width=28, font=("Segoe UI", 11))
        entry.pack(side=tk.LEFT, padx=(0, 6))
        entry.insert(0, "")
        entry.configure(foreground=COLORS["text"])

        ttk.Button(search_frame, text="Search", command=self._search_location).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_frame, text="📍 My Location", command=self._detect_location).pack(side=tk.LEFT, padx=2)
        self.refresh_btn = ttk.Button(search_frame, text="↻", width=3, command=self._refresh)
        self.refresh_btn.pack(side=tk.LEFT, padx=2)

        self.status_var = tk.StringVar(value="Enter a city or use 📍 My Location to get started.")
        status = ttk.Label(self, textvariable=self.status_var, foreground=COLORS["muted"], font=("Segoe UI", 9))
        status.pack(anchor=tk.W, padx=16)

        # Scrollable main area
        canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        self.main = ttk.Frame(canvas)
        self.main.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.main, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._build_current_card()
        self._build_details_row()
        self._build_hourly_section()
        self._build_daily_section()

    def _card(self, parent, **kw) -> ttk.Frame:
        f = ttk.Frame(parent, style="Card.TFrame", padding=16, **kw)
        return f

    def _build_current_card(self) -> None:
        self.current_card = self._card(self.main)
        self.current_card.pack(fill=tk.X, padx=12, pady=(8, 6))

        row = ttk.Frame(self.current_card, style="Card.TFrame")
        row.pack(fill=tk.X)

        left = ttk.Frame(row, style="Card.TFrame")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.loc_label = ttk.Label(left, text="—", style="Card.TLabel", font=("Segoe UI", 16, "bold"))
        self.loc_label.pack(anchor=tk.W)

        self.cond_label = ttk.Label(left, text="—", style="Muted.TLabel", font=("Segoe UI", 12))
        self.cond_label.pack(anchor=tk.W, pady=(4, 8))

        self.temp_label = ttk.Label(left, text="—°", style="BigTemp.TLabel")
        self.temp_label.pack(anchor=tk.W)

        self.feels_label = ttk.Label(left, text="", style="Muted.TLabel")
        self.feels_label.pack(anchor=tk.W)

        self.icon_label = ttk.Label(row, text="🌡️", style="Icon.TLabel")
        self.icon_label.pack(side=tk.RIGHT, padx=(12, 0))

    def _build_details_row(self) -> None:
        self.details_frame = self._card(self.main)
        self.details_frame.pack(fill=tk.X, padx=12, pady=6)

        grid = ttk.Frame(self.details_frame, style="Card.TFrame")
        grid.pack(fill=tk.X)
        for c in range(4):
            grid.columnconfigure(c, weight=1)

        self.detail_vars = {}
        items = [
            ("wind", "💨 Wind", "—"),
            ("humidity", "💧 Humidity", "—"),
            ("precip", "🌧 Precipitation", "—"),
            ("pressure", "📊 Pressure", "—"),
        ]
        for i, (key, title, default) in enumerate(items):
            cell = ttk.Frame(grid, style="Card.TFrame", padding=8)
            cell.grid(row=0, column=i, sticky="nsew", padx=4)
            ttk.Label(cell, text=title, style="Muted.TLabel").pack(anchor=tk.W)
            var = tk.StringVar(value=default)
            self.detail_vars[key] = var
            ttk.Label(cell, textvariable=var, style="Card.TLabel", font=("Segoe UI", 13, "bold")).pack(anchor=tk.W)

    def _build_hourly_section(self) -> None:
        wrap = ttk.Frame(self.main)
        wrap.pack(fill=tk.X, padx=12, pady=(12, 4))
        ttk.Label(wrap, text="Hourly Forecast", style="Title.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)

        self.hourly_canvas = tk.Canvas(wrap, bg=COLORS["bg"], height=130, highlightthickness=0)
        self.hourly_canvas.pack(fill=tk.X, pady=4)
        self.hourly_inner = ttk.Frame(self.hourly_canvas)
        self.hourly_canvas.create_window((0, 0), window=self.hourly_inner, anchor=tk.NW)

        def _hscroll(e):
            self.hourly_canvas.xview_scroll(int(-1 * (e.delta / 120)), "units")

        self.hourly_canvas.bind("<Enter>", lambda _: self.hourly_canvas.bind_all("<MouseWheel>", _hscroll))
        self.hourly_canvas.bind("<Leave>", lambda _: self.hourly_canvas.unbind_all("<MouseWheel>"))

    def _build_daily_section(self) -> None:
        wrap = ttk.Frame(self.main)
        wrap.pack(fill=tk.X, padx=12, pady=(12, 16))
        ttk.Label(wrap, text="7-Day Forecast", style="Title.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)

        self.daily_frame = ttk.Frame(wrap)
        self.daily_frame.pack(fill=tk.X, pady=6)
        for c in range(7):
            self.daily_frame.columnconfigure(c, weight=1)

    # --- Actions ---

    def _set_busy(self, busy: bool, msg: str = "") -> None:
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.refresh_btn.configure(state=state)
        if msg:
            self.status_var.set(msg)

    def _run_async(self, fn, on_ok, on_err=None) -> None:
        if self._busy:
            return
        self._set_busy(True, "Loading weather data…")

        def worker():
            try:
                result = fn()
                self.after(0, lambda: self._finish_ok(on_ok, result))
            except WeatherAPIError as exc:
                self.after(0, lambda: self._finish_err(on_err, str(exc)))
            except Exception as exc:
                self.after(0, lambda: self._finish_err(on_err, f"Unexpected error: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_ok(self, callback, result) -> None:
        self._set_busy(False)
        callback(result)
        self.status_var.set(f"Updated {datetime.now().strftime('%H:%M')} — {self._location_label}")

    def _finish_err(self, on_err, msg: str) -> None:
        self._set_busy(False)
        self.status_var.set(msg)
        if on_err:
            on_err(msg)
        else:
            messagebox.showerror("Weather", msg)

    def _search_location(self) -> None:
        query = self.search_var.get().strip()
        if not query:
            messagebox.showinfo("Search", "Enter a city name, e.g. London or New York.")
            return

        def work():
            results = geocode_location(query)
            return results[0]

        def apply(place):
            self._location_label = f"{place['name']}, {place.get('country_code', '')}"
            self._lat = place["latitude"]
            self._lon = place["longitude"]
            self._load_weather()

        self._run_async(work, apply)

    def _detect_location(self) -> None:
        def work():
            return detect_location_by_ip()

        def apply(result):
            lat, lon, label = result
            self._location_label = label
            self._lat = lat
            self._lon = lon
            self.search_var.set(label.split(",")[0])
            self._load_weather()

        self._run_async(work, apply)

    def _refresh(self) -> None:
        if self._lat is not None and self._lon is not None:
            self._load_weather()
        else:
            self._detect_location()

    def _load_weather(self) -> None:
        lat, lon = self._lat, self._lon

        def work():
            return fetch_weather(lat, lon)

        self._run_async(work, self._render_weather)

    def _render_weather(self, data: dict) -> None:
        cur = data.get("current", {})
        units = data.get("current_units", {})
        daily = data.get("daily", {})
        hourly = data.get("hourly", {})

        code = cur.get("weather_code")
        icon, desc = weather_info(code)
        temp = cur.get("temperature_2m")
        temp_u = units.get("temperature_2m", "°C")
        feels = cur.get("apparent_temperature")

        self.loc_label.configure(text=self._location_label)
        self.cond_label.configure(text=desc)
        self.icon_label.configure(text=icon)
        self.temp_label.configure(text=f"{temp:.0f}{temp_u}" if temp is not None else "—")
        self.feels_label.configure(
            text=f"Feels like {feels:.0f}{temp_u}" if feels is not None else ""
        )

        wind = cur.get("wind_speed_10m")
        wind_u = units.get("wind_speed_10m", "km/h")
        wdir = wind_direction(cur.get("wind_direction_10m"))
        self.detail_vars["wind"].set(f"{wind:.0f} {wind_u} {wdir}" if wind is not None else "—")

        hum = cur.get("relative_humidity_2m")
        self.detail_vars["humidity"].set(f"{hum}%" if hum is not None else "—")

        precip = cur.get("precipitation")
        precip_u = units.get("precipitation", "mm")
        self.detail_vars["precip"].set(f"{precip} {precip_u}" if precip is not None else "—")

        press = cur.get("surface_pressure")
        press_u = units.get("surface_pressure", "hPa")
        self.detail_vars["pressure"].set(f"{press:.0f} {press_u}" if press is not None else "—")

        self._render_hourly(hourly, data.get("hourly_units", {}))
        self._render_daily(daily, data.get("daily_units", {}))

    def _render_hourly(self, hourly: dict, units: dict) -> None:
        for w in self.hourly_inner.winfo_children():
            w.destroy()

        times = hourly.get("time", [])[:24]
        temps = hourly.get("temperature_2m", [])
        codes = hourly.get("weather_code", [])
        winds = hourly.get("wind_speed_10m", [])
        pops = hourly.get("precipitation_probability", [])
        temp_u = units.get("temperature_2m", "°C")
        wind_u = units.get("wind_speed_10m", "km/h")

        for i, t in enumerate(times):
            dt = datetime.fromisoformat(t)
            hour_label = dt.strftime("%H:%M") if i > 0 else "Now"
            icon, _ = weather_info(codes[i] if i < len(codes) else None)
            temp = temps[i] if i < len(temps) else None
            wind = winds[i] if i < len(winds) else None
            pop = pops[i] if i < len(pops) else None

            cell = tk.Frame(
                self.hourly_inner,
                bg=COLORS["hourly_bg"],
                padx=12,
                pady=10,
                highlightbackground=COLORS["card_alt"],
                highlightthickness=1,
            )
            cell.pack(side=tk.LEFT, padx=4)

            tk.Label(cell, text=hour_label, bg=COLORS["hourly_bg"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack()
            tk.Label(cell, text=icon, bg=COLORS["hourly_bg"], font=("Segoe UI", 22)).pack()
            tk.Label(
                cell,
                text=f"{temp:.0f}{temp_u}" if temp is not None else "—",
                bg=COLORS["hourly_bg"],
                fg=COLORS["text"],
                font=("Segoe UI", 11, "bold"),
            ).pack()
            tk.Label(
                cell,
                text=f"💨 {wind:.0f}" if wind is not None else "",
                bg=COLORS["hourly_bg"],
                fg=COLORS["muted"],
                font=("Segoe UI", 8),
            ).pack()
            if pop is not None:
                tk.Label(cell, text=f"{pop}%", bg=COLORS["hourly_bg"], fg=COLORS["accent"], font=("Segoe UI", 8)).pack()

        self.hourly_inner.update_idletasks()
        self.hourly_canvas.configure(scrollregion=self.hourly_canvas.bbox("all"))

    def _render_daily(self, daily: dict, units: dict) -> None:
        for w in self.daily_frame.winfo_children():
            w.destroy()

        dates = daily.get("time", [])
        maxs = daily.get("temperature_2m_max", [])
        mins = daily.get("temperature_2m_min", [])
        codes = daily.get("weather_code", [])
        winds = daily.get("wind_speed_10m_max", [])
        precips = daily.get("precipitation_sum", [])
        temp_u = units.get("temperature_2m_max", "°C")
        wind_u = units.get("wind_speed_10m_max", "km/h")

        for i, d in enumerate(dates):
            dt = datetime.fromisoformat(d)
            day_name = "Today" if i == 0 else dt.strftime("%a")
            icon, desc = weather_info(codes[i] if i < len(codes) else None)
            hi = maxs[i] if i < len(maxs) else None
            lo = mins[i] if i < len(mins) else None
            wind = winds[i] if i < len(winds) else None
            precip = precips[i] if i < len(precips) else None

            cell = tk.Frame(
                self.daily_frame,
                bg=COLORS["card"],
                padx=8,
                pady=12,
                highlightbackground=COLORS["card_alt"],
                highlightthickness=1,
            )
            cell.grid(row=0, column=i, sticky="nsew", padx=3)

            tk.Label(cell, text=day_name, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).pack()
            tk.Label(cell, text=dt.strftime("%d %b"), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack()
            tk.Label(cell, text=icon, bg=COLORS["card"], font=("Segoe UI", 26)).pack(pady=4)
            tk.Label(
                cell,
                text=f"{hi:.0f}° / {lo:.0f}°" if hi is not None and lo is not None else "—",
                bg=COLORS["card"],
                fg=COLORS["text"],
                font=("Segoe UI", 10, "bold"),
            ).pack()
            tk.Label(cell, text=desc[:12], bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 7)).pack()
            if wind is not None:
                tk.Label(
                    cell,
                    text=f"💨 {wind:.0f} {wind_u}",
                    bg=COLORS["card"],
                    fg=COLORS["muted"],
                    font=("Segoe UI", 8),
                ).pack()
            if precip is not None and precip > 0:
                tk.Label(
                    cell,
                    text=f"🌧 {precip:.1f} mm",
                    bg=COLORS["card"],
                    fg=COLORS["accent"],
                    font=("Segoe UI", 8),
                ).pack()


def main() -> None:
    app = WeatherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
