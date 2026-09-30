"""
dashboard.py
-------------
Logged-in User Dashboard for Transora.

This is a SEPARATE, ADD-ON file — it does not modify translator.py or
main.py in any way (both are byte-for-byte unchanged). It reuses the
same translation function (`translator.translate_text` — the exact
same "API"/logic main.py uses) and the same color/font theme from
main.py, rebuilt as an embeddable panel instead of its own window,
because a sidebar layout needs the translator to live *inside* a
content area rather than be its own top-level window.

WHO SEES THE DASHBOARD
-----------------------
Only LOGGED-IN users. Guests keep using the original, unmodified
`main.py` translator directly (see login.py) — exactly as before,
with no sidebar, no history, no favorites. This matches the project's
own flow: guest data must never mix with any logged-in user's data,
and the simplest way to guarantee that is that guests never touch
the dashboard or its storage at all.

DATA STORAGE (read before a viva/interview!)
-----------------------------------------------
This is a desktop app, not a website, so there is no browser
`localStorage`. Instead, each logged-in user's History and Favorites
are stored in their OWN local JSON file, inside a `data/` folder next
to this script, named after their email
(e.g. `data/samava_example_com.json`). This keeps User A's data
completely separate from User B's data, the same way per-user
localStorage keys would on a website.

This is a prototype storage layer — see the `DataStore` class below.
It's deliberately isolated behind a small set of methods
(`add_history`, `get_recent`, `toggle_favorite`, ...) so it could be
swapped for a real database (SQLite, Firebase, a Flask+Postgres API)
later without changing any of the UI code that calls it.
"""

import json
import os
import re
import threading
import uuid
from datetime import datetime

import tkinter as tk
from tkinter import ttk

import pyperclip

