"""
brain.py - Interactive Conversational Router with Dynamic Local/Web Fallback
"""
import re
import psutil
from duckduckgo_search import DDGS
import applog
import status
import web_answer
import requests
import system_control
import file_search
import memory
import music
import language
import weather
import routines
from config import GROQ_API_KEY, OLLAMA_BASE_URL, OLLAMA_MODEL, ASSISTANT_NAME

SYSTEM_PROMPT = (
    f"You are {ASSISTANT_NAME}, a friendly and conversational AI desktop voice assistant. "
    "Be an intelligent, practical solution giver: understand the goal, use recent conversation context, "
    "and give direct, accurate, actionable steps. Do not ask the user to repeat information already given. "
    "Ask one concise follow-up only when a missing detail prevents a safe or useful answer. "
    "Never claim a task succeeded unless it did, and clearly say when information is uncertain. "
    "Keep spoken answers concise, but give enough detail to solve the problem."
)

_MAX_CONTEXT_MESSAGES = 12
_MAX_CONTEXT_CHARS = 1600


def _conversation_messages(system_prompt: str, prompt_payload: str, current_query: str) -> list:
    """Build a bounded chat history without duplicating the current user turn."""
    history = list(memory.get_recent_context(limit=_MAX_CONTEXT_MESSAGES + 1))
    if history and history[-1] == ("user", current_query):
        history.pop()

    messages = [{"role": "system", "content": system_prompt}]
    for role, content in history[-_MAX_CONTEXT_MESSAGES:]:
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        messages.append({
            "role": role,
            "content": content[-_MAX_CONTEXT_CHARS:],
        })
    messages.append({"role": "user", "content": prompt_payload})
    return messages


