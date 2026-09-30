"""
main.py
--------
Transora
CodeAlpha AI Internship — Task 1

A clean, modern Tkinter desktop application that lets a user type
text, pick a source and target language, and translate it instantly.

Layout note: the language selectors AND the action buttons
(Translate / Clear / Copy Translation) live in ONE fixed top bar,
above the text panels. Only the two text panels are allowed to grow
or shrink when the window is resized. This guarantees the buttons
are ALWAYS visible, no matter the window size — they can never be
pushed off-screen the way they could in the previous layout.

Run with:
    python main.py
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

import pyperclip

from translator import (
    translate_text,
    TranslationError,
    get_source_language_names,
    get_target_language_names,
)

# ---------------------------------------------------------------------------
# Color palette / fonts — kept in one place so the whole UI stays consistent
# ---------------------------------------------------------------------------
COLOR_BG = "#EEF3FC"           # app background
COLOR_CARD = "#FFFFFF"         # panel background
COLOR_BORDER = "#E3E9F5"
COLOR_TEXT = "#1F2430"
COLOR_SUBTEXT = "#6B7280"

COLOR_PRIMARY = "#4A66F0"       # main blue accent (Translate button)
COLOR_PRIMARY_DARK = "#3A54D6"
COLOR_PRIMARY_SOFT = "#EAF0FF"  # light blue (Swap button bg)

COLOR_GREEN = "#16A34A"         # Copy Translation accent
COLOR_GREEN_SOFT = "#EAFBF1"

COLOR_GRAY_BORDER = "#D8DEE9"   # Clear button border

COLOR_SUCCESS = "#1F9D55"
COLOR_ERROR = "#D64545"

FONT_TITLE = ("Segoe UI", 19, "bold")
FONT_SUBTITLE = ("Segoe UI", 10)
FONT_TAGLINE = ("Segoe UI", 10, "italic")
FONT_LABEL = ("Segoe UI", 10, "bold")
FONT_TEXT = ("Segoe UI", 11)
FONT_BUTTON = ("Segoe UI", 10, "bold")
FONT_STATUS = ("Segoe UI", 9)
FONT_ICON = ("Segoe UI Emoji", 13)
FONT_BIG_ICON = ("Segoe UI Emoji", 30)

# Flags shown next to each language name in the dropdowns
LANGUAGE_FLAGS = {
    "Auto Detect": "🌐",
    "English": "🇺🇸",
    "Urdu": "🇵🇰",
    "Hindi": "🇮🇳",
    "Arabic": "🇸🇦",
    "French": "🇫🇷",
    "Spanish": "🇪🇸",
    "German": "🇩🇪",
    "Chinese (Simplified)": "🇨🇳",
    "Japanese": "🇯🇵",
    "Korean": "🇰🇷",
    "Turkish": "🇹🇷",
    "Italian": "🇮🇹",
    "Portuguese": "🇵🇹",
    "Russian": "🇷🇺",
}


def _with_flag(name: str) -> str:
    return f"{LANGUAGE_FLAGS.get(name, '')}  {name}".strip()


def _strip_flag(display_value: str) -> str:
    """Turn '🇺🇸  English' back into 'English'."""
    parts = display_value.split("  ", 1)
    return parts[1].strip() if len(parts) == 2 else display_value.strip()


class TranslationApp(tk.Tk):
    """Main application window for Transora."""

    def __init__(self):
        super().__init__()

        self.title("Transora")
        self.geometry("1150x680")
        self.minsize(900, 560)
        self.configure(bg=COLOR_BG)

        # Root grid: only row 2 (the text panels) is allowed to expand.
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # header
        self.rowconfigure(1, weight=0)  # control bar (languages + buttons)
        self.rowconfigure(2, weight=1)  # text panels — the ONLY growing row
        self.rowconfigure(3, weight=0)  # status bar

        self._configure_styles()
        self._build_header()
        self._build_control_bar()
        self._build_text_panels()
        self._build_status_bar()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Fix: readonly comboboxes on Windows default to a grey field —
        # force them to stay white in every state so they match the cards.
        style.configure(
            "TCombobox",
            fieldbackground=COLOR_CARD,
            background=COLOR_CARD,
            foreground=COLOR_TEXT,
            arrowcolor=COLOR_PRIMARY,
            padding=6,
            relief="flat",
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", COLOR_CARD), ("!disabled", COLOR_CARD)],
            selectbackground=[("readonly", COLOR_CARD)],
            selectforeground=[("readonly", COLOR_TEXT)],
        )

        style.configure(
            "Primary.TButton",
            font=FONT_BUTTON, foreground="white", background=COLOR_PRIMARY,
            padding=(12, 9), borderwidth=0,
        )
        style.map("Primary.TButton",
                  background=[("active", COLOR_PRIMARY_DARK), ("disabled", "#A9B4F5")])

        style.configure(
            "Clear.TButton",
            font=FONT_BUTTON, foreground=COLOR_TEXT, background=COLOR_CARD,
            padding=(11, 9), borderwidth=1,
        )
        style.map("Clear.TButton", background=[("active", "#F3F5FA")])

        style.configure(
            "Copy.TButton",
            font=FONT_BUTTON, foreground=COLOR_GREEN, background=COLOR_CARD,
            padding=(11, 9), borderwidth=1,
        )
        style.map("Copy.TButton", background=[("active", COLOR_GREEN_SOFT)])

        style.configure(
            "Swap.TButton",
            font=FONT_BUTTON, foreground=COLOR_PRIMARY, background=COLOR_PRIMARY_SOFT,
            padding=(10, 8), borderwidth=1,
        )
        style.map("Swap.TButton", background=[("active", "#DCE7FF")])

    def _card(self, parent, **kwargs):
        return tk.Frame(parent, bg=COLOR_CARD, highlightbackground=COLOR_BORDER,
                         highlightthickness=1, bd=0, **kwargs)

    # ---- Header (gradient banner) ------------------------------------
    def _build_header(self):
        self.header_canvas = tk.Canvas(self, height=100, highlightthickness=0, bd=0)
        self.header_canvas.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        self.header_canvas.bind("<Configure>", self._draw_header_gradient)

    def _draw_header_gradient(self, event=None):
        canvas = self.header_canvas
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 2 or height < 2:
            return

        # Horizontal pastel gradient: light blue -> light lavender
        start = (0xDC, 0xEB, 0xFF)
        end = (0xEC, 0xE1, 0xFB)
        steps = 120
        for i in range(steps):
            ratio = i / steps
            r = int(start[0] + (end[0] - start[0]) * ratio)
            g = int(start[1] + (end[1] - start[1]) * ratio)
            b = int(start[2] + (end[2] - start[2]) * ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            x0 = int(width * i / steps)
            x1 = int(width * (i + 1) / steps)
            canvas.create_rectangle(x0, 0, x1, height, fill=color, outline=color)

        # Badge circle with a globe icon
        cx, cy, radius = 42, height // 2, 24
        canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                            fill=COLOR_PRIMARY, outline="")
        canvas.create_text(cx, cy, text="🌐", font=("Segoe UI Emoji", 18), fill="white")

        # Title + subtitle
        canvas.create_text(80, cy - 12, anchor="w", text="Transora",
                            font=FONT_TITLE, fill=COLOR_TEXT)
        canvas.create_text(
            80, cy + 14, anchor="w",
            text="Translate. Connect. Communicate.",
            font=FONT_SUBTITLE, fill=COLOR_SUBTEXT,
        )

        # Tagline on the right (only if there's room)
        if width > 560:
            canvas.create_text(width - 24, cy, anchor="e", text="Break Language Barriers ✨",
                                font=FONT_TAGLINE, fill=COLOR_PRIMARY_DARK)

    # ---- Control bar: languages + swap + action buttons ---------------
    def _build_control_bar(self):
        bar = self._card(self)
        bar.grid(row=1, column=0, sticky="ew", padx=16, pady=8)

        inner = tk.Frame(bar, bg=COLOR_CARD)
        inner.pack(fill="x", padx=16, pady=14)

        # --- Source language ---
        src_col = tk.Frame(inner, bg=COLOR_CARD)
        src_col.pack(side="left")
        tk.Label(src_col, text="Source Language", font=FONT_LABEL,
                 bg=COLOR_CARD, fg=COLOR_TEXT).pack(anchor="w")
        self.source_lang_var = tk.StringVar(value=_with_flag("English"))
        self.source_combo = ttk.Combobox(
            src_col, textvariable=self.source_lang_var,
            values=[_with_flag(n) for n in get_source_language_names()],
            state="readonly", font=FONT_TEXT, width=13,
        )
        self.source_combo.pack(anchor="w", pady=(6, 0))

        # --- Swap button ---
        swap_col = tk.Frame(inner, bg=COLOR_CARD)
        swap_col.pack(side="left", padx=12)
        tk.Label(swap_col, text=" ", bg=COLOR_CARD, font=FONT_LABEL).pack(anchor="w")
        ttk.Button(swap_col, text="⇄  Swap", style="Swap.TButton",
                   command=self.swap_languages).pack(pady=(6, 0))

        # --- Target language ---
        tgt_col = tk.Frame(inner, bg=COLOR_CARD)
        tgt_col.pack(side="left")
        tk.Label(tgt_col, text="Target Language", font=FONT_LABEL,
                 bg=COLOR_CARD, fg=COLOR_TEXT).pack(anchor="w")
        self.target_lang_var = tk.StringVar(value=_with_flag("Urdu"))
        self.target_combo = ttk.Combobox(
            tgt_col, textvariable=self.target_lang_var,
            values=[_with_flag(n) for n in get_target_language_names()],
            state="readonly", font=FONT_TEXT, width=13,
        )
        self.target_combo.pack(anchor="w", pady=(6, 0))

        # --- Action buttons (right side, always visible — top bar!) ---
        btn_col = tk.Frame(inner, bg=COLOR_CARD)
        btn_col.pack(side="right")
        tk.Label(btn_col, text=" ", bg=COLOR_CARD, font=FONT_LABEL).pack(anchor="w")

        btn_row = tk.Frame(btn_col, bg=COLOR_CARD)
        btn_row.pack(pady=(6, 0))

        self.translate_btn = ttk.Button(
            btn_row, text="🌐  Translate", style="Primary.TButton", command=self.on_translate
        )
        self.translate_btn.pack(side="left")

        ttk.Button(btn_row, text="🗑  Clear", style="Clear.TButton",
                   command=self.on_clear).pack(side="left", padx=8)

        ttk.Button(btn_row, text="📋  Copy Translation", style="Copy.TButton",
                   command=self.on_copy).pack(side="left")

    # ---- Text panels ----------------------------------------------------
    def _build_text_panels(self):
        panels = tk.Frame(self, bg=COLOR_BG)
        panels.grid(row=2, column=0, sticky="nsew", padx=16, pady=8)
        panels.columnconfigure(0, weight=1)
        panels.columnconfigure(1, weight=1)
        panels.rowconfigure(0, weight=1)

        # ---- Input panel ----
        input_card = self._card(panels)
        input_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        input_header = tk.Frame(input_card, bg=COLOR_CARD)
        input_header.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(input_header, text="✏️", font=FONT_ICON, bg=COLOR_CARD).pack(side="left")
        tk.Label(input_header, text="Enter Text", font=FONT_LABEL,
                 bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="left", padx=(6, 0))
        self.char_count_var = tk.StringVar(value="0 characters")
        tk.Label(input_header, textvariable=self.char_count_var, font=FONT_STATUS,
                 bg=COLOR_CARD, fg=COLOR_SUBTEXT).pack(side="right")

        self.input_text = tk.Text(
            input_card, wrap="word", font=FONT_TEXT, bg=COLOR_CARD, fg=COLOR_TEXT,
            relief="flat", padx=12, pady=8, insertbackground=COLOR_TEXT,
        )
        self.input_text.pack(fill="both", expand=True, padx=12, pady=(0, 14))
        self.input_text.bind("<KeyRelease>", self._update_char_count)

        # ---- Output panel ----
        output_card = self._card(panels)
        output_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        output_header = tk.Frame(output_card, bg=COLOR_CARD)
        output_header.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(output_header, text="📄", font=FONT_ICON, bg=COLOR_CARD).pack(side="left")
        tk.Label(output_header, text="Translation", font=FONT_LABEL,
                 bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="left", padx=(6, 0))
        tk.Button(
            output_header, text="📋", font=FONT_ICON, bg=COLOR_CARD, bd=0,
            activebackground=COLOR_CARD, cursor="hand2", command=self.on_copy,
        ).pack(side="right")

        # Stack: a placeholder (shown when empty) + the real Text widget on top
        self.output_container = tk.Frame(output_card, bg="#FAFBFF")
        self.output_container.pack(fill="both", expand=True, padx=12, pady=(0, 14))

        self.output_placeholder = tk.Frame(self.output_container, bg="#FAFBFF")
        tk.Label(self.output_placeholder, text="🔤", font=FONT_BIG_ICON,
                 bg="#FAFBFF", fg="#B9C2D9").pack(pady=(40, 6))
        tk.Label(self.output_placeholder, text="Translation will appear here",
                 font=FONT_LABEL, bg="#FAFBFF", fg=COLOR_SUBTEXT,
                 wraplength=220, justify="center").pack()
        tk.Label(self.output_placeholder, text="Enter text and click Translate",
                 font=FONT_STATUS, bg="#FAFBFF", fg="#A8B1C4",
                 wraplength=220, justify="center").pack(pady=(2, 0))

        self.output_text = tk.Text(
            self.output_container, wrap="word", font=FONT_TEXT, bg="#FAFBFF",
            fg=COLOR_TEXT, relief="flat", padx=4, pady=4, state="disabled", bd=0,
        )
        self._show_placeholder()

    def _show_placeholder(self):
        self.output_text.place_forget()
        self.output_placeholder.place(relx=0.5, rely=0.5, anchor="center")

    def _show_output_text(self):
        self.output_placeholder.place_forget()
        self.output_text.place(relx=0, rely=0, relwidth=1, relheight=1)

    # ---- Status bar -------------------------------------------------
    def _build_status_bar(self):
        bar = self._card(self)
        bar.grid(row=3, column=0, sticky="ew", padx=16, pady=(8, 16))

        inner = tk.Frame(bar, bg=COLOR_CARD)
        inner.pack(fill="x", padx=16, pady=8)

        self.status_dot = tk.Label(inner, text="●", font=FONT_STATUS,
                                    bg=COLOR_CARD, fg=COLOR_SUCCESS)
        self.status_dot.pack(side="left")

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(inner, textvariable=self.status_var, font=FONT_STATUS,
                 bg=COLOR_CARD, fg=COLOR_SUBTEXT).pack(side="left", padx=(6, 0))

        tk.Label(inner, text="Powered by Google Translate API   📶", font=FONT_STATUS,
                 bg=COLOR_CARD, fg=COLOR_SUBTEXT).pack(side="right")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _update_char_count(self, event=None):
        count = len(self.input_text.get("1.0", "end-1c"))
        self.char_count_var.set(f"{count} characters")

    def swap_languages(self):
        source = _strip_flag(self.source_lang_var.get())
        target = _strip_flag(self.target_lang_var.get())

        if source == "Auto Detect":
            messagebox.showinfo(
                "Cannot Swap",
                "Please select a specific source language (not 'Auto Detect') before swapping.",
            )
            return

        self.source_lang_var.set(_with_flag(target))
        self.target_lang_var.set(_with_flag(source))

        input_content = self.input_text.get("1.0", "end-1c")
        output_content = self.output_text.get("1.0", "end-1c")
        if output_content.strip():
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", output_content)
            self._set_output_text(input_content)
            self._update_char_count()

    def on_translate(self):
        text = self.input_text.get("1.0", "end-1c")
        source_lang = _strip_flag(self.source_lang_var.get())
        target_lang = _strip_flag(self.target_lang_var.get())

        if not text.strip():
            self._set_status("Please enter some text to translate.", error=True)
            return

        self._set_status("Translating...")
        self.translate_btn.config(state="disabled")

        thread = threading.Thread(
            target=self._run_translation, args=(text, source_lang, target_lang), daemon=True
        )
        thread.start()

    def _run_translation(self, text, source_lang, target_lang):
        try:
            result = translate_text(text, source_lang, target_lang)
            self.after(0, self._on_translation_success, result)
        except TranslationError as exc:
            self.after(0, self._on_translation_error, str(exc))
        except Exception as exc:
            self.after(0, self._on_translation_error, f"Unexpected error: {exc}")

    def _on_translation_success(self, result):
        self._set_output_text(result)
        self._set_status("Translation complete.", success=True)
        self.translate_btn.config(state="normal")

    def _on_translation_error(self, message):
        self._set_output_text("")
        self._set_status(message, error=True)
        self.translate_btn.config(state="normal")

    def on_copy(self):
        translation = self.output_text.get("1.0", "end-1c")
        if not translation.strip():
            self._set_status("Nothing to copy yet — translate some text first.", error=True)
            return
        try:
            pyperclip.copy(translation)
            self._set_status("Translation copied to clipboard.", success=True)
        except Exception:
            self._set_status("Could not access the clipboard on this system.", error=True)

    def on_clear(self):
        self.input_text.delete("1.0", "end")
        self._set_output_text("")
        self._update_char_count()
        self._set_status("Cleared.")

    # ------------------------------------------------------------------
    # Small helpers
    # ------------------------------------------------------------------
    def _set_output_text(self, text):
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", text)
        self.output_text.config(state="disabled")
        if text.strip():
            self._show_output_text()
        else:
            self._show_placeholder()

    def _set_status(self, message, success=False, error=False):
        color = COLOR_SUBTEXT
        dot_color = COLOR_SUCCESS
        if success:
            color = COLOR_SUCCESS
            dot_color = COLOR_SUCCESS
        elif error:
            color = COLOR_ERROR
            dot_color = COLOR_ERROR
        self.status_var.set(message)
        self.status_dot.config(fg=dot_color)
        # find the status message label (second child of the status inner frame)
        for w in self.status_dot.master.winfo_children():
            if isinstance(w, tk.Label) and w is not self.status_dot:
                w.config(fg=color)
                break


def main():
    app = TranslationApp()
    app.mainloop()


if __name__ == "__main__":
    main()
