import json
import re
from pathlib import Path
from datetime import datetime

from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class FAQChatbot:
    """NLP-based FAQ chatbot using TF-IDF and cosine similarity."""

    # Lightweight Roman Urdu small-talk patterns, handled before TF-IDF
    # matching so common greetings/thanks feel natural in either language.
    ROMAN_URDU_REPLIES = [
        (
            {"salam", "assalam", "assalamualaikum", "aoa", "slm", "salaam"},
            "Wa alaikum assalam! 👋 Main aapki university se related sawalat "
            "(admissions, fees, exams, attendance, library) mein madad kar "
            "sakta hoon. Apna sawal likhein."
        ),
        (
            {"shukriya", "shukria", "thanks", "thankyou", "jazakallah"},
            "Khushi hui madad kar ke! 😊 Koi aur sawal ho to zaroor poochein."
        ),
        (
            {"haal", "hal", "kaisay", "kaise", "kesay"},
            "Main theek hoon, shukriya! Main aapki university se related "
            "sawalat mein madad kar sakta hoon — poochein kya jaanna hai?"
        ),
    ]

    def __init__(self, data_file="data/faqs.json", threshold=0.28,
                 log_file="data/unanswered_log.json"):
        self.base_dir = Path(__file__).resolve().parent
        self.data_file = self.base_dir / data_file
        self.log_file = self.base_dir / log_file
        self.threshold = threshold
        self.stemmer = PorterStemmer()

        # A small built-in set keeps the project self-contained.
        # NLTK is still used for stemming.
        self.stop_words = {
            "a", "an", "the", "is", "are", "am", "was", "were", "be",
            "to", "of", "in", "on", "for", "from", "and", "or", "but",
            "how", "what", "where", "when", "why", "can", "could",
            "i", "my", "me", "we", "our", "you", "your", "do", "does",
            "did", "this", "that", "it", "with", "at", "by", "about",
            "after", "before", "if", "will", "should", "would"
        }

        self.faqs = self._load_faqs()
        self.questions = [item["question"] for item in self.faqs]

        self.vectorizer = TfidfVectorizer(
            preprocessor=self.preprocess,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9']*\b",
            ngram_range=(1, 2),
            sublinear_tf=True
        )
        self.question_vectors = self.vectorizer.fit_transform(self.questions)
        self.categories = sorted({item["category"] for item in self.faqs})

    def questions_by_category(self, category):
        """Return the list of questions belonging to a given category."""
        return [item["question"] for item in self.faqs if item["category"] == category]

    def _load_faqs(self):
        with open(self.data_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not data:
            raise ValueError("FAQ dataset is empty.")

        required = {"question", "answer", "category"}
        for item in data:
            if not required.issubset(item):
                raise ValueError("Each FAQ must contain question, answer, and category.")
        return data

    def preprocess(self, text):
        text = text.lower()
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9']*", text)
        words = [
            self.stemmer.stem(word)
            for word in words
            if word not in self.stop_words
        ]
        return " ".join(words)

    def _check_roman_urdu_smalltalk(self, user_text):
        """Return a canned reply for short Roman Urdu greetings/thanks, else None."""
        words = set(re.findall(r"[a-zA-Z]+", user_text.lower()))
        if len(words) > 6:
            return None
        for trigger_words, reply in self.ROMAN_URDU_REPLIES:
            if words & trigger_words:
                return reply
        return None

    def _log_unanswered(self, user_text, best_score):
        """Append a low-confidence question to a local JSON log for later review."""
        try:
            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8") as file:
                    entries = json.load(file)
            else:
                entries = []
        except (json.JSONDecodeError, OSError):
            entries = []

        entries.append({
            "question": user_text,
            "confidence": round(best_score, 4),
            "timestamp": datetime.now().isoformat(timespec="seconds")
        })

        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "w", encoding="utf-8") as file:
                json.dump(entries, file, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def get_response(self, user_text):
        user_text = user_text.strip()

        if not user_text:
            return {
                "answer": "Please enter a question so I can help you.",
                "category": "Input",
                "confidence": 0.0,
                "matched_question": None,
                "suggestions": []
            }

        smalltalk_reply = self._check_roman_urdu_smalltalk(user_text)
        if smalltalk_reply:
            return {
                "answer": smalltalk_reply,
                "category": "Greeting",
                "confidence": 1.0,
                "matched_question": None,
                "suggestions": []
            }

        user_vector = self.vectorizer.transform([user_text])
        scores = cosine_similarity(user_vector, self.question_vectors)[0]
        best_index = scores.argmax()
        best_score = float(scores[best_index])

        if best_score < self.threshold:
            self._log_unanswered(user_text, best_score)
            top_n = scores.argsort()[::-1][:3]
            suggestions = [
                self.faqs[i]["question"] for i in top_n if scores[i] > 0
            ]
            return {
                "answer": (
                    "I'm sorry, I couldn't find a reliable answer for that question. "
                    "Please try asking in a different way, or pick one of the closest "
                    "questions below, or contact the relevant university office."
                ),
                "category": "Fallback",
                "confidence": best_score,
                "matched_question": None,
                "suggestions": suggestions
            }

        best_faq = self.faqs[best_index]
        return {
            "answer": best_faq["answer"],
            "category": best_faq["category"],
            "confidence": best_score,
            "matched_question": best_faq["question"],
            "suggestions": []
        }
