"""
login.py
---------
Login / Welcome screen for Transora.

This is a SEPARATE, ADD-ON file — it does not modify, redesign, or
touch translator.py or main.py in any way. The existing translator
keeps working exactly as before if you run `python main.py` directly.

Run THIS file instead to get the new Login -> Guest Mode flow:

    python login.py

Flow:
    Welcome screen -> [Continue as Guest] -> opens the existing
    Translation Dashboard (main.py's TranslationApp) directly.
    Welcome screen -> [Login] -> Login form -> (demo success) ->
    opens the existing Translation Dashboard.
    Welcome screen -> [Sign Up] -> Signup form -> (demo success) ->
    back to Login with a success message.

NOTE ON AUTHENTICATION (read this before a viva/interview!)
-----------------------------------------------------------
This is an internship/portfolio prototype. There is NO real backend
or account database yet. Login and Sign Up here only validate the
*format* of what you type (a valid-looking email, matching
passwords, a minimum password length) as a demo — no password is
saved anywhere, and no real account is created.

The code is deliberately split into small, isolated functions
(`_validate_login`, `_validate_signup`) so that a real backend
(Firebase Auth, a Flask/Express + JWT API, a local SQLite users
table, etc.) could replace just those two functions later without
touching any of the UI code.
"""

import re
import tkinter as tk
from tkinter import ttk

from main import (
    TranslationApp,
    COLOR_BG, COLOR_CARD, COLOR_BORDER, COLOR_TEXT, COLOR_SUBTEXT,
    COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_PRIMARY_SOFT,
    COLOR_GREEN, COLOR_ERROR, COLOR_SUCCESS,
    FONT_TITLE, FONT_SUBTITLE, FONT_TAGLINE, FONT_LABEL,
    FONT_TEXT, FONT_BUTTON, FONT_STATUS,
)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 6

# Bigger versions of the shared theme fonts, used only on these login/signup
# screens so they feel proportionate on a full laptop screen instead of
# looking like a small mobile widget floating in empty space.
BIG_FONT_TITLE = ("Segoe UI", 28, "bold")
BIG_FONT_SUBTITLE = ("Segoe UI", 13)
BIG_FONT_LABEL = ("Segoe UI", 12, "bold")
BIG_FONT_TEXT = ("Segoe UI", 13)
BIG_FONT_BUTTON = ("Segoe UI", 13, "bold")
BIG_FONT_STATUS = ("Segoe UI", 11)


# ---------------------------------------------------------------------------
# Demo "authentication" — format validation only. See module docstring.
# ---------------------------------------------------------------------------
def _validate_login(email: str, password: str):
    """Returns (is_valid, message)."""
    if not email.strip() or not password.strip():
        return False, "Please enter both email/username and password."
    if not EMAIL_PATTERN.match(email.strip()) and "@" in email:
        # Looks like they tried an email but got the format wrong.
        return False, "Please enter a valid email address."
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    return True, "Login successful! Opening translator..."


def _validate_signup(full_name: str, email: str, password: str, confirm: str):
    """Returns (is_valid, message)."""
    if not full_name.strip():
        return False, "Please enter your full name."
    if not EMAIL_PATTERN.match(email.strip()):
        return False, "Please enter a valid email address."
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if password != confirm:
        return False, "Passwords do not match."
    return True, "Account created! Please log in."


class LoginApp(tk.Tk):
    """Welcome / Login / Sign Up window, styled to match the translator."""

    def __init__(self):
        super().__init__()
        self.title("Transora — Login")
        self.geometry("1200x800")
        self.minsize(900, 700)
        self.configure(bg=COLOR_BG)

        self._configure_styles()

        # A single container holds all three screens stacked on top of
        # each other; only one is raised (visible) at a time.
        container = tk.Frame(self, bg=COLOR_BG)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        self.frames = {}
        for FrameClass in (WelcomeFrame, LoginFrame, SignupFrame):
            frame = FrameClass(container, self)
            self.frames[FrameClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("WelcomeFrame")

        # Maximize to fill the laptop screen. Done last, and via .after(),
        # so it applies after the window is fully built on every platform.
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

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "Primary.TButton",
            font=BIG_FONT_BUTTON, foreground="white", background=COLOR_PRIMARY,
            padding=(18, 14), borderwidth=0,
        )
        style.map("Primary.TButton", background=[("active", COLOR_PRIMARY_DARK)])

        style.configure(
            "Secondary.TButton",
            font=BIG_FONT_BUTTON, foreground=COLOR_PRIMARY, background=COLOR_PRIMARY_SOFT,
            padding=(18, 14), borderwidth=0,
        )
        style.map("Secondary.TButton", background=[("active", "#DCE7FF")])

        style.configure(
            "Ghost.TButton",
            font=BIG_FONT_BUTTON, foreground=COLOR_TEXT, background=COLOR_CARD,
            padding=(18, 14), borderwidth=1,
        )
        style.map("Ghost.TButton", background=[("active", "#F3F5FA")])

    def show_frame(self, name):
        self.frames[name].tkraise()
        if hasattr(self.frames[name], "on_show"):
            self.frames[name].on_show()

    def launch_translator(self):
        """Close the login window and open the existing translator, unchanged."""
        self.destroy()
        app = TranslationApp()
        app.mainloop()

    def launch_dashboard(self, user_email: str):
        """Close the login window and open the logged-in user's Dashboard
        (sidebar + Translation + Recent + History + Favorites)."""
        self.destroy()
        from dashboard import DashboardApp  # deferred import avoids a circular import
        app = DashboardApp(user_email=user_email)
        app.mainloop()


