"""
translator.py
--------------
Handles all translation logic for the AI Language Translation Tool.

WHY THE "TOO MANY REQUESTS" ERROR HAPPENED
--------------------------------------------
The previous version only used `GoogleTranslator` from `deep-translator`,
which works by calling Google Translate's free, *unofficial* web
endpoint (the same one translate.google.com uses in a browser). Google
rate-limits that endpoint per IP address — the message you saw
("Up to 2K requests per day...") is Google itself blocking further
requests once that shared limit is hit. This is a known limitation of
every free/unofficial Google-Translate wrapper, not a bug in your code.

HOW THIS VERSION FIXES IT (still 100% free, no paid API required)
--------------------------------------------------------------------
1. Automatic fallback chain: if Google's endpoint is rate-limited or
   unreachable, the app automatically retries the same request with
   MyMemory Translate (mymemory.translated.net) — a separate, free
   translation service with its own daily limit. One provider being
   busy no longer means the app stops working.
2. In-memory caching: translating the exact same text/language pair
   twice (e.g. clicking Translate twice by accident, or switching
   back to a sentence you already translated) is served instantly
   from cache instead of firing a new request — this alone removes a
   lot of unnecessary API calls during testing/demoing.
3. Optional official API support: if you ever add a Microsoft
   Translator key (see "Using an official API key" below), it is
   used automatically as the first, most reliable choice — with
   Google and MyMemory kept as free fallbacks.
4. Every failure is converted into a single, friendly `TranslationError`
   so the GUI can never crash — the user just sees a clear message.

USING AN OFFICIAL API KEY (fully optional)
---------------------------------------------
You do NOT need an API key to use this project — the free fallback
chain above works out of the box. If you later want the extra
reliability of Microsoft Translator (Azure), you can:

1. Get a free-tier key from the Azure Portal (Translator resource).
2. Create a file named `.env` in the project root (never commit this
   file to GitHub) containing:
       MICROSOFT_TRANSLATOR_KEY=your_key_here
       MICROSOFT_TRANSLATOR_REGION=your_region_here
3. That's it — this file automatically detects the key and uses
   Microsoft Translator first, falling back to the free services only
   if that key is missing or fails.
"""

import os
import time

from deep_translator import GoogleTranslator, MyMemoryTranslator

try:
    from deep_translator import MicrosoftTranslator
except ImportError:  # pragma: no cover - always present in current deep-translator
    MicrosoftTranslator = None

# python-dotenv is optional. If it isn't installed, the app still runs
# fine — it just relies on real environment variables instead of a
# .env file.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class TranslationError(Exception):
    """Raised whenever a translation could not be completed."""
    pass


# ---------------------------------------------------------------------------
# Supported languages
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES = {
    "Auto Detect": "auto",
    "English": "en",
    "Urdu": "ur",
    "Hindi": "hi",
    "Arabic": "ar",
    "French": "fr",
    "Spanish": "es",
    "German": "de",
    "Chinese (Simplified)": "zh-CN",
    "Japanese": "ja",
    "Korean": "ko",
    "Turkish": "tr",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
}

TARGET_LANGUAGES = {
    name: code for name, code in SUPPORTED_LANGUAGES.items() if name != "Auto Detect"
}

# MyMemory (unlike Google) needs region-qualified codes — e.g. "en-US"
# instead of plain "en" — or it rejects the request before even trying
# to translate. This maps our plain codes to the ones MyMemory expects.
MYMEMORY_CODE_MAP = {
    "en": "en-US",
    "ur": "ur-PK",
    "hi": "hi-IN",
    "ar": "ar-SA",
    "fr": "fr-FR",
    "es": "es-ES",
    "de": "de-DE",
    "zh-CN": "zh-CN",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "tr": "tr-TR",
    "it": "it-IT",
    "pt": "pt-PT",
    "ru": "ru-RU",
}


def get_source_language_names():
    return list(SUPPORTED_LANGUAGES.keys())


def get_target_language_names():
    return list(TARGET_LANGUAGES.keys())


# ---------------------------------------------------------------------------
# In-memory cache — avoids re-sending a request for text/language pairs
# that were already translated in this session.
# ---------------------------------------------------------------------------
_CACHE = {}
_CACHE_MAX_ENTRIES = 200


def _cache_get(key):
    return _CACHE.get(key)


