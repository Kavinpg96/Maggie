# Darling — Your Personal JARVIS

A voice assistant that:
- Listens continuously for the wake word **"Darling"**
- Understands what you ask (speech-to-text)
- Searches the live web when your question needs current info (news, weather, prices, "latest", etc.)
- Sends your question (+ web context if needed) to a free AI model (Gemini or Groq — no credit card needed)
- **Speaks** the answer back to you
- **Prints** everything to the console
- **Remembers** every conversation in a local database, so you can later say
  *"Darling, what did I ask you about the R2000 project?"*

This version uses **100% free services** — no billing, no credit card, anywhere.

---

## Step-by-step setup (do these in order)

### Step 1 — Open your terminal and go to the project folder
```bash
cd ~/darling
ls
```
You should see: `main.py`, `brain.py`, `listener.py`, `speaker.py`, `memory.py`, `config.py`, `requirements.txt`, `.env.example`, `data/`

### Step 2 — Create a virtual environment (only needed once)
```bash
python3 -m venv venv --system-site-packages
source venv/bin/activate
```
Your terminal prompt should now start with `(venv)`.

> Every time you open a new terminal to use Darling, run `source venv/bin/activate` again first.

### Step 3 — Install the Python packages
```bash
pip install -r requirements.txt
```
No `sudo` here — ever. If pip complains about `pyaudio`, that's already handled by `--system-site-packages` above.

### Step 4 — Get a free Gemini API key
1. Open **https://aistudio.google.com/apikey** in your browser
2. Sign in with any Google account
3. Click **"Create API key"**
4. Copy the key (starts with `AIza...`)

No card. No billing. Completely free.

### Step 5 — Set up your `.env` file
```bash
cp .env.example .env
nano .env
```
Make sure it looks like this (paste your real key in place of `your_key_here`):
```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
```
Save: `Ctrl+O`, then `Enter`, then exit: `Ctrl+X`

### Step 6 — Test your microphone is detected
```bash
python3 -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"
```
This should print a list of audio devices. If it errors or shows an empty list, tell me the output before continuing.

### Step 7 — Run Darling
```bash
python main.py
```
Wait for `Darling is online.` Then say **"Darling"** out loud, wait for it to reply "Yes?", then ask your question.

To stop: say **"Darling, stop listening"**, or press `Ctrl+C`.

---

## Every time you come back later (after today)

You don't need to repeat all the steps above — just:
```bash
cd ~/darling
source venv/bin/activate
python main.py
```

---

## How the pieces fit together

```
listener.py   -> hears you, converts speech to text (free, via Google's speech API)
brain.py      -> decides if it needs to search the web, then asks Gemini/Groq
speaker.py    -> converts the answer to speech and plays it (free, via edge-tts)
memory.py     -> saves every Q&A to data/darling_memory.db (SQLite) for recall later
main.py       -> the loop that ties it all together
```

## Free providers supported

| Provider | Get a key at | Notes |
|---|---|---|
| Gemini (default) | https://aistudio.google.com/apikey | No card needed, generous free tier |
| Groq | https://console.groq.com/keys | No card needed, very fast, runs Llama models |

To switch to Groq instead of Gemini, just change two lines in `.env`:
```
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key_here
```

## Things worth knowing

- **Wake word detection** works by checking if "darling" appears in what you say —
  simple and free. For a snappier, dedicated wake-word engine later, look at
  [Picovoice Porcupine](https://picovoice.ai/platform/porcupine/) (also has a free tier).
- **Speech-to-text** uses Google's free web API via `SpeechRecognition` — needs internet,
  no key required.
- **Real-time info** comes from DuckDuckGo search — free, no key needed.
- **Tune what counts as "needs a web search"** by editing `REALTIME_TRIGGERS` in `config.py`.
- **Memory** is local SQLite in `data/darling_memory.db`.

## Natural next upgrades (once this baseline works)

1. Swap Google STT -> local Whisper for offline + more accurate transcription
2. Swap the wake-word check -> Porcupine for instant, low-CPU wake detection
3. Turn `memory.py` into a FastAPI service with Postgres, so Darling can run on
   one machine and be queried/updated from others
4. Add a simple web dashboard (React/Vite) that shows live transcript + history
5. Add "interrupt while speaking" so you can cut Darling off mid-sentence
