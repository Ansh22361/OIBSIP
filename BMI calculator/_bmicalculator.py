import csv
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from bmi_logic import (
    calculate_bmi, bmi_category, height_to_meters,
    lbs_to_kg, kg_to_lbs, m_to_cm, parse_datetime,
)
from database import Database


COLORS = {
    "bg": "#f4f6f8",
    "card": "#ffffff",
    "primary": "#2563eb",
    "text": "#1e293b",
    "muted": "#64748b",
    "underweight": "#3498db",
    "normal": "#2ecc71",
    "overweight": "#f39c12",
    "obese": "#e74c3c",
}


class BMICalculatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BMI Calculator Pro")
        self.geometry("1000x740")
        self.minsize(920, 680)
        self.configure(bg=COLORS["bg"])

        self.db = Database("data/bmi.db")
        self.weight_unit = tk.StringVar(value="kg")
        self.height_unit = tk.StringVar(value="cm")
        self.record_ids: dict[str, int] = {}

        self.style = ttk.Style(self)
        self._setup_styles()
        self._build_ui()
        self.refresh_users()
        self.bind("<Return>", lambda _e: self.on_calculate())

    def _setup_styles(self):
        self.style.theme_use("clam")
        self.style.configure("TFrame", background=COLORS["bg"])
        self.style.configure("Card.TFrame", background=COLORS["card"])
        self.style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
        self.style.configure("Card.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 20, "bold"))
        self.style.configure("Subtitle.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=("Segoe UI", 10))
        self.style.configure("Result.TLabel", background=COLORS["card"], font=("Segoe UI", 24, "bold"))
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))
        self.style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(18, 8))
        ttk.Label(header, text="BMI Calculator Pro", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Calculate, store, and analyze BMI for multiple users.", style="Subtitle.TLabel").pack(anchor="w")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.calc_frame = ttk.Frame(self.notebook)
        self.history_frame = ttk.Frame(self.notebook)
        self.trends_frame = ttk.Frame(self.notebook)
        self.users_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.calc_frame, text="  Calculator  ")
        self.notebook.add(self.history_frame, text="  History  ")
        self.notebook.add(self.trends_frame, text="  Trends  ")
        self.notebook.add(self.users_frame, text="  Users  ")

        self._build_calculator_tab()
        self._build_history_tab()
        self._build_trends_tab()
        self._build_users_tab()

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, anchor="w", style="Subtitle.TLabel").pack(fill="x", padx=20, pady=(0, 12))
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _card(self, parent, title):
        outer = ttk.Frame(parent, style="Card.TFrame", padding=16)
        outer.pack(fill="both", expand=True, padx=8, pady=8)
        ttk.Label(outer, text=title, style="Card.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 12))
        return outer

    def _build_calculator_tab(self):
        container = ttk.Frame(self.calc_frame)
        container.pack(fill="both", expand=True)

        left = self._card(container, "User & Measurements")
        right = self._card(container, "Result")

        user_row = ttk.Frame(left, style="Card.TFrame")
        user_row.pack(fill="x", pady=4)
        ttk.Label(user_row, text="Select User", style="Card.TLabel", width=14).pack(side="left")
        self.user_var = tk.StringVar()
        self.user_combo = ttk.Combobox(user_row, textvariable=self.user_var, state="readonly", width=26)
        self.user_combo.pack(side="left", padx=(0, 8))
        self.user_combo.bind("<<ComboboxSelected>>", lambda _e: self.on_user_selected())
        ttk.Button(user_row, text="+ Add User", command=self.on_add_user).pack(side="left")

        unit_row = ttk.Frame(left, style="Card.TFrame")
        unit_row.pack(fill="x", pady=(10, 6))
        ttk.Label(unit_row, text="Units", style="Card.TLabel", width=14).pack(side="left")
        ttk.Radiobutton(unit_row, text="kg / cm", variable=self.weight_unit, value="kg",
                        command=self._sync_unit_labels).pack(side="left")
        ttk.Radiobutton(unit_row, text="lbs / ft-in", variable=self.weight_unit, value="lbs",
                        command=self._sync_unit_labels).pack(side="left", padx=(12, 0))

        self.weight_label = ttk.Label(left, text="Weight (kg)", style="Card.TLabel")
        self.weight_label.pack(anchor="w")
        self.weight_entry = ttk.Entry(left, width=32)
        self.weight_entry.pack(fill="x", pady=(2, 8))

        self.height_label = ttk.Label(left, text="Height (cm)", style="Card.TLabel")
        self.height_label.pack(anchor="w")
        self.height_entry = ttk.Entry(left, width=32)
        self.height_entry.pack(fill="x", pady=(2, 8))

        self.height_ft_label = ttk.Label(left, text="Height (ft)", style="Card.TLabel")
        self.height_ft_entry = ttk.Entry(left, width=32)

        self.height_in_label = ttk.Label(left, text="Height (in)", style="Card.TLabel")
        self.height_in_entry = ttk.Entry(left, width=32)

        btn_row = ttk.Frame(left, style="Card.TFrame")
        btn_row.pack(fill="x", pady=(16, 0))
        ttk.Button(btn_row, text="Calculate BMI", style="Primary.TButton", command=self.on_calculate).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Clear", command=self.on_clear).pack(side="left")
        ttk.Button(btn_row, text="Load Latest", command=self.load_latest_for_user).pack(side="left", padx=(8, 0))

        self.result_label = ttk.Label(right, text="—", style="Result.TLabel", foreground=COLORS["muted"])
        self.result_label.pack(anchor="w")
        self.category_label = ttk.Label(right, text="Enter values and press Calculate or Enter.", style="Card.TLabel", foreground=COLORS["muted"])
        self.category_label.pack(anchor="w", pady=(4, 16))

        self.gauge_canvas = tk.Canvas(right, width=340, height=28, bg=COLORS["card"], highlightthickness=0)
        self.gauge_canvas.pack(anchor="w", pady=(0, 16))
        self._draw_gauge(None)

        guide = (
            "BMI Categories:\n"
            "• Underweight: below 18.5\n"
            "• Normal: 18.5 – 24.9\n"
            "• Overweight: 25 – 29.9\n"
            "• Obese: 30 and above"
        )
        ttk.Label(right, text=guide, style="Card.TLabel", foreground=COLORS["muted"]).pack(anchor="w")
        self._sync_unit_labels()

    def _sync_unit_labels(self):
        if self.weight_unit.get() == "kg":
            self.height_unit.set("cm")
            self.weight_label.config(text="Weight (kg)")
            self.height_label.pack(anchor="w")
            self.height_entry.pack(fill="x", pady=(2, 8))
            self.height_ft_label.pack_forget()
            self.height_ft_entry.pack_forget()
            self.height_in_label.pack_forget()
            self.height_in_entry.pack_forget()
        else:
            self.height_unit.set("ftin")
            self.weight_label.config(text="Weight (lbs)")
            self.height_label.pack_forget()
            self.height_entry.pack_forget()
            self.height_ft_label.pack(anchor="w")
            self.height_ft_entry.pack(fill="x", pady=(2, 8))
            self.height_in_label.pack(anchor="w")
            self.height_in_entry.pack(fill="x", pady=(2, 8))

    def _build_history_tab(self):
        card = self._card(self.history_frame, "Measurement History")

        toolbar = ttk.Frame(card, style="Card.TFrame")
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="Delete Selected", command=self.on_delete_record).pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Export CSV", command=self.on_export_csv).pack(side="left")

        columns = ("date", "weight", "height", "bmi", "category")
        self.history_tree = ttk.Treeview(card, columns=columns, show="headings", height=14)
        for col, text, width in [
            ("date", "Date", 180), ("weight", "Weight", 100),
            ("height", "Height", 100), ("bmi", "BMI", 80), ("category", "Category", 120),
        ]:
            self.history_tree.heading(col, text=text)
            self.history_tree.column(col, width=width, anchor="center")

        scroll = ttk.Scrollbar(card, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scroll.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _build_trends_tab(self):
        stats_card = self._card(self.trends_frame, "Statistics")
        self.stats_labels = {}
        for key, label in [
            ("latest", "Latest BMI"), ("average", "Average BMI"),
            ("min", "Minimum"), ("max", "Maximum"),
            ("change", "Change"), ("count", "Total Records"),
        ]:
            row = ttk.Frame(stats_card, style="Card.TFrame")
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, style="Card.TLabel", width=16).pack(side="left")
            val = ttk.Label(row, text="—", style="Card.TLabel", font=("Segoe UI", 11, "bold"))
            val.pack(side="left")
            self.stats_labels[key] = val

        chart_card = self._card(self.trends_frame, "BMI Trend Chart")
        self.chart_container = ttk.Frame(chart_card, style="Card.TFrame")
        self.chart_container.pack(fill="both", expand=True)

    def _build_users_tab(self):
        card = self._card(self.users_frame, "Manage Users")
        columns = ("name", "records", "latest_bmi", "created")
        self.users_tree = ttk.Treeview(card, columns=columns, show="headings", height=12)
        for col, text, width in [
            ("name", "Name", 180), ("records", "Records", 90),
            ("latest_bmi", "Latest BMI", 100), ("created", "Created", 180),
        ]:
            self.users_tree.heading(col, text=text)
            self.users_tree.column(col, width=width, anchor="center")

        scroll = ttk.Scrollbar(card, orient="vertical", command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=scroll.set)
        self.users_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        btns = ttk.Frame(self.users_frame, style="Card.TFrame")
        btns.pack(fill="x", padx=24, pady=(0, 12))
        ttk.Button(btns, text="Add User", command=self.on_add_user).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Delete Selected User", command=self.on_delete_user).pack(side="left")

    def _draw_gauge(self, bmi):
        c = self.gauge_canvas
        c.delete("all")
        width, height = 340, 28
        ranges = [(0, 18.5, COLORS["underweight"]), (18.5, 25, COLORS["normal"]),
                  (25, 30, COLORS["overweight"]), (30, 40, COLORS["obese"])]
        max_bmi = 40
        x = 0
        for start, end, color in ranges:
            seg_w = (end - start) / max_bmi * width
            c.create_rectangle(x, 4, x + seg_w, height - 4, fill=color, outline="")
            x += seg_w
        if bmi is not None:
            marker_x = min(max(bmi / max_bmi * width, 0), width)
            c.create_polygon(marker_x, 0, marker_x - 6, height, marker_x + 6, height, fill=COLORS["text"])

    def _get_height_m(self) -> float:
        if self.weight_unit.get() == "kg":
            return height_to_meters(cm=float(self.height_entry.get()))
        feet = float(self.height_ft_entry.get() or 0)
        inches = float(self.height_in_entry.get() or 0)
        return height_to_meters(feet=feet, inches=inches)

    def _get_weight_kg(self) -> float:
        value = float(self.weight_entry.get())
        return value if self.weight_unit.get() == "kg" else lbs_to_kg(value)

    def _fill_inputs_from_record(self, record: dict):
        self.on_clear(show_status=False)
        if self.weight_unit.get() == "kg":
            self.weight_entry.insert(0, str(record["weight_kg"]))
            self.height_entry.insert(0, str(m_to_cm(record["height_m"])))
        else:
            self.weight_entry.insert(0, str(kg_to_lbs(record["weight_kg"])))
            total_inches = record["height_m"] / 0.0254
            feet = int(total_inches // 12)
            inches = round(total_inches % 12, 1)
            self.height_ft_entry.insert(0, str(feet))
            self.height_in_entry.insert(0, str(inches))

    def on_user_selected(self):
        self.load_latest_for_user(show_status=False)
        self._refresh_all_views()

    def load_latest_for_user(self, show_status=True):
        user_name = self.user_var.get()
        if not user_name:
            return
        record = self.db.get_latest_record(self.db.get_user_id(user_name))
        if record:
            self._fill_inputs_from_record(record)
            if show_status:
                self.status_var.set(f"Loaded latest record for {user_name}")
        elif show_status:
            self.status_var.set(f"No records yet for {user_name}")

    def refresh_users(self):
        users = self.db.get_users()
        names = [u["name"] for u in users]
        self.user_combo["values"] = names
        if names and self.user_var.get() not in names:
            self.user_var.set(names[0])
        self.refresh_users_tab()
        self._refresh_all_views()

    def refresh_users_tab(self):
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        for user in self.db.get_users():
            uid = user["id"]
            stats = self.db.get_statistics(uid)
            self.users_tree.insert("", "end", values=(
                user["name"],
                stats["count"] if stats else 0,
                stats["latest"] if stats else "—",
                user["created_at"],
            ))

    def _refresh_all_views(self):
        self.refresh_history()
        self.refresh_stats()
        self.refresh_trends()

    def refresh_history(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        self.record_ids.clear()

        user_name = self.user_var.get()
        if not user_name:
            return

        unit = self.weight_unit.get()
        for row in self.db.get_history(self.db.get_user_id(user_name)):
            iid = self.history_tree.insert("", "end", values=(
                row["recorded_at"],
                f'{row["weight_kg"]:.1f} kg' if unit == "kg" else f'{kg_to_lbs(row["weight_kg"])} lbs',
                f'{m_to_cm(row["height_m"])} cm' if unit == "kg" else f'{row["height_m"] / 0.0254 / 12:.1f} ft',
                f'{row["bmi"]:.2f}',
                row["category"],
            ))
            self.record_ids[iid] = row["id"]

    def refresh_stats(self):
        user_name = self.user_var.get()
        stats = self.db.get_statistics(self.db.get_user_id(user_name)) if user_name else None
        for key, label in self.stats_labels.items():
            if not stats:
                label.config(text="—")
            elif key == "change":
                change = stats["change"]
                sign = "+" if change > 0 else ""
                label.config(text=f"{sign}{change}")
            else:
                label.config(text=str(stats[key]))

    def refresh_trends(self):
        for widget in self.chart_container.winfo_children():
            widget.destroy()

        user_name = self.user_var.get()
        if not user_name:
            ttk.Label(self.chart_container, text="Select a user to view trends.", style="Card.TLabel").pack()
            return

        records = list(reversed(self.db.get_history(self.db.get_user_id(user_name))))
        if not records:
            ttk.Label(self.chart_container, text="No records yet for this user.", style="Card.TLabel").pack()
            return

        dates = [parse_datetime(r["recorded_at"]) for r in records]
        bmis = [r["bmi"] for r in records]

        fig = Figure(figsize=(8.5, 3.8), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(dates, bmis, marker="o", linewidth=2, color=COLORS["primary"])
        ax.axhspan(0, 18.5, alpha=0.08, color=COLORS["underweight"])
        ax.axhspan(18.5, 25, alpha=0.08, color=COLORS["normal"])
        ax.axhspan(25, 30, alpha=0.08, color=COLORS["overweight"])
        ax.axhspan(30, 40, alpha=0.08, color=COLORS["obese"])
        ax.set_title(f"BMI Trend — {user_name}")
        ax.set_xlabel("Date")
        ax.set_ylabel("BMI")
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def on_add_user(self):
        name = simpledialog.askstring("Add User", "Enter user name:")
        if not name:
            return
        try:
            self.db.add_user(name.strip())
            self.user_var.set(name.strip())
            self.refresh_users()
            self.status_var.set(f"Added user: {name.strip()}")
        except sqlite3.IntegrityError:
            messagebox.showwarning("Duplicate", "That user already exists.")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def on_delete_user(self):
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showinfo("Delete User", "Select a user first.")
            return
        name = self.users_tree.item(selected[0], "values")[0]
        if not messagebox.askyesno("Confirm", f"Delete '{name}' and all their records?"):
            return
        self.db.delete_user(name)
        self.user_var.set("")
        self.refresh_users()
        self.status_var.set(f"Deleted user: {name}")

    def on_delete_record(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showinfo("Delete Record", "Select a record first.")
            return
        record_id = self.record_ids.get(selected[0])
        if record_id is None:
            return
        if messagebox.askyesno("Confirm", "Delete this record?"):
            self.db.delete_record(record_id)
            self._refresh_all_views()
            self.status_var.set("Record deleted")

    def on_export_csv(self):
        user_name = self.user_var.get()
        if not user_name:
            messagebox.showwarning("Export", "Select a user first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"{user_name.replace(' ', '_')}_bmi_history.csv",
        )
        if not path:
            return
        self.db.export_csv(self.db.get_user_id(user_name), path)
        self.status_var.set(f"Exported history to {path}")
        messagebox.showinfo("Export", "CSV exported successfully.")

    def on_clear(self, show_status=True):
        for entry in [self.weight_entry, self.height_entry, self.height_ft_entry, self.height_in_entry]:
            entry.delete(0, tk.END)
        self.result_label.config(text="—", foreground=COLORS["muted"])
        self.category_label.config(text="Enter values and press Calculate or Enter.")
        self._draw_gauge(None)
        if show_status:
            self.status_var.set("Inputs cleared")

    def on_calculate(self):
        user_name = self.user_var.get()
        if not user_name:
            messagebox.showwarning("No user", "Please select or add a user first.")
            return
        try:
            weight = self._get_weight_kg()
            height_m = self._get_height_m()
            if weight <= 0 or height_m <= 0:
                raise ValueError("Weight and height must be positive numbers.")

            bmi = calculate_bmi(weight, height_m)
            category, color = bmi_category(bmi)
            self.result_label.config(text=str(bmi), foreground=color)
            self.category_label.config(text=f"Category: {category}", foreground=color)
            self._draw_gauge(bmi)

            self.db.add_record(self.db.get_user_id(user_name), weight, height_m, bmi, category)
            self.refresh_users()
            self.status_var.set(f"Saved BMI {bmi} for {user_name}")
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))

    def _on_tab_changed(self, _event):
        self._refresh_all_views()


if __name__ == "__main__":
    app = BMICalculatorApp()
    app.mainloop()