def _cache_set(key, value):
    if len(_CACHE) >= _CACHE_MAX_ENTRIES:
        # Drop the oldest entry (dicts preserve insertion order in Python 3.7+)
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = value


# ---------------------------------------------------------------------------
# Backends — each takes (text, source_code, target_code) and returns a
# translated string, or raises an exception on failure.
# ---------------------------------------------------------------------------
def _translate_with_microsoft(text, source_code, target_code):
    api_key = os.getenv("MICROSOFT_TRANSLATOR_KEY")
    if not api_key or MicrosoftTranslator is None:
        raise TranslationError("Microsoft Translator key not configured.")
    region = os.getenv("MICROSOFT_TRANSLATOR_REGION")
    kwargs = {"api_key": api_key, "target": target_code}
    if source_code != "auto":
        kwargs["source"] = source_code
    if region:
        kwargs["region"] = region
    translator = MicrosoftTranslator(**kwargs)
    return translator.translate(text)


def _translate_with_google(text, source_code, target_code):
    translator = GoogleTranslator(source=source_code, target=target_code)
    return translator.translate(text)


def _translate_with_mymemory(text, source_code, target_code):
    # MyMemory needs an explicit source language — it cannot auto-detect.
    if source_code == "auto":
        raise TranslationError("MyMemory cannot auto-detect the source language.")
    mm_source = MYMEMORY_CODE_MAP.get(source_code, source_code)
    mm_target = MYMEMORY_CODE_MAP.get(target_code, target_code)
    translator = MyMemoryTranslator(source=mm_source, target=mm_target)
    return translator.translate(text)


def _build_backend_chain():
    """
    Decide which backends to try, and in what order.
    Microsoft (official, needs a key) is tried first only if configured.
    Google and MyMemory (both free, no key needed) are always available
    as fallbacks.
    """
    chain = []
    if os.getenv("MICROSOFT_TRANSLATOR_KEY"):
        chain.append(("Microsoft Translator", _translate_with_microsoft))
    chain.append(("Google Translate", _translate_with_google))
    chain.append(("MyMemory Translate", _translate_with_mymemory))
    return chain


def translate_text(text: str, source_lang_name: str, target_lang_name: str) -> str:
    """
    Translate `text` from `source_lang_name` to `target_lang_name`.

    Tries each configured backend in order (see `_build_backend_chain`).
    If one backend is rate-limited, down, or errors out, the next one is
    tried automatically. Results are cached so repeat requests for the
    same text/language pair never hit the network at all.

    Raises:
        TranslationError: for empty input, unsupported languages, or
        when every backend has failed. The message is written to be
        shown directly to the user.
    """
    # --- Input validation ---------------------------------------------
    if text is None or not text.strip():
        raise TranslationError("Please enter some text to translate.")

    if source_lang_name not in SUPPORTED_LANGUAGES:
        raise TranslationError(f"Unsupported source language: {source_lang_name}")

    if target_lang_name not in TARGET_LANGUAGES:
        raise TranslationError(f"Unsupported target language: {target_lang_name}")

    source_code = SUPPORTED_LANGUAGES[source_lang_name]
    target_code = TARGET_LANGUAGES[target_lang_name]

    if source_code != "auto" and source_code == target_code:
        raise TranslationError("Source and target languages must be different.")

    clean_text = text.strip()

    # --- Cache check: skip the network entirely on a repeat request ----
    cache_key = (clean_text, source_code, target_code)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # --- Try each backend in order until one succeeds -------------------
    last_error_message = None
    for backend_name, backend_fn in _build_backend_chain():
        try:
            result = backend_fn(clean_text, source_code, target_code)
            if result and result.strip():
                _cache_set(cache_key, result)
                return result
            last_error_message = f"{backend_name} returned an empty result."
        except Exception as exc:
            last_error_message = f"{backend_name} failed: {exc}"
            # A short pause before trying the next backend avoids
            # hammering the network right after a failure.
            time.sleep(0.3)
            continue

    # --- Every backend failed --------------------------------------------
    if source_code == "auto":
        raise TranslationError(
            "Translation service is temporarily unavailable. "
            "Please try again later, or pick a specific source language "
            "instead of 'Auto Detect'."
        )
    raise TranslationError(
        "Translation service is temporarily unavailable. Please try again later."
    )
