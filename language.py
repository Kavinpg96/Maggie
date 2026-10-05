"""
language.py - Bilingual (English/Tamil) support for Maggie

Detects Tamil vs English from recognized text (script-based, since it's
reliable and needs no extra libraries), then exposes the right TTS voice
and an LLM system-prompt addition so replies come back in the same language.
"""
import re
import json
import os

TAMIL_TTS_VOICE = "ta-IN-PallaviNeural"
ENGLISH_TTS_VOICE = "en-US-GuyNeural"  # swap for whatever voice you're already using

_TAMIL_RANGE = re.compile(r'[\u0B80-\u0BFF]')
_MODE_STATE_PATH = os.path.join(os.path.dirname(__file__), "data", "language_state.json")


def get_mode() -> str:
    """Returns the current language mode: 'en' or 'ta'. Defaults to 'en'.
    This is the single source of truth for both recognition and reply
    language — set only by an explicit "speak in Tamil/English" command,
    never guessed per-utterance (guessing per-utterance is what broke
    things: a Tamil-locale decode transliterates ANY audio, English
    included, into Tamil script, so script-presence isn't a real signal)."""
    try:
        with open(_MODE_STATE_PATH) as f:
            return json.load(f).get("mode", "en")
    except Exception:
        return "en"


def set_mode(mode: str):
    try:
        os.makedirs(os.path.dirname(_MODE_STATE_PATH), exist_ok=True)
        with open(_MODE_STATE_PATH, "w") as f:
            json.dump({"mode": mode}, f)
    except Exception:
        pass


def detect_language(text: str) -> str:
    """Returns 'ta' if the text contains Tamil script, else 'en'.

    Note: this only works once the text is already in Tamil script — it
    can't detect someone speaking Tamil words in English transliteration
    ("epdi irukeenga"). For that, the speech recognizer itself needs to be
    told to listen for Tamil (see the two-pass recognition note below).
    """
    return "ta" if _TAMIL_RANGE.search(text) else "en"


def tts_voice_for(lang: str) -> str:
    return TAMIL_TTS_VOICE if lang == "ta" else ENGLISH_TTS_VOICE


def system_prompt_suffix(lang: str) -> str:
    """Append this to SYSTEM_PROMPT in brain.py before calling Groq."""
    if lang == "ta":
        return " Respond only in Tamil (தமிழ் script), in a natural conversational tone."
    return ""


# Common Tamil-script renderings of English/Tanglish command words. Google's
# recognizer transcribes spoken English loanwords ("play", "video", "stop")
# into Tamil script when it thinks the whole utterance is Tamil, so plain
# `"play" in q` checks in brain.py never fire. This maps the transcribed
# forms back to their English keyword for intent matching only — words not
# in this list (like தமிழ், a search term) are left untouched, so the
# original meaning still reaches the YouTube search / LLM prompt.
TAMIL_KEYWORD_MAP = {
    "ப்ளே": "play",
    "பிளே": "play",
    "ப்லே": "play",
    "வீடியோ": "video",
    "யூடியூப்": "youtube",
    "யூட்யூப்": "youtube",
    "சாங்ஸ்": "songs",
    "சாங்": "song",
    "பாடல்கள்": "songs",
    "பாடல்": "song",
    "பாட்டு": "song",
    "நிறுத்து": "stop",
    "ஓபன்": "open",
    "ஓபன்ன்": "open",
    "சர்ச்": "search",
    "வெதர்": "weather",
    "ட்ராஃபிக்": "traffic",
    "நியூஸ்": "news",
    "ஸ்பீக்": "speak",
    "இங்கிலீஷ்": "english",
    "இன்": "in",
    "படத்தை": "movie",
    "படம்": "movie",
    "லேட்டஸ்ட்": "latest",
}


def normalize_intent_text(text: str) -> str:
    """Replace known Tamil-script command loanwords with their English
    equivalent, for keyword matching only — pass the ORIGINAL text (not
    this output) to search/LLM calls so real Tamil content is preserved."""
    normalized = text
    for tamil_word, english_word in TAMIL_KEYWORD_MAP.items():
        normalized = normalized.replace(tamil_word, english_word)
    return normalized