from translator import translate_text, TranslationError
from main import (
    COLOR_BG, COLOR_CARD, COLOR_BORDER, COLOR_TEXT, COLOR_SUBTEXT,
    COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_PRIMARY_SOFT,
    COLOR_GREEN, COLOR_GREEN_SOFT, COLOR_ERROR, COLOR_SUCCESS,
    FONT_TITLE, FONT_SUBTITLE, FONT_LABEL, FONT_TEXT, FONT_BUTTON,
    FONT_STATUS, FONT_ICON, FONT_BIG_ICON,
    LANGUAGE_FLAGS, _with_flag, _strip_flag,
    get_source_language_names, get_target_language_names,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
COLOR_STAR = "#F5A524"  # amber, used only for the favorite star


# ---------------------------------------------------------------------------
# Storage layer — one JSON file per logged-in user.
# ---------------------------------------------------------------------------
def _safe_filename(email: str) -> str:
    """Turn an email into a safe filename, e.g. 'sam@x.com' -> 'sam_x_com.json'."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", email.strip().lower())
    return f"{cleaned}.json"


class DataStore:
    """
    Loads/saves ONE user's history + favorites as a JSON file.
    Every method here is the only place that touches disk — swapping
    this class out for a real database later is a self-contained change.
    """

    def __init__(self, user_email: str):
        self.user_email = user_email
        os.makedirs(DATA_DIR, exist_ok=True)
        self.path = os.path.join(DATA_DIR, _safe_filename(user_email))
        self._data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data.setdefault("history", [])
                    data.setdefault("favorites", [])
                    return data
            except (json.JSONDecodeError, OSError):
                pass  # corrupt/unreadable file -> start fresh rather than crash
        return {"history": [], "favorites": []}

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass  # non-fatal: the app keeps working with in-memory data

    # ---- History ----------------------------------------------------
    def add_history(self, original_text, source_lang, translated_text, target_lang):
        now = datetime.now()
        entry = {
            "id": uuid.uuid4().hex,
            "original_text": original_text,
            "source_lang": source_lang,
            "translated_text": translated_text,
            "target_lang": target_lang,
            "date": now.strftime("%d %B %Y"),
            "time": now.strftime("%I:%M %p"),
        }
        self._data["history"].append(entry)
        self._save()
        return entry

    def get_history(self, query=""):
        """Newest first. Optional case-insensitive text search."""
        items = list(reversed(self._data["history"]))
        if query.strip():
            q = query.strip().lower()
            items = [
                e for e in items
                if q in e["original_text"].lower() or q in e["translated_text"].lower()
            ]
        return items

    def get_recent(self, limit=8):
        return list(reversed(self._data["history"]))[:limit]

    def delete_history_item(self, item_id):
        self._data["history"] = [e for e in self._data["history"] if e["id"] != item_id]
        self._save()

    def clear_history(self):
        self._data["history"] = []
        self._save()

    # ---- Favorites (independent copies, not linked to history ids) ---
    def _find_favorite_index(self, original_text, source_lang, target_lang):
        for i, e in enumerate(self._data["favorites"]):
            if (e["original_text"] == original_text and e["source_lang"] == source_lang
                    and e["target_lang"] == target_lang):
                return i
        return -1

    def is_favorite(self, original_text, source_lang, target_lang):
        return self._find_favorite_index(original_text, source_lang, target_lang) != -1

    def toggle_favorite(self, original_text, source_lang, translated_text, target_lang,
                         date=None, time=None):
        """Returns True if now favorited, False if it was just un-favorited."""
        idx = self._find_favorite_index(original_text, source_lang, target_lang)
        if idx != -1:
            self._data["favorites"].pop(idx)
            self._save()
            return False
        now = datetime.now()
        entry = {
            "id": uuid.uuid4().hex,
            "original_text": original_text,
            "source_lang": source_lang,
            "translated_text": translated_text,
            "target_lang": target_lang,
            "date": date or now.strftime("%d %B %Y"),
            "time": time or now.strftime("%I:%M %p"),
        }
        self._data["favorites"].append(entry)
        self._save()
        return True

    def get_favorites(self):
        return list(reversed(self._data["favorites"]))

    def remove_favorite(self, item_id):
        self._data["favorites"] = [e for e in self._data["favorites"] if e["id"] != item_id]
        self._save()


# ---------------------------------------------------------------------------
# Small reusable widgets
# ---------------------------------------------------------------------------
class ScrollableList(tk.Frame):
    """A vertically scrollable area — used by Recent / History / Favorites."""

    def __init__(self, parent, bg=COLOR_BG):
        super().__init__(parent, bg=bg)
        canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = tk.Frame(canvas, bg=bg)

        self.inner.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()


def _empty_state(parent, icon, message):
    frame = tk.Frame(parent, bg=COLOR_BG)
    tk.Label(frame, text=icon, font=FONT_BIG_ICON, bg=COLOR_BG, fg="#B9C2D9").pack(pady=(60, 8))
    tk.Label(frame, text=message, font=FONT_LABEL, bg=COLOR_BG, fg=COLOR_SUBTEXT).pack()
    return frame


def _record_card(parent, entry, on_copy=None, on_delete=None, on_reuse=None,
                  on_favorite=None, is_favorite=False):
    """One history/recent/favorite item, styled as a small white card."""
    card = tk.Frame(parent, bg=COLOR_CARD, highlightbackground=COLOR_BORDER,
                     highlightthickness=1)
    card.pack(fill="x", padx=4, pady=6)

    top = tk.Frame(card, bg=COLOR_CARD)
    top.pack(fill="x", padx=14, pady=(10, 2))

    lang_line = f"{entry['source_lang']} → {entry['target_lang']}"
    tk.Label(top, text=lang_line, font=FONT_LABEL, bg=COLOR_CARD, fg=COLOR_PRIMARY_DARK).pack(side="left")
    tk.Label(top, text=f"{entry['date']} · {entry['time']}", font=FONT_STATUS,
             bg=COLOR_CARD, fg=COLOR_SUBTEXT).pack(side="right")

    body = tk.Frame(card, bg=COLOR_CARD)
    body.pack(fill="x", padx=14, pady=(2, 8))
    original_preview = entry["original_text"] if len(entry["original_text"]) <= 90 else entry["original_text"][:87] + "..."
    translated_preview = entry["translated_text"] if len(entry["translated_text"]) <= 90 else entry["translated_text"][:87] + "..."
    tk.Label(body, text=original_preview, font=FONT_TEXT, bg=COLOR_CARD, fg=COLOR_TEXT,
             anchor="w", justify="left", wraplength=520).pack(fill="x", anchor="w")
    tk.Label(body, text=translated_preview, font=FONT_TEXT, bg=COLOR_CARD, fg=COLOR_SUBTEXT,
             anchor="w", justify="left", wraplength=520).pack(fill="x", anchor="w", pady=(2, 0))

    actions = tk.Frame(card, bg=COLOR_CARD)
    actions.pack(fill="x", padx=10, pady=(0, 8))

    def icon_btn(text, command, fg=COLOR_TEXT):
        return tk.Button(actions, text=text, font=FONT_ICON, bg=COLOR_CARD, bd=0,
                          fg=fg, activebackground=COLOR_CARD, cursor="hand2", command=command)

    if on_reuse:
        icon_btn("↩ Reuse", on_reuse, fg=COLOR_PRIMARY).pack(side="left", padx=4)
    if on_copy:
        icon_btn("📋 Copy", on_copy).pack(side="left", padx=4)
    if on_favorite:
        star = "★" if is_favorite else "☆"
        icon_btn(f"{star} Favorite", on_favorite, fg=COLOR_STAR if is_favorite else COLOR_SUBTEXT).pack(side="left", padx=4)
    if on_delete:
        icon_btn("🗑 Delete", on_delete, fg=COLOR_ERROR).pack(side="right", padx=4)

    return card


# ---------------------------------------------------------------------------
# Main dashboard window
# ---------------------------------------------------------------------------
class DashboardApp(tk.Tk):
    def __init__(self, user_email: str, user_name: str = None):
        super().__init__()
        self.user_email = user_email
        self.user_name = user_name or user_email.split("@")[0].title()
        self.store = DataStore(user_email)

        self.title("Transora — Dashboard")
        self.geometry("1200x760")
        self.minsize(1020, 640)
        self.configure(bg=COLOR_BG)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # header — fixed, always visible
        self.rowconfigure(1, weight=1)  # body (sidebar + content)

        self.sidebar_collapsed = False

        self._build_header()
        self._build_body()

        self.show_view("Translation")

        # Maximize to fill the laptop screen, same as the Login window.
        self.after(10, self._maximize)

    def _maximize(self):
        try:
            self.state("zoomed")  # Windows / most Linux window managers
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)  # some Linux window managers
            except tk.TclError:
                pass

        # Guaranteed fallback: some window managers accept the call above
        # without error but don't actually resize the window. If it still
        # isn't filling (most of) the screen, force it manually.
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        if self.winfo_width() < screen_w * 0.9 or self.winfo_height() < screen_h * 0.9:
            self.geometry(f"{screen_w}x{screen_h}+0+0")

    # ------------------------------------------------------------------
    def _build_header(self):
        header = tk.Frame(self, bg=COLOR_CARD, highlightbackground=COLOR_BORDER,
                           highlightthickness=1, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        left = tk.Frame(header, bg=COLOR_CARD)
        left.pack(side="left", padx=16, pady=10)
        tk.Label(left, text="🌐", font=FONT_ICON, bg=COLOR_CARD).pack(side="left")
        tk.Label(left, text="Transora", font=FONT_LABEL,
                 bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="left", padx=(6, 0))

        right = tk.Frame(header, bg=COLOR_CARD)
        right.pack(side="right", padx=16, pady=10)
        tk.Label(right, text=f"Hi, {self.user_name}", font=FONT_STATUS,
                 bg=COLOR_CARD, fg=COLOR_SUBTEXT).pack(side="right")

    def _build_body(self):
        body = tk.Frame(self, bg=COLOR_BG)
        body.grid(row=1, column=0, sticky="nsew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)  # only the content column expands

        self.sidebar = tk.Frame(body, bg=COLOR_CARD, width=220,
                                 highlightbackground=COLOR_BORDER, highlightthickness=1)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        self.content_area = tk.Frame(body, bg=COLOR_BG)
        self.content_area.grid(row=0, column=1, sticky="nsew")
        self.content_area.rowconfigure(0, weight=1)
        self.content_area.columnconfigure(0, weight=1)

        self._build_sidebar_contents()

        # The four pages, stacked and swapped with tkraise()
        self.views = {
            "Translation": TranslationView(self.content_area, self),
            "Recent": RecentView(self.content_area, self),
            "History": HistoryView(self.content_area, self),
            "Favorites": FavoritesView(self.content_area, self),
        }
        for view in self.views.values():
            view.grid(row=0, column=0, sticky="nsew")

    def _build_sidebar_contents(self):
        for child in self.sidebar.winfo_children():
            child.destroy()

        toggle_row = tk.Frame(self.sidebar, bg=COLOR_CARD)
        toggle_row.pack(fill="x", pady=(10, 4), padx=8)
        tk.Button(
            toggle_row, text="☰", font=FONT_ICON, bg=COLOR_CARD, bd=0,
            activebackground=COLOR_CARD, cursor="hand2", command=self._toggle_sidebar,
        ).pack(side="right")

        self.nav_buttons = {}
        nav_items = [
            ("Translation", "🌐"),
            ("Recent", "📄"),
            ("History", "🕘"),
            ("Favorites", "⭐"),
        ]
        for name, icon in nav_items:
            label = icon if self.sidebar_collapsed else f"{icon}  {name}"
            btn = tk.Button(
                self.sidebar, text=label, font=FONT_BUTTON, bg=COLOR_CARD, fg=COLOR_TEXT,
                bd=0, anchor="w", padx=16, pady=12, activebackground=COLOR_PRIMARY_SOFT,
                cursor="hand2", command=lambda n=name: self.show_view(n),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self.nav_buttons[name] = btn

        spacer = tk.Frame(self.sidebar, bg=COLOR_CARD)
        spacer.pack(fill="both", expand=True)

        logout_label = "🚪" if self.sidebar_collapsed else "🚪  Logout"
        tk.Button(
            self.sidebar, text=logout_label, font=FONT_BUTTON, bg=COLOR_CARD, fg=COLOR_ERROR,
            bd=0, anchor="w", padx=16, pady=12, activebackground="#FBEAEA",
            cursor="hand2", command=self.on_logout,
        ).pack(fill="x", padx=8, pady=(2, 16), side="bottom")

    def _toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        self.sidebar.config(width=64 if self.sidebar_collapsed else 220)
        self._build_sidebar_contents()
        self._highlight_active_nav()

    # ------------------------------------------------------------------
    def show_view(self, name):
        self.views[name].tkraise()
        if hasattr(self.views[name], "on_show"):
            self.views[name].on_show()
        self._highlight_active_nav(name)

    def _highlight_active_nav(self, active=None):
        active = active or getattr(self, "_active_nav", "Translation")
        self._active_nav = active
        for name, btn in self.nav_buttons.items():
            if name == active:
                btn.config(bg=COLOR_PRIMARY_SOFT, fg=COLOR_PRIMARY_DARK)
            else:
                btn.config(bg=COLOR_CARD, fg=COLOR_TEXT)

    def on_logout(self):
        self.destroy()
        from login import LoginApp  # deferred import avoids a circular import
        LoginApp().mainloop()

    def refresh_all_lists(self):
        """Called after any add/delete so every view reflects the latest data."""
        self.views["Recent"].refresh()
        self.views["History"].refresh()
        self.views["Favorites"].refresh()


# ---------------------------------------------------------------------------
# View: Translation (the actual translator, embedded — same logic as main.py)
# ---------------------------------------------------------------------------
class TranslationView(tk.Frame):
    def __init__(self, parent, app: DashboardApp):
        super().__init__(parent, bg=COLOR_BG)
        self.app = app
        self.current_entry = None  # the history entry for the last successful translation

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # control bar — always visible
        self.rowconfigure(1, weight=1)  # text panels

        self._build_control_bar()
        self._build_text_panels()

    def _build_control_bar(self):
        bar = tk.Frame(self, bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        bar.grid(row=0, column=0, sticky="ew", padx=16, pady=16)

        inner = tk.Frame(bar, bg=COLOR_CARD)
        inner.pack(fill="x", padx=16, pady=14)

        src_col = tk.Frame(inner, bg=COLOR_CARD)
        src_col.pack(side="left")
        tk.Label(src_col, text="Source Language", font=FONT_LABEL, bg=COLOR_CARD, fg=COLOR_TEXT).pack(anchor="w")
        self.source_lang_var = tk.StringVar(value=_with_flag("English"))
        ttk.Combobox(src_col, textvariable=self.source_lang_var,
                     values=[_with_flag(n) for n in get_source_language_names()],
                     state="readonly", font=FONT_TEXT, width=13).pack(anchor="w", pady=(6, 0))

        swap_col = tk.Frame(inner, bg=COLOR_CARD)
        swap_col.pack(side="left", padx=12)
        tk.Label(swap_col, text=" ", bg=COLOR_CARD, font=FONT_LABEL).pack(anchor="w")
        tk.Button(swap_col, text="⇄ Swap", font=FONT_BUTTON, bg=COLOR_PRIMARY_SOFT,
                  fg=COLOR_PRIMARY, bd=0, padx=10, pady=8, cursor="hand2",
                  command=self.swap_languages).pack(pady=(6, 0))

        tgt_col = tk.Frame(inner, bg=COLOR_CARD)
        tgt_col.pack(side="left")
        tk.Label(tgt_col, text="Target Language", font=FONT_LABEL, bg=COLOR_CARD, fg=COLOR_TEXT).pack(anchor="w")
        self.target_lang_var = tk.StringVar(value=_with_flag("Urdu"))
        ttk.Combobox(tgt_col, textvariable=self.target_lang_var,
                     values=[_with_flag(n) for n in get_target_language_names()],
                     state="readonly", font=FONT_TEXT, width=13).pack(anchor="w", pady=(6, 0))

        btn_col = tk.Frame(inner, bg=COLOR_CARD)
        btn_col.pack(side="right")
        tk.Label(btn_col, text=" ", bg=COLOR_CARD, font=FONT_LABEL).pack(anchor="w")
        btn_row = tk.Frame(btn_col, bg=COLOR_CARD)
        btn_row.pack(pady=(6, 0))

        self.translate_btn = tk.Button(
            btn_row, text="🌐 Translate", font=FONT_BUTTON, bg=COLOR_PRIMARY, fg="white",
            bd=0, padx=14, pady=9, cursor="hand2", command=self.on_translate,
        )
        self.translate_btn.pack(side="left")
        tk.Button(btn_row, text="🗑 Clear", font=FONT_BUTTON, bg=COLOR_CARD, fg=COLOR_TEXT,
                  highlightbackground=COLOR_BORDER, highlightthickness=1, bd=0, padx=12, pady=9,
                  cursor="hand2", command=self.on_clear).pack(side="left", padx=8)
        tk.Button(btn_row, text="📋 Copy Translation", font=FONT_BUTTON, bg=COLOR_CARD, fg=COLOR_GREEN,
                  highlightbackground=COLOR_BORDER, highlightthickness=1, bd=0, padx=12, pady=9,
                  cursor="hand2", command=self.on_copy).pack(side="left", padx=(0, 8))
        self.favorite_btn = tk.Button(
            btn_row, text="☆ Favorite", font=FONT_BUTTON, bg=COLOR_CARD, fg=COLOR_SUBTEXT,
            highlightbackground=COLOR_BORDER, highlightthickness=1, bd=0, padx=12, pady=9,
            cursor="hand2", command=self.on_toggle_favorite, state="disabled",
        )
        self.favorite_btn.pack(side="left")

    def _build_text_panels(self):
        panels = tk.Frame(self, bg=COLOR_BG)
        panels.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        panels.columnconfigure(0, weight=1)
        panels.columnconfigure(1, weight=1)
        panels.rowconfigure(0, weight=1)

        input_card = tk.Frame(panels, bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        input_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        head = tk.Frame(input_card, bg=COLOR_CARD)
        head.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(head, text="✏️ Enter Text", font=FONT_LABEL, bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="left")
        self.char_count_var = tk.StringVar(value="0 characters")
        tk.Label(head, textvariable=self.char_count_var, font=FONT_STATUS, bg=COLOR_CARD, fg=COLOR_SUBTEXT).pack(side="right")
        self.input_text = tk.Text(input_card, wrap="word", font=FONT_TEXT, bg=COLOR_CARD,
                                   fg=COLOR_TEXT, relief="flat", padx=12, pady=8)
        self.input_text.pack(fill="both", expand=True, padx=12, pady=(0, 14))
        self.input_text.bind("<KeyRelease>", self._update_char_count)

        output_card = tk.Frame(panels, bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        output_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ohead = tk.Frame(output_card, bg=COLOR_CARD)
        ohead.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(ohead, text="📄 Translation", font=FONT_LABEL, bg=COLOR_CARD, fg=COLOR_TEXT).pack(side="left")

        self.output_text = tk.Text(output_card, wrap="word", font=FONT_TEXT, bg="#FAFBFF",
                                    fg=COLOR_TEXT, relief="flat", padx=12, pady=8, state="disabled")
        self.output_text.pack(fill="both", expand=True, padx=12, pady=(0, 14))

        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(self, textvariable=self.status_var, font=FONT_STATUS,
                                      bg=COLOR_BG, fg=COLOR_SUBTEXT)
        self.status_label.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 10))

    # ---- behaviour: identical translation flow to main.py ---------------
    def _update_char_count(self, event=None):
        count = len(self.input_text.get("1.0", "end-1c"))
        self.char_count_var.set(f"{count} characters")

    def swap_languages(self):
        source = _strip_flag(self.source_lang_var.get())
        target = _strip_flag(self.target_lang_var.get())
        if source == "Auto Detect":
            return
        self.source_lang_var.set(_with_flag(target))
        self.target_lang_var.set(_with_flag(source))

    def on_translate(self):
        text = self.input_text.get("1.0", "end-1c")
        source_lang = _strip_flag(self.source_lang_var.get())
        target_lang = _strip_flag(self.target_lang_var.get())
        if not text.strip():
            self._set_status("Please enter some text to translate.", error=True)
            return
        self._set_status("Translating...")
        self.translate_btn.config(state="disabled")
        threading.Thread(target=self._run_translation, args=(text, source_lang, target_lang), daemon=True).start()

    def _run_translation(self, text, source_lang, target_lang):
        try:
            result = translate_text(text, source_lang, target_lang)
            self.after(0, self._on_success, text.strip(), source_lang, result, target_lang)
        except TranslationError as exc:
            self.after(0, self._on_error, str(exc))
        except Exception as exc:
            self.after(0, self._on_error, f"Unexpected error: {exc}")

    def _on_success(self, original_text, source_lang, translated_text, target_lang):
        self._set_output_text(translated_text)
        self._set_status("Translation complete.", success=True)
        self.translate_btn.config(state="normal")

        # Save to this logged-in user's history (guests never reach this view).
        entry = self.app.store.add_history(original_text, source_lang, translated_text, target_lang)
        self.current_entry = entry
        self.favorite_btn.config(state="normal")
        self._refresh_favorite_button()
        self.app.refresh_all_lists()

    def _on_error(self, message):
        self._set_output_text("")
        self._set_status(message, error=True)
        self.translate_btn.config(state="normal")

    def on_copy(self):
        text = self.output_text.get("1.0", "end-1c")
        if not text.strip():
            self._set_status("Nothing to copy yet — translate some text first.", error=True)
            return
        try:
            pyperclip.copy(text)
            self._set_status("Translation copied to clipboard.", success=True)
        except Exception:
            self._set_status("Could not access the clipboard on this system.", error=True)

    def on_clear(self):
        self.input_text.delete("1.0", "end")
        self._set_output_text("")
        self._update_char_count()
        self._set_status("Cleared.")
        self.current_entry = None
        self.favorite_btn.config(state="disabled", text="☆ Favorite", fg=COLOR_SUBTEXT)

    def on_toggle_favorite(self):
        if not self.current_entry:
            return
        e = self.current_entry
        now_favorite = self.app.store.toggle_favorite(
            e["original_text"], e["source_lang"], e["translated_text"], e["target_lang"],
            date=e["date"], time=e["time"],
        )
        self._refresh_favorite_button(now_favorite)
        self.app.refresh_all_lists()

    def _refresh_favorite_button(self, is_fav=None):
        if not self.current_entry:
            return
        e = self.current_entry
        if is_fav is None:
            is_fav = self.app.store.is_favorite(e["original_text"], e["source_lang"], e["target_lang"])
        if is_fav:
            self.favorite_btn.config(text="★ Favorited", fg=COLOR_STAR)
        else:
            self.favorite_btn.config(text="☆ Favorite", fg=COLOR_SUBTEXT)

    def load_entry(self, entry):
        """Used by History/Recent 'Reuse' buttons to bring a past translation back."""
        self.source_lang_var.set(_with_flag(entry["source_lang"]))
        self.target_lang_var.set(_with_flag(entry["target_lang"]))
        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", entry["original_text"])
        self._update_char_count()
        self._set_output_text(entry["translated_text"])
        self.current_entry = entry
        self.favorite_btn.config(state="normal")
        self._refresh_favorite_button()
        self._set_status("Loaded from your saved translations.")

    def _set_output_text(self, text):
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", text)
        self.output_text.config(state="disabled")

    def _set_status(self, message, success=False, error=False):
        color = COLOR_SUBTEXT
        if success:
            color = COLOR_SUCCESS
        elif error:
            color = COLOR_ERROR
        self.status_var.set(message)
        self.status_label.config(fg=color)


# ---------------------------------------------------------------------------
# View: Recent Translated Files
# ---------------------------------------------------------------------------
class RecentView(tk.Frame):
    def __init__(self, parent, app: DashboardApp):
        super().__init__(parent, bg=COLOR_BG)
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=COLOR_BG)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        tk.Label(header, text="📄 Recent Translated Files", font=FONT_TITLE, bg=COLOR_BG, fg=COLOR_TEXT).pack(anchor="w")
        tk.Label(header, text="Your latest translations, newest first.", font=FONT_SUBTITLE,
                 bg=COLOR_BG, fg=COLOR_SUBTEXT).pack(anchor="w")

        self.list_area = ScrollableList(self)
        self.list_area.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

    def on_show(self):
        self.refresh()

    def refresh(self):
        self.list_area.clear()
        items = self.app.store.get_recent(limit=8)
        if not items:
            _empty_state(self.list_area.inner, "📄", "No recent translations yet.").pack(fill="both", expand=True)
            return
        for entry in items:
            self._add_card(entry)

    def _add_card(self, entry):
        is_fav = self.app.store.is_favorite(entry["original_text"], entry["source_lang"], entry["target_lang"])

        def do_copy():
            pyperclip.copy(entry["translated_text"])

        def do_delete():
            self.app.store.delete_history_item(entry["id"])
            self.app.refresh_all_lists()

        def do_reuse():
            self.app.views["Translation"].load_entry(entry)
            self.app.show_view("Translation")

        _record_card(self.list_area.inner, entry, on_copy=do_copy, on_delete=do_delete,
                     on_reuse=do_reuse)


# ---------------------------------------------------------------------------
# View: History (search + delete + clear all)
# ---------------------------------------------------------------------------
class HistoryView(tk.Frame):
    def __init__(self, parent, app: DashboardApp):
        super().__init__(parent, bg=COLOR_BG)
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = tk.Frame(self, bg=COLOR_BG)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        tk.Label(header, text="🕘 Translation History", font=FONT_TITLE, bg=COLOR_BG, fg=COLOR_TEXT).pack(anchor="w")

        toolbar = tk.Frame(self, bg=COLOR_BG)
        toolbar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(toolbar, textvariable=self.search_var, font=FONT_TEXT,
                                 relief="flat", highlightbackground=COLOR_BORDER,
                                 highlightthickness=1, bg=COLOR_CARD)
        search_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        search_entry.bind("<KeyRelease>", lambda e: self.refresh())
        tk.Label(toolbar, text="🔍", font=FONT_ICON, bg=COLOR_BG).pack(side="left", padx=(0, 12))

        tk.Button(toolbar, text="Clear All", font=FONT_BUTTON, bg=COLOR_CARD, fg=COLOR_ERROR,
                  highlightbackground=COLOR_BORDER, highlightthickness=1, bd=0, padx=12, pady=6,
                  cursor="hand2", command=self.on_clear_all).pack(side="right")

        self.list_area = ScrollableList(self)
        self.list_area.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))

    def on_show(self):
        self.refresh()

    def refresh(self):
        self.list_area.clear()
        items = self.app.store.get_history(query=self.search_var.get())
        if not items:
            msg = "No translation history yet." if not self.search_var.get().strip() else "No matches found."
            _empty_state(self.list_area.inner, "🕘", msg).pack(fill="both", expand=True)
            return
        for entry in items:
            self._add_card(entry)

    def _add_card(self, entry):
        def do_copy():
            pyperclip.copy(entry["translated_text"])

        def do_delete():
            self.app.store.delete_history_item(entry["id"])
            self.app.refresh_all_lists()

        def do_reuse():
            self.app.views["Translation"].load_entry(entry)
            self.app.show_view("Translation")

        _record_card(self.list_area.inner, entry, on_copy=do_copy, on_delete=do_delete,
                     on_reuse=do_reuse)

    def on_clear_all(self):
        self.app.store.clear_history()
        self.app.refresh_all_lists()


# ---------------------------------------------------------------------------
# View: Favorites
# ---------------------------------------------------------------------------
class FavoritesView(tk.Frame):
    def __init__(self, parent, app: DashboardApp):
        super().__init__(parent, bg=COLOR_BG)
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=COLOR_BG)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        tk.Label(header, text="⭐ Favorites", font=FONT_TITLE, bg=COLOR_BG, fg=COLOR_TEXT).pack(anchor="w")
        tk.Label(header, text="Translations you've starred for quick access.", font=FONT_SUBTITLE,
                 bg=COLOR_BG, fg=COLOR_SUBTEXT).pack(anchor="w")

        self.list_area = ScrollableList(self)
        self.list_area.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

    def on_show(self):
        self.refresh()

    def refresh(self):
        self.list_area.clear()
        items = self.app.store.get_favorites()
        if not items:
            _empty_state(self.list_area.inner, "⭐", "No favorites yet.").pack(fill="both", expand=True)
            return
        for entry in items:
            self._add_card(entry)

    def _add_card(self, entry):
        def do_copy():
            pyperclip.copy(entry["translated_text"])

        def do_remove():
            self.app.store.remove_favorite(entry["id"])
            self.app.refresh_all_lists()

        def do_reuse():
            self.app.views["Translation"].load_entry(entry)
            self.app.show_view("Translation")

        _record_card(self.list_area.inner, entry, on_copy=do_copy, on_delete=do_remove,
                     on_reuse=do_reuse)


def main(user_email="guest_preview@example.com", user_name=None):
    app = DashboardApp(user_email, user_name)
    app.mainloop()


if __name__ == "__main__":
    # Running this file directly opens a preview dashboard for testing.
    main()