def search_web_fallback(query: str) -> str:
    """Fetches real-time information from DuckDuckGo when local handlers match nothing."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return ""
        snippets = "\n".join(f"- {r['body']}" for r in results)
        return snippets
    except Exception as e:
        applog.log(f"Web search error: {e}", style="red")
        return ""


def _contextual_search_query(query: str) -> str:
    """Include recent user wording so searches for short follow-ups have a topic."""
    history = memory.get_recent_context(limit=7)
    earlier_user_turns = [
        content for role, content in history
        if role == "user" and content != query
    ]
    if not earlier_user_turns:
        return query
    return f"{earlier_user_turns[-1]} {query}"


def _ask_ollama(messages: list) -> str:
    response = requests.post(
        f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat",
        json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
        timeout=8,
    )
    response.raise_for_status()
    answer = response.json().get("message", {}).get("content", "").strip()
    if not answer:
        raise RuntimeError("Ollama returned an empty answer")
    return answer


def get_response(query: str) -> str:
    if not query.strip():
        return ""

    q = query.lower().strip()
    # Normalize Tamil-script renderings of command words ("ப்ளே" -> "play")
    # so keyword matching below works even when the recognizer transcribed
    # spoken English/Tanglish into Tamil script. Real Tamil content words
    # (song names etc.) pass through unchanged.
    q = language.normalize_intent_text(q)
    memory.log_conversation("user", query)

    # --- 0. LANGUAGE MODE SWITCH ---
    # Explicit and deterministic -- this is the only thing that changes
    # recognition/reply language, never a per-utterance guess.
    if "speak" in q and "english" in q:
        language.set_mode("en")
        res = "Okay, I'll speak in English now."
        memory.log_conversation("assistant", res)
        return res
    if "speak" in q and ("tamil" in q or "தமிழ்" in query):
        language.set_mode("ta")
        res = "சரி, நான் இனி தமிழில் பேசுவேன்."
        memory.log_conversation("assistant", res)
        return res

    # --- 1. LOCAL SYSTEM COMMANDS ---
    if any(cmd in q for cmd in ["shutdown", "close program", "exit maggie"]):
        status.set_flag("exit_requested", True)
        return "Shutting down system. Goodbye Kavin."

    if any(phrase in q for phrase in (
        "where am i", "current location", "my location", "where is my location",
    )):
        try:
            location = weather.get_current_location()
            if location.get("source") == "device":
                res = f"Your device location is {location['place']}."
                if location.get("accuracy_meters") is not None:
                    res += f" The device reports accuracy within about {round(location['accuracy_meters'])} meters."
            else:
                res = (
                    "I don't have a verified location fix, and I won't guess from your IP "
                    "because it has shown the wrong city. Open Google Maps and enable its "
                    "location permission, or connect a GPS receiver, then ask me again."
                )
        except Exception as e:
            applog.log(f"Current location lookup failed: {e}", style="red")
            res = (
                "I don't have a verified location fix right now. I won't use an "
                "IP guess because it can put you in the wrong city."
            )
        memory.log_conversation("assistant", res)
        return res

    if any(cmd in q for cmd in ["status", "system status", "cpu", "memory", "ram"]):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        res = f"System operational. CPU load is at {cpu} percent, and memory usage is at {ram} percent."
        memory.log_conversation("assistant", res)
        return res

    exec_res = system_control.handle_execution(query)
    if exec_res:
        memory.log_conversation("assistant", exec_res)
        return exec_res

    if any(trig in q for trig in ["file", "find file", "open file"]):
        res = file_search.search_and_display(query)
        memory.log_conversation("assistant", res)
        return res

    # --- 2. TRAFFIC & ROUTE QUERIES ---
    if "traffic" in q or "route" in q or "how long from" in q:
        route_match = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+)", q)
        if not route_match:
            res = (
                "Tell me the route, for example, 'traffic from Chennai to Tambaram'. "
                "The map can show the route, but live congestion data is not configured."
            )
            memory.log_conversation("assistant", res)
            return res

        origin, dest = (part.strip() for part in route_match.groups())

        traffic_data = web_answer.fetch_traffic_eta(origin, dest)
        if traffic_data.get("origin_lat") is not None:
            status.set_traffic_map(traffic_data)

        res = traffic_data["text"]
        memory.log_conversation("assistant", res)
        return res

    # --- 3. WEATHER QUERIES ---
    if "weather" in q:
        location = "Bangalore"
        if "in " in q:
            location = q.split("in ")[1].strip()
        res = web_answer.fetch_weather(location)
        memory.log_conversation("assistant", res)
        return res

    # --- 3.3 OPEN A NAMED WEBSITE (+ optional notification check) ---
    # Handles arbitrary named sites system_control.py doesn't know about
    # (e.g. "open tnpsc website") by resolving the official URL live,
    # rather than hardcoding every possible site.
    site_match = re.search(r"open\s+([a-z0-9\s]+?)\s+website", q)
    if site_match:
        name = site_match.group(1).strip()
        opened, domain, msg = web_answer.open_official_site(name)
        res = msg
        if opened and any(w in q for w in ["notification", "update", "new"]):
            info = web_answer.fetch_from_domain(f"{name} notification", domain)
            res = f"{msg} {info}"
        memory.log_conversation("assistant", res)
        return res

    # --- 3.4 MUSIC / VIDEO SONGS ---
    # Runs before browser-search so a "play" command doesn't fall through
    # to the generic "search for" trigger. Mentioning "video" or "youtube"
    # explicitly means the user wants to see it -> open in the browser.
    # Otherwise it streams audio-only via mpv.
    if "play" in q and "stop" not in q:
        wants_video = "video" in q or "youtube" in q

        term = re.sub(r"\bplay\b", "", q)
        term = re.sub(
            r"\b(a song|song|songs|for me|on youtube|in youtube|youtube|"
            r"video|track|music|open|and|please|can you|could you)\b",
            "", term,
        )
        term = re.sub(r"\s+", " ", term).strip() or "trending songs"

        if wants_video:
            ok = music.play_video(term)
            res = f"Playing {term} on YouTube." if ok else f"I couldn't find a video for {term}."
        else:
            ok = music.play(term)
            res = f"Playing {term}." if ok else f"I couldn't find that song: {term}."
        memory.log_conversation("assistant", res)
        return res

    if "stop music" in q or "pause music" in q or "stop song" in q:
        music.stop()
        res = "Stopped the music."
        memory.log_conversation("assistant", res)
        return res

    # --- 3.5 BROWSER SEARCH ---
    # Must sit above the news block below: a search query containing a word
    # like "latest" (e.g. "search for Tamil movies latest") would otherwise
    # get hijacked by the news trigger before it ever reached here.
    search_triggers = [
        "search in chrome for", "search chrome for", "search on chrome for",
        "google search for", "search for", "look up",
    ]
    matched_trig = next((t for t in search_triggers if t in q), None)
    if matched_trig:
        term = q.split(matched_trig, 1)[1]
        res = web_answer.open_browser_search(term)
        memory.log_conversation("assistant", res)
        return res

    # --- 3.6 TOPIC / SITE FETCH ---
    # Named sites ("check imdb for...") or known topics (movies, food,
    # cricket, ...) route to that specific site. Checked before the news
    # block below so a word like "latest" inside a movie/food query doesn't
    # get swallowed into generic tech news.
    topic_hit = (
        any(name in q for name in web_answer.SITE_NAME_TO_DOMAIN)
        or any(topic in q for topic in web_answer.TOPIC_TO_DOMAIN)
    )
    if topic_hit:
        res = web_answer.fetch_topic(query)
        memory.log_conversation("assistant", res)
        return res

    # --- 3.7 SCHEDULE DAILY BRIEFING ---
    # e.g. "set a daily briefing at 8am" / "give me a morning briefing every day at 7:30"
    if "briefing" in q and ("set" in q or "every day" in q or "daily" in q or "schedule" in q or "give me" in q):
        parsed = routines.parse_routine(query)
        if parsed:
            hour, minute, _label = parsed
            routines.add_routine(hour, minute, "daily briefing", kind="briefing")
            res = f"Done — I'll give you a daily briefing at {hour:02d}:{minute:02d}."
        else:
            res = "What time should I give you the daily briefing?"
        memory.log_conversation("assistant", res)
        return res

    # --- 4. NEWS & TECH UPDATES ---
    if any(trig in q for trig in ["news", "tech", "technology", "updates", "latest"]):
        res = web_answer.fetch_news(query)
        memory.log_conversation("assistant", res)
        return res

    # --- 5. ONLINE CONVERSATIONAL FALLBACK WITH LIVE SEARCH ---
    # Live search adds a network round trip to every open-ended request.
    # Keep that cost for questions that are likely to need current facts.
    needs_live_info = any(term in q for term in (
        " latest ", "today", "right now", "current", "currently", "news",
        "tomorrow", "weather", "traffic", "price", "score", "search", "look up",
    ))
    web_context = (
        search_web_fallback(_contextual_search_query(query))
        if needs_live_info else ""
    )
    prompt_payload = query
    if web_context:
        prompt_payload = (
            f"User Question: {query}\n\nLive Web Information:\n{web_context}\n\n"
            "Use this information when it is relevant. Distinguish sourced facts from uncertainty."
        )

    messages = _conversation_messages(
        SYSTEM_PROMPT + language.system_prompt_suffix(language.get_mode()),
        prompt_payload,
        query,
    )
    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            res = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                max_tokens=500
            ).choices[0].message.content
        except Exception as e:
            applog.log(f"Groq Inference Note: {e}", style="yellow")
        else:
            if res:
                memory.log_conversation("assistant", res)
                return res

    try:
        res = _ask_ollama(messages)
        memory.log_conversation("assistant", res)
        return res
    except requests.RequestException as e:
        applog.log(f"Local Ollama inference unavailable: {e}", style="yellow")
    except (KeyError, RuntimeError, ValueError) as e:
        applog.log(f"Local Ollama inference failed: {e}", style="yellow")

    if web_context:
        res = (
            "I couldn't reach an AI model just now. Here's the information I could find: "
            f"{web_context[:1200]}"
        )
    else:
        res = (
            "I couldn't reach the AI service or a local Ollama model. Check your internet "
            "connection and AI provider settings, then try again."
        )

    memory.log_conversation("assistant", res)
    return res
