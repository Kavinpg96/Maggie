"""
brain.py - Interactive Conversational Router with Dynamic Local/Web Fallback
"""
import psutil
from duckduckgo_search import DDGS
from rich.console import Console

import status
import web_answer
import system_control
import file_search
import memory
from config import GROQ_API_KEY, ASSISTANT_NAME

console = Console()

SYSTEM_PROMPT = (
    f"You are {ASSISTANT_NAME}, a friendly and conversational AI desktop voice assistant. "
    "Always speak naturally with the user, provide short 2 to 3 sentence answers, and offer proactive updates."
)

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
        console.print(f"[red]Web search error: {e}[/red]")
        return ""

def get_response(query: str) -> str:
    if not query.strip():
        return ""

    q = query.lower().strip()
    memory.log_conversation("user", query)

    # --- 1. LOCAL SYSTEM COMMANDS ---
    if any(cmd in q for cmd in ["shutdown", "close program", "exit maggie"]):
        status.set_flag("exit_requested", True)
        return "Shutting down system. Goodbye Kavin."

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
        origin, dest = "Electronic City", "Silk Board"
        if "from" in q and "to" in q:
            parts = q.split("from")[1].split("to")
            origin = parts[0].strip()
            dest = parts[1].strip()

        traffic_data = web_answer.fetch_traffic_eta(origin, dest)
        if "origin_lat" in traffic_data:
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

    # --- 4. NEWS & TECH UPDATES ---
    if any(trig in q for trig in ["news", "tech", "technology", "updates", "latest"]):
        res = web_answer.fetch_news("latest technology trends and news")
        memory.log_conversation("assistant", res)
        return res

    # --- 5. ONLINE CONVERSATIONAL FALLBACK WITH LIVE SEARCH ---
    web_context = search_web_fallback(query)
    prompt_payload = query
    if web_context:
        prompt_payload = f"User Question: {query}\n\nLive Web Information:\n{web_context}\n\nAnswer concisely in a conversational voice tone."

    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_payload}
                ],
                max_tokens=150
            ).choices[0].message.content
            memory.log_conversation("assistant", res)
            return res
        except Exception as e:
            console.print(f"[yellow]Groq Inference Note: {e}[/yellow]")

    res = "I searched online for that topic, but I could not reach the AI response server right now."
    memory.log_conversation("assistant", res)
    return res