# ---------------------------------------------------------------------------
# Shared little helpers used by more than one screen
# ---------------------------------------------------------------------------
def _card(parent, content_width=560):
    """
    A vertically SCROLLABLE, full-window white area. Content that's
    taller than the screen (e.g. a long Signup form on a small laptop
    screen) is reachable by scrolling instead of the last button
    getting pushed off-screen. The actual form controls live in a
    fixed-width column centered inside it, so fields stay readable
    instead of stretching edge-to-edge on a wide screen.
    """
    outer = tk.Frame(parent, bg=COLOR_CARD)

    canvas = tk.Canvas(outer, bg=COLOR_CARD, highlightthickness=0)
    scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    inner = tk.Frame(canvas, bg=COLOR_CARD)
    inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")

    card = tk.Frame(inner, bg=COLOR_CARD, width=content_width)
    card.pack(expand=True, pady=20)

    def _sync_scrollregion(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _sync_width(event):
        canvas.itemconfig(inner_window, width=event.width)

    inner.bind("<Configure>", _sync_scrollregion)
    canvas.bind("<Configure>", _sync_width)

    def _on_mousewheel(event):
        if canvas.winfo_exists() and canvas.winfo_ismapped():
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")

    return outer, card

def _logo_badge(parent):
    badge = tk.Frame(parent, bg=COLOR_CARD)
    badge.pack(pady=(38, 6))
    circle = tk.Canvas(badge, width=96, height=96, bg=COLOR_CARD, highlightthickness=0)
    circle.pack()
    circle.create_oval(2, 2, 94, 94, fill=COLOR_PRIMARY, outline="")
    circle.create_text(48, 48, text="🌐", font=("Segoe UI Emoji", 36), fill="white")


def _password_field(parent, label_text):
    """
    Returns (wrapper_frame, StringVar, entry_widget).
    Includes a show/hide (👁 / 🙈) toggle button next to the field.
    """
    wrapper = tk.Frame(parent, bg=COLOR_CARD)
    tk.Label(wrapper, text=label_text, font=BIG_FONT_LABEL, bg=COLOR_CARD,
              fg=COLOR_TEXT).pack(anchor="w")

    row = tk.Frame(wrapper, bg=COLOR_CARD, highlightbackground=COLOR_BORDER,
                    highlightthickness=1)
    row.pack(fill="x", pady=(6, 0))

    var = tk.StringVar()
    entry = tk.Entry(row, textvariable=var, font=BIG_FONT_TEXT, relief="flat",
                      bg=COLOR_CARD, fg=COLOR_TEXT, show="•", bd=0)
    entry.pack(side="left", fill="x", expand=True, ipady=12, padx=(12, 0))

    state = {"visible": False}

    def toggle():
        state["visible"] = not state["visible"]
        entry.config(show="" if state["visible"] else "•")
        toggle_btn.config(text="🙈" if state["visible"] else "👁")

    toggle_btn = tk.Button(row, text="👁", font=BIG_FONT_STATUS, bg=COLOR_CARD, bd=0,
                            activebackground=COLOR_CARD, cursor="hand2", command=toggle)
    toggle_btn.pack(side="right", padx=6)

    return wrapper, var, entry


def _text_field(parent, label_text):
    wrapper = tk.Frame(parent, bg=COLOR_CARD)
    tk.Label(wrapper, text=label_text, font=BIG_FONT_LABEL, bg=COLOR_CARD,
              fg=COLOR_TEXT).pack(anchor="w")
    var = tk.StringVar()
    entry = tk.Entry(wrapper, textvariable=var, font=BIG_FONT_TEXT, relief="flat",
                      bg=COLOR_CARD, fg=COLOR_TEXT, bd=0,
                      highlightbackground=COLOR_BORDER, highlightthickness=1)
    entry.pack(fill="x", pady=(6, 0), ipady=12)
    return wrapper, var, entry


def _clickable_label(parent, text, command, color=None):
    lbl = tk.Label(parent, text=text, font=BIG_FONT_STATUS, bg=COLOR_CARD,
                    fg=color or COLOR_PRIMARY, cursor="hand2")
    lbl.bind("<Button-1>", lambda e: command())
    return lbl


def _back_button(card, command):
    """A small '← Back' link pinned to the top-left of a card."""
    top_bar = tk.Frame(card, bg=COLOR_CARD)
    top_bar.pack(fill="x", padx=24, pady=(18, 0))
    tk.Button(
        top_bar, text="← Back", font=BIG_FONT_STATUS, bg=COLOR_CARD, fg=COLOR_PRIMARY,
        bd=0, cursor="hand2", activebackground=COLOR_CARD, activeforeground=COLOR_PRIMARY_DARK,
        command=command,
    ).pack(side="left")


# ---------------------------------------------------------------------------
# Screen 1: Welcome / landing screen
# ---------------------------------------------------------------------------
class WelcomeFrame(tk.Frame):
    def __init__(self, parent, controller: LoginApp):
        super().__init__(parent, bg=COLOR_BG)
        self.controller = controller

        outer, card = _card(self)
        outer.pack(fill="both", expand=True)

        _logo_badge(card)

        tk.Label(card, text="Transora", font=BIG_FONT_TITLE,
                 bg=COLOR_CARD, fg=COLOR_TEXT).pack(pady=(10, 4), padx=50)
        tk.Label(
            card, text="Translate. Connect. Communicate.",
            font=BIG_FONT_SUBTITLE, bg=COLOR_CARD, fg=COLOR_SUBTEXT, justify="center",
        ).pack(pady=(0, 34), padx=40)

        btn_area = tk.Frame(card, bg=COLOR_CARD)
        btn_area.pack(fill="x", padx=56, pady=(0, 42))

        ttk.Button(btn_area, text="Log In", style="Primary.TButton",
                   command=lambda: controller.show_frame("LoginFrame")).pack(fill="x")
        ttk.Button(btn_area, text="Sign Up", style="Secondary.TButton",
                   command=lambda: controller.show_frame("SignupFrame")).pack(fill="x", pady=12)
        ttk.Button(btn_area, text="Continue as Guest", style="Ghost.TButton",
                   command=controller.launch_translator).pack(fill="x")


# ---------------------------------------------------------------------------
# Screen 2: Login
# ---------------------------------------------------------------------------
class LoginFrame(tk.Frame):
    def __init__(self, parent, controller: LoginApp):
        super().__init__(parent, bg=COLOR_BG)
        self.controller = controller

        outer, card = _card(self)
        outer.pack(fill="both", expand=True)

        _back_button(card, lambda: controller.show_frame("WelcomeFrame"))
        _logo_badge(card)
        tk.Label(card, text="Welcome to Transora", font=BIG_FONT_TITLE, bg=COLOR_CARD,
                 fg=COLOR_TEXT).pack(pady=(6, 4))
        tk.Label(card, text="Log in to continue translating.", font=BIG_FONT_SUBTITLE,
                 bg=COLOR_CARD, fg=COLOR_SUBTEXT).pack(pady=(0, 28))

        form = tk.Frame(card, bg=COLOR_CARD)
        form.pack(fill="x", padx=56)

        email_wrap, self.email_var, _ = _text_field(form, "Email / Username")
        email_wrap.pack(fill="x", pady=(0, 16))

        pwd_wrap, self.password_var, _ = _password_field(form, "Password")
        pwd_wrap.pack(fill="x")

        options_row = tk.Frame(form, bg=COLOR_CARD)
        options_row.pack(fill="x", pady=(12, 6))
        self.remember_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            options_row, text="Remember me", variable=self.remember_var,
            font=BIG_FONT_STATUS, bg=COLOR_CARD, fg=COLOR_SUBTEXT,
            activebackground=COLOR_CARD, selectcolor=COLOR_CARD, bd=0,
        ).pack(side="left")

        self.message_var = tk.StringVar(value="")
        self.message_label = tk.Label(
            form, textvariable=self.message_var, font=BIG_FONT_STATUS,
            bg=COLOR_CARD, fg=COLOR_ERROR, wraplength=440, justify="left",
        )
        self.message_label.pack(fill="x", pady=(4, 12), anchor="w")

        ttk.Button(form, text="Login", style="Primary.TButton",
                   command=self.on_login).pack(fill="x")
        ttk.Button(form, text="Continue as Guest", style="Ghost.TButton",
                   command=controller.launch_translator).pack(fill="x", pady=12)

        signup_row = tk.Frame(card, bg=COLOR_CARD)
        signup_row.pack(pady=(0, 34))
        tk.Label(signup_row, text="Don't have an account?", font=BIG_FONT_STATUS,
                 bg=COLOR_CARD, fg=COLOR_SUBTEXT).pack(side="left")
        _clickable_label(
            signup_row, "  Sign Up", lambda: controller.show_frame("SignupFrame")
        ).pack(side="left")

    def on_show(self):
        self.message_var.set("")

    def on_login(self):
        is_valid, message = _validate_login(self.email_var.get(), self.password_var.get())
        if is_valid:
            self.message_label.config(fg=COLOR_SUCCESS)
            self.message_var.set(message)
            email = self.email_var.get().strip()
            self.after(600, lambda: self.controller.launch_dashboard(email))
        else:
            self.message_label.config(fg=COLOR_ERROR)
            self.message_var.set(message)


