import json
import random
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tkinter import filedialog
from datetime import datetime
from pathlib import Path

from chatbot import FAQChatbot


# ---------------------------------------------------------------------------
# Forest Green & Cream theme
# ---------------------------------------------------------------------------
BG = "#F5F0E6"            # cream background
CARD = "#FFFDF8"          # near-white cream card
PRIMARY = "#1F5C43"       # forest green
PRIMARY_DARK = "#174935"  # darker forest green
ACCENT = "#C9A24B"        # muted gold accent
TEXT = "#22331F"          # deep green-charcoal text
MUTED = "#7A8B7F"         # muted sage gray
USER_BG = "#E4EEE0"       # soft sage bubble
BOT_BG = "#F3ECD8"        # warm cream bubble
SIDEBAR_BG = "#E9E2CF"    # deeper cream for sidebar
BORDER = "#DED3B4"
SUCCESS = "#2F9E5C"
WARNING = "#B98A2D"
ERROR = "#B3402E"

BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = BASE_DIR / "assets" / "icon.png"

DEFAULT_SUGGESTION_POOL = [
    "How can I apply for admission?",
    "How can I check my grades?",
    "How can I check my attendance?",
    "How do I pay my semester fee?",
    "How can I get a library card?",
    "Who do I contact for IT support?",
    "What is the exam retake policy?",
    "How do I request an official transcript?",
]

MAX_INPUT_CHARS = 300


class SplashScreen(tk.Toplevel):
    """A short, branded loading screen shown while the chatbot model loads."""

    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(bg=PRIMARY)

        width, height = 420, 260
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        tk.Label(
            self, text="🤖", font=("Segoe UI", 42), fg=CARD, bg=PRIMARY
        ).pack(pady=(38, 6))

        tk.Label(
            self, text="Smart FAQ Chatbot", font=("Segoe UI", 17, "bold"),
            fg="white", bg=PRIMARY
        ).pack()

        tk.Label(
            self, text="CodeAlpha AI Internship — Task 2",
            font=("Segoe UI", 9), fg="#D9E8DE", bg=PRIMARY
        ).pack(pady=(2, 18))

        self.progress = ttk.Progressbar(
            self, mode="indeterminate", length=280
        )
        self.progress.pack()
        self.progress.start(12)

        tk.Label(
            self, text="Loading NLP model...", font=("Segoe UI", 8),
            fg="#D9E8DE", bg=PRIMARY
        ).pack(pady=(10, 0))


class FAQChatbotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()

        self.title("Smart FAQ Chatbot | CodeAlpha AI Internship")
        self.geometry("1150x740")
        self.minsize(900, 640)
        self.configure(bg=BG)

        self._set_window_icon()

        splash = SplashScreen(self)
        self.update()

        try:
            self.chatbot = FAQChatbot()
        except Exception as exc:
            splash.destroy()
            messagebox.showerror("Startup Error", f"Could not load the FAQ chatbot:\n\n{exc}")
            self.destroy()
            return

        self.active_category = None
        self.suggestion_pool = list(DEFAULT_SUGGESTION_POOL)
        self._typing_job = None
        self._typing_label = None
        self._typing_row = None
        self._typing_dots = 0

        self._setup_styles()
        self._build_ui()
        self._add_welcome_message()
        self._refresh_suggestions()

        self.bind("<Control-Return>", lambda event: self.send_message())
        self.bind("<Return>", self._handle_enter)

        self.after(700, lambda: self._finish_startup(splash))

    def _finish_startup(self, splash):
        splash.destroy()
        self.deiconify()
        self.input_box.focus_set()

    def _set_window_icon(self):
        try:
            self._icon_image = tk.PhotoImage(file=str(ICON_PATH))
            self.iconphoto(True, self._icon_image)
        except Exception:
            pass

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 9),
            borderwidth=0
        )
        style.configure(
            "TProgressbar",
            troughcolor=PRIMARY_DARK,
            background=ACCENT,
            bordercolor=PRIMARY_DARK,
            lightcolor=ACCENT,
            darkcolor=ACCENT
        )
        style.configure(
            "Sidebar.TButton",
            font=("Segoe UI", 9, "bold"),
            padding=(10, 8)
        )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        self._build_header()

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        self._build_sidebar(body)

        main_col = tk.Frame(body, bg=BG)
        main_col.pack(side="left", fill="both", expand=True, padx=(14, 0))

        self._build_status_row(main_col)
        self._build_chat_area(main_col)
        self._build_suggestions(main_col)
        self._build_input_area(main_col)

    def _build_header(self):
        header = tk.Frame(self, bg=PRIMARY, height=92)
        header.pack(fill="x")
        header.pack_propagate(False)

        title = tk.Label(
            header,
            text="  🤖  Smart FAQ Chatbot",
            font=("Segoe UI", 23, "bold"),
            fg="white",
            bg=PRIMARY
        )
        title.pack(anchor="w", padx=28, pady=(14, 0))

        subtitle = tk.Label(
            header,
            text="NLP-powered university assistant • CodeAlpha AI Internship — Task 2",
            font=("Segoe UI", 10),
            fg="#D9E8DE",
            bg=PRIMARY
        )
        subtitle.pack(anchor="w", padx=32, pady=(2, 0))

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=SIDEBAR_BG, width=190, highlightbackground=BORDER, highlightthickness=1)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar, text="CATEGORIES", font=("Segoe UI", 9, "bold"),
            fg=MUTED, bg=SIDEBAR_BG
        ).pack(anchor="w", padx=16, pady=(16, 8))

        self.category_buttons = {}

        all_btn = tk.Button(
            sidebar, text="💬  All Topics", anchor="w",
            command=lambda: self._select_category(None),
            font=("Segoe UI", 9, "bold"), fg="white", bg=PRIMARY,
            activebackground=PRIMARY_DARK, activeforeground="white",
            relief="flat", padx=12, pady=8, cursor="hand2", bd=0
        )
        all_btn.pack(fill="x", padx=10, pady=3)
        self.category_buttons[None] = all_btn

        icons = {
            "Admissions": "🎓", "Fees": "💳", "Academic": "📘",
            "Exams": "📝", "Attendance": "🗓️", "Library": "📚",
            "IT Support": "💻", "Student Services": "🏫", "General": "❓"
        }

        self._sidebar_frame = sidebar
        self._sidebar_icons = icons
        self._populate_sidebar()

    def _populate_sidebar(self):
        for category in self.chatbot.categories:
            icon = self._sidebar_icons.get(category, "•")
            btn = tk.Button(
                self._sidebar_frame, text=f"{icon}  {category}", anchor="w",
                command=lambda c=category: self._select_category(c),
                font=("Segoe UI", 9), fg=TEXT, bg=SIDEBAR_BG,
                activebackground=USER_BG, activeforeground=TEXT,
                relief="flat", padx=12, pady=7, cursor="hand2", bd=0
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.category_buttons[category] = btn

    def _build_status_row(self, parent):
        info = tk.Frame(parent, bg=BG)
        info.pack(fill="x", pady=(14, 10))

        tk.Label(
            info,
            text="Ask a question about admissions, fees, academics, exams, library, attendance or student services.",
            font=("Segoe UI", 10),
            fg=MUTED,
            bg=BG
        ).pack(side="left")

        self.status_label = tk.Label(
            info,
            text="● Ready",
            font=("Segoe UI", 10, "bold"),
            fg=SUCCESS,
            bg=BG
        )
        self.status_label.pack(side="right")

    def _build_chat_area(self, parent):
        chat_card = tk.Frame(
            parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1
        )
        chat_card.pack(fill="both", expand=True)

        self.chat_canvas = tk.Canvas(
            chat_card, bg=CARD, highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            chat_card, orient="vertical", command=self.chat_canvas.yview
        )
        self.messages_frame = tk.Frame(self.chat_canvas, bg=CARD)

        self.messages_frame.bind(
            "<Configure>",
            lambda event: self.chat_canvas.configure(
                scrollregion=self.chat_canvas.bbox("all")
            )
        )

        self.chat_window = self.chat_canvas.create_window(
            (0, 0), window=self.messages_frame, anchor="nw"
        )

        self.chat_canvas.bind(
            "<Configure>",
            lambda event: self.chat_canvas.itemconfigure(
                self.chat_window, width=event.width
            )
        )

        self.chat_canvas.configure(yscrollcommand=scrollbar.set)

        self.chat_canvas.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=12)
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=12)

    def _build_suggestions(self, parent):
        suggestions_wrap = tk.Frame(parent, bg=BG)
        suggestions_wrap.pack(fill="x", pady=(12, 8))

        top_row = tk.Frame(suggestions_wrap, bg=BG)
        top_row.pack(fill="x")

        tk.Label(
            top_row, text="Try:", font=("Segoe UI", 9, "bold"),
            fg=MUTED, bg=BG
        ).pack(side="left", padx=(2, 7))

        self.suggestions_row = tk.Frame(top_row, bg=BG)
        self.suggestions_row.pack(side="left", fill="x", expand=True)

        refresh_btn = tk.Button(
            top_row, text="🔄 Refresh", command=self._refresh_suggestions,
            font=("Segoe UI", 8, "bold"), fg=PRIMARY, bg=BG,
            activebackground=USER_BG, relief="flat", bd=0, cursor="hand2"
        )
        refresh_btn.pack(side="right", padx=(6, 2))

    def _build_input_area(self, parent):
        input_card = tk.Frame(
            parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1
        )
        input_card.pack(fill="x")

        button_area = tk.Frame(input_card, bg=CARD)
        button_area.pack(side="right", padx=10, pady=8)

        text_col = tk.Frame(input_card, bg=CARD)
        text_col.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)

        self.input_box = tk.Text(
            text_col,
            height=3,
            wrap="word",
            font=("Segoe UI", 11),
            fg=TEXT,
            bg=CARD,
            insertbackground=PRIMARY,
            relief="flat",
            padx=12,
            pady=10
        )
        self.input_box.pack(fill="both", expand=True)
        self.input_box.bind("<KeyRelease>", self._update_char_count)

        self.char_count_label = tk.Label(
            text_col, text=f"0 words • 0 / {MAX_INPUT_CHARS} characters",
            font=("Segoe UI", 8), fg=MUTED, bg=CARD
        )
        self.char_count_label.pack(anchor="e", padx=10, pady=(0, 4))

        export_btn = tk.Button(
            button_area,
            text="⬇ Export",
            command=self.export_chat,
            font=("Segoe UI", 9, "bold"),
            fg=PRIMARY,
            bg="#EFEADA",
            activebackground="#E4DCC3",
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2"
        )
        export_btn.pack(pady=(0, 6), fill="x")

        clear_chat_btn = tk.Button(
            button_area,
            text="🗑 Clear Chat",
            command=self.clear_chat,
            font=("Segoe UI", 9, "bold"),
            fg=MUTED,
            bg="#EFEADA",
            activebackground="#E4DCC3",
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2"
        )
        clear_chat_btn.pack(pady=(0, 6), fill="x")

        send_btn = tk.Button(
            button_area,
            text="Send  ➤",
            command=self.send_message,
            font=("Segoe UI", 10, "bold"),
            fg="white",
            bg=PRIMARY,
            activebackground=PRIMARY_DARK,
            relief="flat",
            padx=18,
            pady=10,
            cursor="hand2"
        )
        send_btn.pack(fill="x")

        tk.Label(
            parent,
            text="Press Enter to send • Ctrl+Enter also works • Shift+Enter for a new line",
            font=("Segoe UI", 8),
            fg=MUTED,
            bg=BG
        ).pack(anchor="e", pady=(5, 0))

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------
    def _handle_enter(self, event):
        if event.state & 0x0001:
            return
        self.send_message()
        return "break"

    def _update_char_count(self, event=None):
        text = self.input_box.get("1.0", "end-1c")
        if len(text) > MAX_INPUT_CHARS:
            text = text[:MAX_INPUT_CHARS]
            self.input_box.delete("1.0", "end")
            self.input_box.insert("1.0", text)

        words = len(text.split())
        chars = len(text)
        color = ERROR if chars >= MAX_INPUT_CHARS else MUTED
        self.char_count_label.config(
            text=f"{words} words • {chars} / {MAX_INPUT_CHARS} characters",
            fg=color
        )

    def _select_category(self, category):
        self.active_category = category
        for cat, btn in self.category_buttons.items():
            if cat == category:
                btn.config(bg=PRIMARY, fg="white", activebackground=PRIMARY_DARK)
            else:
                btn.config(bg=SIDEBAR_BG, fg=TEXT, activebackground=USER_BG)

        if category is None:
            self._refresh_suggestions()
        else:
            questions = self.chatbot.questions_by_category(category)
            sample = random.sample(questions, min(4, len(questions)))
            self._render_suggestions(sample)

    def _refresh_suggestions(self):
        sample = random.sample(
            self.suggestion_pool, min(3, len(self.suggestion_pool))
        )
        self._render_suggestions(sample)

    def _render_suggestions(self, questions):
        for widget in self.suggestions_row.winfo_children():
            widget.destroy()

        for text in questions:
            btn = tk.Button(
                self.suggestions_row,
                text=text,
                command=lambda q=text: self.use_suggestion(q),
                font=("Segoe UI", 8),
                fg=TEXT,
                bg=CARD,
                activebackground=USER_BG,
                relief="solid",
                bd=1,
                highlightthickness=0,
                padx=8,
                pady=4,
                cursor="hand2",
                wraplength=220,
                justify="left"
            )
            btn.pack(side="left", padx=4, pady=2)

    def _add_welcome_message(self):
        self._add_message(
            "bot",
            "Hello! 👋 I'm your Smart FAQ Chatbot.\n\n"
            "Ask me about admissions, fees, academics, attendance, exams, "
            "library, IT support, or student services — or pick a category "
            "from the sidebar."
        )

    def _add_message(self, sender, text, category=None, confidence=None, suggestions=None):
        row = tk.Frame(self.messages_frame, bg=CARD)
        row.pack(fill="x", padx=12, pady=7)

        if sender == "user":
            bubble_bg = USER_BG
            title = "You"
            anchor = "e"
            title_fg = PRIMARY
        else:
            bubble_bg = BOT_BG
            title = "FAQ Assistant"
            anchor = "w"
            title_fg = SUCCESS

        container = tk.Frame(row, bg=bubble_bg, padx=13, pady=9)
        container.pack(anchor=anchor, padx=8)

        tk.Label(
            container,
            text=title,
            font=("Segoe UI", 9, "bold"),
            fg=title_fg,
            bg=bubble_bg
        ).pack(anchor="w")

        tk.Label(
            container,
            text=text,
            font=("Segoe UI", 10),
            fg=TEXT,
            bg=bubble_bg,
            justify="left",
            wraplength=680
        ).pack(anchor="w", pady=(3, 0))

        if sender == "bot" and category:
            confidence_text = f"Category: {category}"
            if confidence is not None:
                confidence_text += f"  •  Match: {confidence:.0%}"

            tk.Label(
                container,
                text=confidence_text,
                font=("Segoe UI", 8),
                fg=MUTED,
                bg=bubble_bg
            ).pack(anchor="w", pady=(5, 0))

        if sender == "bot" and suggestions:
            tip = tk.Label(
                container, text="Did you mean:", font=("Segoe UI", 8, "bold"),
                fg=ACCENT, bg=bubble_bg
            )
            tip.pack(anchor="w", pady=(8, 2))
            for q in suggestions:
                sbtn = tk.Button(
                    container, text=f"↳ {q}", anchor="w",
                    command=lambda qq=q: self.use_suggestion(qq),
                    font=("Segoe UI", 8), fg=PRIMARY, bg=bubble_bg,
                    activebackground=USER_BG, relief="flat", bd=0,
                    cursor="hand2", justify="left", wraplength=620
                )
                sbtn.pack(anchor="w", pady=1)

        if sender == "bot" and category and category not in ("Greeting", "Input"):
            self._add_feedback_row(container, bubble_bg, text)

        timestamp = datetime.now().strftime("%I:%M %p")
        tk.Label(
            row,
            text=timestamp,
            font=("Segoe UI", 7),
            fg="#9AA9B8",
            bg=CARD
        ).pack(anchor=anchor, padx=14)

        self.after(30, self._scroll_to_bottom)
        return row

    def _add_feedback_row(self, container, bubble_bg, answer_text):
        row = tk.Frame(container, bg=bubble_bg)
        row.pack(anchor="w", pady=(8, 0))

        tk.Label(
            row, text="Was this helpful?", font=("Segoe UI", 8),
            fg=MUTED, bg=bubble_bg
        ).pack(side="left", padx=(0, 6))

        feedback_state = {"given": False}

        def give_feedback(is_helpful, up_btn, down_btn):
            if feedback_state["given"]:
                return
            feedback_state["given"] = True
            up_btn.config(state="disabled")
            down_btn.config(state="disabled")
            self._log_feedback(answer_text, is_helpful)
            note = "Thanks for the feedback! 🙏" if is_helpful else "Noted — thanks, we'll improve this. 🙏"
            tk.Label(
                row, text=note, font=("Segoe UI", 8, "italic"),
                fg=SUCCESS if is_helpful else MUTED, bg=bubble_bg
            ).pack(side="left", padx=(6, 0))

        up_btn = tk.Button(
            row, text="👍", font=("Segoe UI", 9), bg=bubble_bg,
            activebackground=USER_BG, relief="flat", bd=0, cursor="hand2",
            padx=4, pady=0
        )
        down_btn = tk.Button(
            row, text="👎", font=("Segoe UI", 9), bg=bubble_bg,
            activebackground=USER_BG, relief="flat", bd=0, cursor="hand2",
            padx=4, pady=0
        )
        up_btn.config(command=lambda: give_feedback(True, up_btn, down_btn))
        down_btn.config(command=lambda: give_feedback(False, up_btn, down_btn))
        up_btn.pack(side="left")
        down_btn.pack(side="left")

    def _log_feedback(self, answer_text, is_helpful):
        log_path = BASE_DIR / "data" / "feedback_log.json"
        try:
            if log_path.exists():
                with open(log_path, "r", encoding="utf-8") as file:
                    entries = json.load(file)
            else:
                entries = []
        except (json.JSONDecodeError, OSError):
            entries = []

        entries.append({
            "answer": answer_text,
            "helpful": is_helpful,
            "timestamp": datetime.now().isoformat(timespec="seconds")
        })

        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as file:
                json.dump(entries, file, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def _scroll_to_bottom(self):
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def _show_typing_indicator(self):
        row = tk.Frame(self.messages_frame, bg=CARD)
        row.pack(fill="x", padx=12, pady=7)

        container = tk.Frame(row, bg=BOT_BG, padx=13, pady=9)
        container.pack(anchor="w", padx=8)

        tk.Label(
            container, text="FAQ Assistant", font=("Segoe UI", 9, "bold"),
            fg=SUCCESS, bg=BOT_BG
        ).pack(anchor="w")

        label = tk.Label(
            container, text="typing.", font=("Segoe UI", 10, "italic"),
            fg=MUTED, bg=BOT_BG
        )
        label.pack(anchor="w", pady=(3, 0))

        self._typing_row = row
        self._typing_label = label
        self._typing_dots = 1
        self._animate_typing()
        self.after(30, self._scroll_to_bottom)

    def _animate_typing(self):
        if not self._typing_label:
            return
        dots = "." * (self._typing_dots % 4 + 1)
        self._typing_label.config(text=f"typing{dots}")
        self._typing_dots += 1
        self._typing_job = self.after(400, self._animate_typing)

    def _hide_typing_indicator(self):
        if self._typing_job:
            self.after_cancel(self._typing_job)
            self._typing_job = None
        if self._typing_row:
            self._typing_row.destroy()
            self._typing_row = None
            self._typing_label = None

    def send_message(self):
        text = self.input_box.get("1.0", "end").strip()
        if not text:
            self.status_label.config(text="● Enter a question", fg=WARNING)
            return

        self._add_message("user", text)
        self.input_box.delete("1.0", "end")
        self._update_char_count()
        self.status_label.config(text="● Finding the best answer...", fg=PRIMARY)
        self.update_idletasks()

        self._show_typing_indicator()

        delay = min(1400, max(500, len(text) * 20))
        self.after(delay, lambda: self._deliver_response(text))

    def _deliver_response(self, text):
        self._hide_typing_indicator()
        try:
            result = self.chatbot.get_response(text)
            self._add_message(
                "bot",
                result["answer"],
                result["category"],
                result["confidence"],
                suggestions=result.get("suggestions")
            )
            self.status_label.config(text="● Ready", fg=SUCCESS)
        except Exception as exc:
            self._add_message(
                "bot",
                "Something went wrong while processing your question. "
                "Please try again."
            )
            self.status_label.config(text="● Error", fg=ERROR)
            print(f"Error: {exc}")

    def use_suggestion(self, question):
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", question)
        self._update_char_count()
        self.input_box.focus_set()
        self.send_message()

    def clear_input(self):
        self.input_box.delete("1.0", "end")
        self._update_char_count()
        self.input_box.focus_set()
        self.status_label.config(text="● Ready", fg=SUCCESS)

    def clear_chat(self):
        if not messagebox.askyesno("Clear Chat", "Clear the whole conversation?"):
            return
        for widget in self.messages_frame.winfo_children():
            widget.destroy()
        self._add_welcome_message()
        self.status_label.config(text="● Chat cleared", fg=SUCCESS)

    def export_chat(self):
        lines = []
        for row in self.messages_frame.winfo_children():
            for container in row.winfo_children():
                labels = [w for w in container.winfo_children() if isinstance(w, tk.Label)]
                if len(labels) >= 2:
                    speaker = labels[0].cget("text")
                    message = labels[1].cget("text")
                    lines.append(f"{speaker}: {message}")
            lines.append("")

        if not lines:
            messagebox.showinfo("Export Chat", "There is no conversation to export yet.")
            return

        default_name = f"faq_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text file", "*.txt")]
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write("Smart FAQ Chatbot — Conversation Export\n")
                file.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                file.write("=" * 50 + "\n\n")
                file.write("\n".join(lines))
            self.status_label.config(text="● Chat exported", fg=SUCCESS)
        except Exception as exc:
            messagebox.showerror("Export Error", f"Could not save the file:\n\n{exc}")


if __name__ == "__main__":
    app = FAQChatbotApp()
    app.mainloop()
