# 🌐 Transora

A desktop language translation application built for **Task 1** of the
**CodeAlpha Artificial Intelligence Internship**.

The app lets a user type text, choose a source and target language, and
instantly see the translated result — with copy, clear, and swap-languages
functionality, wrapped in a clean, modern desktop UI.

Suggested GitHub repository name: **`CodeAlpha_LanguageTranslationTool`**

---

## ✨ Features

- 📝 Multi-line text input box
- 🌍 Dropdowns for **source** and **target** language (14+ languages, plus Auto-Detect for source)
- 🔄 **Swap Languages** button — instantly flips source/target and the text in both boxes
- 🧹 **Clear** button — resets both text areas
- 📋 **Copy Translation** button — copies the result straight to the clipboard
- ⚠️ Robust error handling — empty input, unsupported languages, and network/API failures are all caught and shown as friendly status messages (the app never crashes)
- ⏳ Non-blocking UI — translation runs on a background thread, so the window stays responsive while waiting on the network
- 🎨 Modern, light, professional interface built with `tkinter.ttk`

---

## 🛠️ Technologies Used

| Component        | Technology                                  |
|-------------------|----------------------------------------------|
| Language          | Python 3.9+                                   |
| GUI               | Tkinter / ttk (standard library)              |
| Translation engine| [`deep-translator`](https://pypi.org/project/deep-translator/) (Google Translate backend) |
| Clipboard support | `pyperclip`                                   |

---

## 📁 Project Structure

```
LanguageTranslationTool/
│
├── main.py             # Tkinter GUI — layout, events, threading
├── translator.py        # Translation logic, language map, error handling
├── requirements.txt     # Python dependencies
├── README.md             # Project documentation (this file)
└── assets/                # Reserved for icons/screenshots (optional)
```

Keeping the GUI (`main.py`) and the translation logic (`translator.py`)
in separate files means the translation engine can be tested, reused, or
swapped out (e.g. for a different API) without touching any GUI code.

---

## ⚙️ How Translation Works

1. The user types text into the **Enter text** box and picks a **source**
   and **target** language from the dropdowns.
2. `main.py` validates that the box isn't empty, then hands the text off
   to `translate_text()` in `translator.py` on a **background thread**
   (so the window never freezes).
3. `translator.py` maps the human-readable language names (e.g. "Urdu")
   to the language codes the translation backend expects (e.g. `"ur"`),
   then calls `GoogleTranslator` from the `deep-translator` library,
   which sends the request to Google Translate's public web endpoint
   and returns the translated string.
4. Any failure (empty text, unsupported language, no internet, API
   downtime) is caught and converted into a single `TranslationError`
   with a clear message, which the GUI displays in the status bar
   instead of crashing.
5. The result is displayed in the **Translation** panel, ready to be
   copied with one click.

---

## 🚀 Installation & Setup

### 1. Prerequisites
- Python 3.9 or newer installed
- `pip` available on your PATH

### 2. Get the project
```bash
git clone https://github.com/<your-username>/CodeAlpha_LanguageTranslationTool.git
cd CodeAlpha_LanguageTranslationTool
```
*(Or simply download/copy the `LanguageTranslationTool` folder.)*

### 3. (Recommended) Create a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

> **Note on Tkinter:** Tkinter ships with most standard Python installs.
> On some Linux distributions you may need to install it separately:
> `sudo apt-get install python3-tk`

---

## ▶️ How to Run the Project (including in VS Code)

1. Open the `LanguageTranslationTool` folder in **VS Code**
   (`File → Open Folder...`).
2. Make sure VS Code is using the Python interpreter from your virtual
   environment (bottom-right corner of VS Code, or `Ctrl+Shift+P` →
   *Python: Select Interpreter*).
3. Open `main.py`.
4. Run it either by:
   - Clicking the **▶ Run** button in the top-right of VS Code, or
   - Opening a terminal in VS Code (`` Ctrl+` ``) and running:
     ```bash
     python main.py
     ```
5. The **Transora** window should open.

---

## 🔑 API Configuration

This project uses `deep-translator`, which calls free translation
services — **no API key is required** to run the project out of the box.
This keeps setup simple for a student/internship submission.

### About the "too many requests" rate-limit message

Google's free translate endpoint enforces a shared daily request limit
per IP address. If you see a "too many requests" / rate-limit error,
it means that free endpoint is temporarily busy — it is **not** a bug
in the code. This project now handles that automatically:

- It tries **Google Translate** first.
- If Google is rate-limited or unreachable, it automatically falls
  back to **MyMemory Translate**, a separate free service — so a
  translation still comes back.
- Identical text/language requests are **cached** in memory for the
  session, so re-translating the same sentence never re-hits the
  network.
- If every free service is genuinely down at the same time, you'll
  see a clear message: *"Translation service is temporarily
  unavailable. Please try again later."* — the app will never crash.

### Optional: using an official Microsoft Translator key

You don't need this to run the project, but if you want extra
reliability, you can add a free-tier **Microsoft Translator** (Azure)
key:

1. Get a key from the Azure Portal (Translator resource).
2. Create a file named `.env` in the project root (add it to
   `.gitignore` — never commit it) containing:
   ```
   MICROSOFT_TRANSLATOR_KEY=your_key_here
   MICROSOFT_TRANSLATOR_REGION=your_region_here
   ```
3. That's it — `translator.py` automatically detects the key and uses
   Microsoft Translator first, falling back to the free Google/MyMemory
   chain only if it's missing or fails.

### Switching to a paid/official API (optional, for extra credit)

If you'd like to use the **official Google Cloud Translation API** or
**Microsoft Translator (Azure) API** instead (both mentioned in the
CodeAlpha task description), the project is structured so this only
requires changing `translator.py`:

1. Create a `.env` file in the project root (never commit this file):
   ```
   TRANSLATION_API_KEY=your_api_key_here
   ```
2. Add `python-dotenv` to `requirements.txt` and load the key safely:
   ```python
   import os
   from dotenv import load_dotenv

   load_dotenv()
   API_KEY = os.getenv("TRANSLATION_API_KEY")
   if not API_KEY:
       raise TranslationError("Missing TRANSLATION_API_KEY in your .env file.")
   ```
3. Replace the `GoogleTranslator(...)` call in `translate_text()` with a
   call to your chosen API's SDK/HTTP client, using `API_KEY` for
   authentication.
4. Add `.env` to your `.gitignore` so the key is never pushed to GitHub.

Because all translation logic is isolated in `translate_text()`, the GUI
in `main.py` requires **zero changes** when you make this switch.

---

## 🧪 Testing Instructions

Run the app (`python main.py`) and try the following cases:

| # | Input | Source → Target | Expected Result |
|---|-------|------------------|------------------|
| 1 | `Hello, how are you?` | English → Urdu | Urdu translation appears in the output panel |
| 2 | `I love programming.` | English → French | French translation appears |
| 3 | *(leave input empty)*, click **Translate** | any → any | Status bar shows "Please enter some text to translate." — no crash |
| 4 | Any text, then click **Swap Languages** | e.g. English ⇄ Urdu | Source/target dropdowns and text boxes swap |
| 5 | Translate something, then click **Copy Translation** | — | Status bar confirms "Translation copied to clipboard." — paste anywhere to verify |
| 6 | Click **Clear** | — | Both text boxes empty, status resets |
| 7 | Disconnect your internet, then click **Translate** | any → any | Friendly error: "Could not reach the translation service..." — app stays open |

---

## 🔮 Possible Future Improvements

- Add **text-to-speech** playback for both input and output text
- Add **language auto-detection display** (show which language was detected)
- Support **file upload** (translate `.txt`/`.docx` files)
- Add a **translation history** panel with a local SQLite database
- Add a **dark mode** toggle
- Package the app as a standalone `.exe` / `.app` using PyInstaller
- Add unit tests (`pytest`) for `translator.py`

---

## 📸 Making It Shine on GitHub / LinkedIn

- Add 2–3 **screenshots** or a short **screen recording (GIF)** of the
  app translating text — place them in the `assets/` folder and embed
  them at the top of this README.
- Write a short LinkedIn post: *"Completed Task 1 of my AI Internship at
  @CodeAlpha — built a desktop Language Translation Tool in Python with
  a custom Tkinter GUI, multithreaded API calls, and full error
  handling. #CodeAlpha #ArtificialIntelligence #Python"*
- Pin the repo on your GitHub profile and add topics like `python`,
  `tkinter`, `nlp`, `translation`, `codealpha`, `internship`.
- Include a **"Built With" badges** section at the top of this README
  (Python, Tkinter badges) for a more polished look.
- Tag CodeAlpha in your LinkedIn post so it's easy for reviewers to find.

---

## 👤 Author

Built as part of the **CodeAlpha Artificial Intelligence Internship — Task 1**.