# ---------------------------------------------------------------------------
# Screen 3: Sign Up
# ---------------------------------------------------------------------------
class SignupFrame(tk.Frame):
    def __init__(self, parent, controller: LoginApp):
        super().__init__(parent, bg=COLOR_BG)
        self.controller = controller

        outer, card = _card(self)
        outer.pack(fill="both", expand=True)

        _back_button(card, lambda: controller.show_frame("WelcomeFrame"))
        _logo_badge(card)
        tk.Label(card, text="Create Account", font=BIG_FONT_TITLE, bg=COLOR_CARD,
                 fg=COLOR_TEXT).pack(pady=(6, 4))
        tk.Label(card, text="Sign up to save your translation history.",
                 font=BIG_FONT_SUBTITLE, bg=COLOR_CARD, fg=COLOR_SUBTEXT).pack(pady=(0, 24))

        form = tk.Frame(card, bg=COLOR_CARD)
        form.pack(fill="x", padx=56)

        name_wrap, self.name_var, _ = _text_field(form, "Full Name")
        name_wrap.pack(fill="x", pady=(0, 14))

        email_wrap, self.email_var, _ = _text_field(form, "Email")
        email_wrap.pack(fill="x", pady=(0, 14))

        pwd_wrap, self.password_var, _ = _password_field(form, "Password")
        pwd_wrap.pack(fill="x", pady=(0, 14))

        confirm_wrap, self.confirm_var, _ = _password_field(form, "Confirm Password")
        confirm_wrap.pack(fill="x")

        self.message_var = tk.StringVar(value="")
        self.message_label = tk.Label(
            form, textvariable=self.message_var, font=BIG_FONT_STATUS,
            bg=COLOR_CARD, fg=COLOR_ERROR, wraplength=440, justify="left",
        )
        self.message_label.pack(fill="x", pady=(12, 12), anchor="w")

        ttk.Button(form, text="Create Account", style="Primary.TButton",
                   command=self.on_signup).pack(fill="x")
        ttk.Button(form, text="Back to Login", style="Ghost.TButton",
                   command=lambda: controller.show_frame("LoginFrame")).pack(fill="x", pady=(12, 34))

    def on_show(self):
        self.message_var.set("")

    def on_signup(self):
        is_valid, message = _validate_signup(
            self.name_var.get(), self.email_var.get(),
            self.password_var.get(), self.confirm_var.get(),
        )
        if is_valid:
            self.message_label.config(fg=COLOR_SUCCESS)
            self.message_var.set(message)
            login_frame = self.controller.frames["LoginFrame"]
            login_frame.email_var.set(self.email_var.get())
            self.after(700, lambda: self.controller.show_frame("LoginFrame"))
        else:
            self.message_label.config(fg=COLOR_ERROR)
            self.message_var.set(message)


def main():
    app = LoginApp()
    app.mainloop()


if __name__ == "__main__":
    main()
