#!/usr/bin/env python3
"""Advanced password generator with GUI — complexity options, security rules, clipboard."""

import random
import secrets
import string
import tkinter as tk
from tkinter import messagebox, ttk


# Character pools
LOWERCASE = string.ascii_lowercase
UPPERCASE = string.ascii_uppercase
DIGITS = string.digits
SYMBOLS_BASIC = "!@#$%^&*"
SYMBOLS_EXTENDED = "!@#$%^&*()-_=+[]{}|;:,.<>?"


class PasswordGeneratorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Advanced Password Generator")
        self.root.minsize(480, 520)
        self.root.resizable(True, True)

        self._build_ui()
        self._update_strength_preview()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        # --- Output ---
        output_frame = ttk.LabelFrame(main, text="Generated Password", padding=10)
        output_frame.pack(fill=tk.X, pady=(0, 12))

        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(
            output_frame,
            textvariable=self.password_var,
            font=("Consolas", 14),
            state="readonly",
        )
        self.password_entry.pack(fill=tk.X, pady=(0, 8))

        btn_row = ttk.Frame(output_frame)
        btn_row.pack(fill=tk.X)

        ttk.Button(btn_row, text="Generate", command=self.generate_password).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btn_row, text="Copy to Clipboard", command=self.copy_to_clipboard).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btn_row, text="Clear", command=self.clear_password).pack(side=tk.LEFT)

        # --- Length ---
        length_frame = ttk.LabelFrame(main, text="Length", padding=10)
        length_frame.pack(fill=tk.X, pady=(0, 12))

        self.length_var = tk.IntVar(value=16)
        self.length_label = ttk.Label(length_frame, text="16 characters")
        self.length_label.pack(anchor=tk.W)

        length_scale = ttk.Scale(
            length_frame,
            from_=8,
            to=64,
            orient=tk.HORIZONTAL,
            variable=self.length_var,
            command=self._on_length_change,
        )
        length_scale.pack(fill=tk.X, pady=4)

        # --- Character sets ---
        charset_frame = ttk.LabelFrame(main, text="Character Sets", padding=10)
        charset_frame.pack(fill=tk.X, pady=(0, 12))

        self.use_lower = tk.BooleanVar(value=True)
        self.use_upper = tk.BooleanVar(value=True)
        self.use_digits = tk.BooleanVar(value=True)
        self.use_symbols = tk.BooleanVar(value=True)
        self.use_extended_symbols = tk.BooleanVar(value=False)

        checks = [
            (self.use_lower, "Lowercase (a-z)"),
            (self.use_upper, "Uppercase (A-Z)"),
            (self.use_digits, "Digits (0-9)"),
            (self.use_symbols, "Symbols (!@#$%^&*)"),
            (self.use_extended_symbols, "Extended symbols (-_=+[]{}|;:,.<>?)"),
        ]
        for var, label in checks:
            ttk.Checkbutton(
                charset_frame,
                text=label,
                variable=var,
                command=self._update_strength_preview,
            ).pack(anchor=tk.W, pady=1)

        # --- Security rules ---
        rules_frame = ttk.LabelFrame(main, text="Security Rules", padding=10)
        rules_frame.pack(fill=tk.X, pady=(0, 12))

        self.require_each_selected = tk.BooleanVar(value=True)
        self.exclude_ambiguous = tk.BooleanVar(value=True)
        self.no_repeating = tk.BooleanVar(value=False)
        self.no_sequential = tk.BooleanVar(value=True)

        rule_checks = [
            (
                self.require_each_selected,
                "Require at least one character from each selected set",
            ),
            (
                self.exclude_ambiguous,
                "Exclude ambiguous characters (0, O, l, 1, I)",
            ),
            (self.no_repeating, "Avoid consecutive identical characters"),
            (self.no_sequential, "Avoid simple sequences (abc, 123, qwerty)"),
        ]
        for var, label in rule_checks:
            ttk.Checkbutton(
                rules_frame,
                text=label,
                variable=var,
                command=self._update_strength_preview,
            ).pack(anchor=tk.W, pady=1)

        # --- Strength indicator ---
        strength_frame = ttk.LabelFrame(main, text="Security Preview", padding=10)
        strength_frame.pack(fill=tk.X, pady=(0, 12))

        self.strength_var = tk.StringVar(value="Configure options and generate a password.")
        ttk.Label(strength_frame, textvariable=self.strength_var, wraplength=420).pack(
            anchor=tk.W
        )

        self.strength_bar = ttk.Progressbar(
            strength_frame, orient=tk.HORIZONTAL, length=200, mode="determinate"
        )
        self.strength_bar.pack(fill=tk.X, pady=(8, 0))

        # --- Footer ---
        ttk.Label(
            main,
            text="Uses cryptographically secure randomness (secrets module).",
            font=("Segoe UI", 8),
            foreground="gray",
        ).pack(anchor=tk.W, pady=(4, 0))

        self.root.bind("<Control-g>", lambda _: self.generate_password())
        self.root.bind("<Control-c>", lambda e: self._handle_ctrl_c(e))

    def _on_length_change(self, _value: str) -> None:
        length = int(float(self.length_var.get()))
        self.length_label.config(text=f"{length} characters")
        self._update_strength_preview()

    def _handle_ctrl_c(self, event: tk.Event) -> str | None:
        if self.root.focus_get() == self.password_entry:
            self.copy_to_clipboard()
            return "break"
        return None

    def _get_active_pools(self) -> list[tuple[str, str]]:
        pools: list[tuple[str, str]] = []
        if self.use_lower.get():
            pools.append(("lower", LOWERCASE))
        if self.use_upper.get():
            pools.append(("upper", UPPERCASE))
        if self.use_digits.get():
            pools.append(("digits", DIGITS))
        symbols = ""
        if self.use_symbols.get():
            symbols += SYMBOLS_BASIC
        if self.use_extended_symbols.get():
            symbols += SYMBOLS_EXTENDED
        if symbols:
            pools.append(("symbols", symbols))
        return pools

    def _filter_ambiguous(self, charset: str) -> str:
        if not self.exclude_ambiguous.get():
            return charset
        ambiguous = set("0O1lI")
        return "".join(c for c in charset if c not in ambiguous)

    def _is_sequential_pair(self, a: str, b: str) -> bool:
        if not self.no_sequential.get():
            return False
        sequences = [
            string.ascii_lowercase,
            string.ascii_lowercase[::-1],
            string.digits,
            string.digits[::-1],
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm",
        ]
        for seq in sequences:
            for i in range(len(seq) - 1):
                if a == seq[i] and b == seq[i + 1]:
                    return True
                if a == seq[i + 1] and b == seq[i]:
                    return True
        return False

    def _char_allowed(self, char: str, prev: str | None) -> bool:
        if self.no_repeating.get() and prev is not None and char == prev:
            return False
        if prev is not None and self._is_sequential_pair(prev, char):
            return False
        return True

    def _build_charset(self, pools: list[tuple[str, str]]) -> str:
        chars = ""
        for _, pool in pools:
            filtered = self._filter_ambiguous(pool)
            if not filtered:
                raise ValueError(
                    f"Character set '{pool}' is empty after excluding ambiguous characters."
                )
            chars += filtered
        return chars

    def generate_password(self) -> None:
        pools = self._get_active_pools()
        if not pools:
            messagebox.showwarning(
                "No character sets",
                "Select at least one character set to generate a password.",
            )
            return

        length = int(float(self.length_var.get()))
        if self.require_each_selected.get() and length < len(pools):
            messagebox.showwarning(
                "Length too short",
                f"Password length must be at least {len(pools)} to include "
                "one character from each selected set.",
            )
            return

        try:
            charset = self._build_charset(pools)
        except ValueError as exc:
            messagebox.showerror("Invalid configuration", str(exc))
            return

        password_chars: list[str] = []

        if self.require_each_selected.get():
            for _, pool in pools:
                filtered = self._filter_ambiguous(pool)
                password_chars.append(secrets.choice(filtered))

        max_attempts = length * 200
        attempts = 0
        while len(password_chars) < length:
            attempts += 1
            if attempts > max_attempts:
                messagebox.showerror(
                    "Generation failed",
                    "Could not satisfy all security rules with the current settings. "
                    "Try relaxing rules or increasing length.",
                )
                return

            char = secrets.choice(charset)
            prev = password_chars[-1] if password_chars else None
            if not self._char_allowed(char, prev):
                continue
            password_chars.append(char)

        random.SystemRandom().shuffle(password_chars)
        password = "".join(password_chars)

        self.password_var.set(password)
        self._update_strength_preview(password)
        self.root.bell()

    def copy_to_clipboard(self) -> None:
        password = self.password_var.get()
        if not password:
            messagebox.showinfo("Nothing to copy", "Generate a password first.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(password)
        self.root.update()
        self._flash_status("Copied to clipboard!")

    def clear_password(self) -> None:
        self.password_var.set("")
        self._update_strength_preview()

    def _flash_status(self, message: str) -> None:
        original = self.strength_var.get()
        self.strength_var.set(message)
        self.root.after(2000, lambda: self.strength_var.set(original))

    def _estimate_entropy(self, length: int, charset_size: int) -> float:
        if charset_size <= 0 or length <= 0:
            return 0.0
        import math

        return length * math.log2(charset_size)

    def _strength_label(self, entropy: float) -> tuple[str, int]:
        if entropy < 40:
            return "Weak — consider a longer password or more character types.", 25
        if entropy < 60:
            return "Fair — acceptable for low-risk accounts.", 50
        if entropy < 80:
            return "Strong — suitable for most accounts.", 75
        return "Very strong — excellent for sensitive accounts.", 100

    def _update_strength_preview(self, password: str | None = None) -> None:
        pools = self._get_active_pools()
        length = int(float(self.length_var.get()))

        if password is None:
            password = self.password_var.get()

        if not pools:
            self.strength_var.set("Select at least one character set.")
            self.strength_bar["value"] = 0
            return

        try:
            charset_size = len(set(self._build_charset(pools)))
        except ValueError as exc:
            self.strength_var.set(str(exc))
            self.strength_bar["value"] = 0
            return

        eval_length = len(password) if password else length
        entropy = self._estimate_entropy(eval_length, charset_size)
        label, bar_value = self._strength_label(entropy)

        rules_active = []
        if self.require_each_selected.get():
            rules_active.append("mixed sets")
        if self.exclude_ambiguous.get():
            rules_active.append("no ambiguous")
        if self.no_repeating.get():
            rules_active.append("no repeats")
        if self.no_sequential.get():
            rules_active.append("no sequences")

        rules_text = f" | Rules: {', '.join(rules_active)}" if rules_active else ""
        entropy_text = f"Estimated entropy: {entropy:.1f} bits — {label}{rules_text}"
        self.strength_var.set(entropy_text)
        self.strength_bar["value"] = bar_value


def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    elif "clam" in style.theme_names():
        style.theme_use("clam")

    PasswordGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
