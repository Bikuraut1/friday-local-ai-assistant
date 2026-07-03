import io
import html
import ctypes
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse
from xml.etree import ElementTree

import numpy as np
import requests
import sounddevice as sd
import soundfile as sf
import whisper
from dotenv import load_dotenv


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/Friday")
VOICE_ROOT = ROOT / "voice"
ENV_PATH = VOICE_ROOT / ".env"
load_dotenv(ENV_PATH)
load_dotenv(ROOT / "n8n" / ".env", override=False)
RECORDINGS = VOICE_ROOT / "recordings"
OPEN_WEBUI = os.getenv("FRIDAY_OPEN_WEBUI_URL", "http://localhost:3000")
OPEN_WEBUI_EMAIL = os.getenv("FRIDAY_OPENWEBUI_EMAIL")
OPEN_WEBUI_PASSWORD = os.getenv("FRIDAY_OPENWEBUI_PASSWORD")
OLLAMA = os.getenv("FRIDAY_OLLAMA_URL", "http://localhost:11434")
KOKORO = os.getenv("FRIDAY_KOKORO_URL", "http://localhost:8880/v1")
MEMORY_BRIDGE = os.getenv("FRIDAY_MEMORY_BRIDGE_URL", "http://localhost:8765")
MEMORY_START_SCRIPT = Path(os.getenv("FRIDAY_MEMORY_START_SCRIPT", str(ROOT / "mem0" / "start-memory.ps1")))
ROUTER_URL = os.getenv("FRIDAY_ROUTER_URL", "http://localhost:8790")
SEARXNG_URL = os.getenv("FRIDAY_SEARXNG_URL", "http://localhost:8081/search")
WAKEWORD_ROOT = Path(os.getenv("FRIDAY_OPENWAKEWORD_ROOT", str(VOICE_ROOT / "wakewords" / "openwakeword")))
WAKE_WORD_MODEL = Path(os.getenv("FRIDAY_WAKE_WORD_MODEL_PATH", str(VOICE_ROOT / "wakewords" / "hey_friday.onnx")))
WAKE_WORD_FALLBACK = os.getenv(
    "FRIDAY_WAKE_WORD_FALLBACK_MODEL",
    str(WAKEWORD_ROOT / "hey_jarvis_v0.1.onnx"),
)
USE_JARVIS_WAKE_WORD = os.getenv("FRIDAY_USE_JARVIS_WAKE_WORD", "1").lower() in {"1", "true", "yes"}
WAKE_THRESHOLD = float(os.getenv("FRIDAY_WAKE_WORD_THRESHOLD", "0.65"))
WAKE_CONFIRM_FRAMES = int(os.getenv("FRIDAY_WAKE_WORD_CONFIRM_FRAMES", "2"))
WAKE_COOLDOWN_SECONDS = float(os.getenv("FRIDAY_WAKE_WORD_COOLDOWN_SECONDS", "8.0"))
WAKE_POST_RESPONSE_MUTE_SECONDS = float(os.getenv("FRIDAY_WAKE_WORD_POST_RESPONSE_MUTE_SECONDS", "10.0"))
WAKE_DEBUG = os.getenv("FRIDAY_WAKE_DEBUG", "0").lower() in {"1", "true", "yes"}
WAKE_DEBUG_SCORE_THRESHOLD = float(os.getenv("FRIDAY_WAKE_DEBUG_SCORE_THRESHOLD", "0.35"))
SAMPLE_RATE = int(os.getenv("FRIDAY_VOICE_SAMPLE_RATE", "16000"))
SESSION_START_TIMEOUT_SECONDS = float(os.getenv("FRIDAY_SESSION_START_TIMEOUT_SECONDS", "20.0"))
SESSION_MAX_TURN_SECONDS = float(os.getenv("FRIDAY_SESSION_MAX_TURN_SECONDS", "25.0"))
SESSION_END_SILENCE_SECONDS = float(os.getenv("FRIDAY_SESSION_END_SILENCE_SECONDS", "0.45"))
SESSION_ENERGY_THRESHOLD = float(os.getenv("FRIDAY_SESSION_ENERGY_THRESHOLD", "420.0"))
SESSION_NOISE_MULTIPLIER = float(os.getenv("FRIDAY_SESSION_NOISE_MULTIPLIER", "3.5"))
SESSION_MIN_SPEECH_SECONDS = float(os.getenv("FRIDAY_SESSION_MIN_SPEECH_SECONDS", "0.45"))
SESSION_EMPTY_TURN_LIMIT = int(os.getenv("FRIDAY_SESSION_EMPTY_TURN_LIMIT", "2"))
SESSION_POST_SPEECH_MUTE_SECONDS = float(os.getenv("FRIDAY_SESSION_POST_SPEECH_MUTE_SECONDS", "0.15"))
SESSION_DUCK_AUDIO = os.getenv("FRIDAY_SESSION_DUCK_AUDIO", "1").lower() in {"1", "true", "yes"}
SESSION_DUCK_VOLUME_STEPS = int(os.getenv("FRIDAY_SESSION_DUCK_VOLUME_STEPS", "8"))
WAKE_ACK_TEXT = os.getenv("FRIDAY_WAKE_ACK_TEXT", "").strip()
STT_LANGUAGE = os.getenv("FRIDAY_STT_LANGUAGE", "auto").strip().lower()
STT_ENGINE = os.getenv("FRIDAY_STT_ENGINE", "local").strip().lower()
LOCAL_WHISPER_MODEL_NAME = os.getenv("FRIDAY_LOCAL_WHISPER_MODEL", "medium")
LOCAL_WHISPER_MODEL_DIR = Path(os.getenv("FRIDAY_LOCAL_WHISPER_MODEL_DIR", str(VOICE_ROOT / "whisper" / "models")))
STT_PROMPT = os.getenv(
    "FRIDAY_STT_PROMPT",
    "Transcribe assistant commands in Indian English, Hindi, or Hinglish. "
    "Use the same language and script as the speaker. "
    "Hindi examples should be written in Devanagari: क्रोम खोलो, आज की खबर सुनाओ, मौसम बताओ. "
    "Hinglish examples should stay romanized: Chrome kholo, aaj ka weather batao, gaana bajao. "
    "Do not invent repeated phrases like thank you, bye, happy new year, or subscribe.",
)
CHAT_MODEL = os.getenv("FRIDAY_CHAT_MODEL", "friday:phi4")
CHAT_KEEP_ALIVE = os.getenv("FRIDAY_CHAT_KEEP_ALIVE", "30m")
CHAT_NUM_PREDICT = int(os.getenv("FRIDAY_CHAT_NUM_PREDICT", "40"))
CHAT_TEMPERATURE = float(os.getenv("FRIDAY_CHAT_TEMPERATURE", "0.25"))
VOICE_USE_ROUTER = os.getenv("FRIDAY_VOICE_USE_ROUTER", "0").lower() in {"1", "true", "yes"}
VOICE_ALWAYS_MEMORY = os.getenv("FRIDAY_VOICE_ALWAYS_MEMORY", "0").lower() in {"1", "true", "yes"}
MEMORY_TOP_K = int(os.getenv("FRIDAY_MEMORY_TOP_K", "3"))
RAG_TOP_K = int(os.getenv("FRIDAY_RAG_TOP_K", "3"))
RAG_COLLECTION_CACHE_SECONDS = float(os.getenv("FRIDAY_RAG_COLLECTION_CACHE_SECONDS", "120.0"))
RAG_QUERY_TIMEOUT_SECONDS = float(os.getenv("FRIDAY_RAG_QUERY_TIMEOUT_SECONDS", "45.0"))
WEB_RESULT_COUNT = int(os.getenv("FRIDAY_WEB_RESULT_COUNT", "10"))
WEB_SPOKEN_RESULT_COUNT = int(os.getenv("FRIDAY_WEB_SPOKEN_RESULT_COUNT", "3"))
WEB_BLOCKED_DOMAINS = {
    "britannica.com",
    "india.gov.in",
    "merriam-webster.com",
    "dictionary.com",
    "wikipedia.org",
    "youtube.com",
    "youtu.be",
    "facebook.com",
    "msn.com",
    "x.com",
    "twitter.com",
}
NEWS_DOMAINS = [
    "indianexpress.com",
    "thehindu.com",
    "hindustantimes.com",
    "timesofindia.indiatimes.com",
    "indiatoday.in",
    "ndtv.com",
    "news18.com",
    "livemint.com",
    "economictimes.indiatimes.com",
    "business-standard.com",
    "moneycontrol.com",
    "firstpost.com",
    "scroll.in",
    "thewire.in",
    "news.abplive.com",
    "ddindia.co.in",
    "bbc.com",
    "reuters.com",
    "apnews.com",
]
NEWS_FEEDS = [
    ("Indian Express", "https://indianexpress.com/section/india/feed/"),
    ("The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"),
    ("India Today", "https://www.indiatoday.in/rss/1206584"),
    ("Hindustan Times", "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"),
    ("NDTV", "https://feeds.feedburner.com/ndtvnews-top-stories"),
    ("News18", "https://www.news18.com/rss/india.xml"),
]
NEWS_RSS_SKIP_PATTERNS = [
    "live updates",
    "breaking news live",
    "top 10 |",
    "afternoon bulletin",
    "morning bulletin",
    "evening bulletin",
    "morning digest",
    "school assembly",
    "weather today",
]
SOURCE_LABELS = {
    "indianexpress.com": "Indian Express",
    "thehindu.com": "The Hindu",
    "hindustantimes.com": "Hindustan Times",
    "timesofindia.indiatimes.com": "Times of India",
    "indiatoday.in": "India Today",
    "ndtv.com": "NDTV",
    "news18.com": "News18",
    "livemint.com": "Mint",
    "economictimes.indiatimes.com": "Economic Times",
    "business-standard.com": "Business Standard",
    "moneycontrol.com": "Moneycontrol",
    "news.abplive.com": "ABP Live",
    "ddindia.co.in": "DD India",
    "bbc.com": "BBC",
    "reuters.com": "Reuters",
    "apnews.com": "AP",
}
INDIAN_ENGLISH_STYLE = (
    "Primary speaking style: polished Indian English. Use clear, natural phrasing an Indian user would expect. "
    "Prefer India-local defaults: IST for time, India-first news and public context, INR for money, "
    "Indian date context, metric units, and local examples when the location is ambiguous. "
    "Keep responses concise, practical, and respectful. Do not imitate an accent with misspellings."
)
HINGLISH_STYLE = (
    "Hinglish support is secondary. Understand romanised Hindi/Hinglish commands, but reply in English unless "
    "Boss uses Hinglish first. When replying in Hinglish, keep it light and professional, never filmi or exaggerated."
)
VOICE_SYSTEM_PROMPT = os.getenv(
    "FRIDAY_VOICE_SYSTEM_PROMPT",
    "You are FRIDAY, Fully Responsive Intelligent Digital Assistant for You. "
    "Address the user as Boss. Never call yourself Assistant. "
    "Voice mode: answer in one concise sentence unless Boss asks for detail. "
    f"{INDIAN_ENGLISH_STYLE} {HINGLISH_STYLE} Do not use emojis or filler.",
)
TTS_MODEL = os.getenv("FRIDAY_TTS_MODEL", "kokoro")
TTS_VOICE = os.getenv("FRIDAY_TTS_VOICE", "af_bella")
TTS_FALLBACK_VOICE = os.getenv("FRIDAY_TTS_FALLBACK_VOICE", "bf_emma")
ALLOW_NON_ENGLISH_TTS = os.getenv("FRIDAY_ALLOW_NON_ENGLISH_TTS", "0").lower() in {"1", "true", "yes"}
STARTUP_GREETING = os.getenv(
    "FRIDAY_STARTUP_GREETING",
    "FRIDAY online. Ready when you are, Boss.",
).strip()
RAG_COLLECTION_CACHE = {"loaded_at": 0.0, "collections": []}
MEMORY_START_ATTEMPTED = False
LOCAL_STT_MODEL = None
LAST_DETECTED_STT_LANGUAGE = None


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def signin() -> str:
    if not OPEN_WEBUI_EMAIL or not OPEN_WEBUI_PASSWORD:
        die("Set FRIDAY_OPENWEBUI_EMAIL and FRIDAY_OPENWEBUI_PASSWORD in n8n/.env.")

    response = requests.post(
        f"{OPEN_WEBUI}/api/v1/auths/signin",
        json={"email": OPEN_WEBUI_EMAIL, "password": OPEN_WEBUI_PASSWORD},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["token"]


def write_wav(path: Path, pcm, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), pcm, sample_rate)


def resample_audio(audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate or len(audio) == 0:
        return audio.astype(np.float32, copy=False)
    duration = len(audio) / float(source_rate)
    target_len = max(1, int(round(duration * target_rate)))
    source_x = np.linspace(0.0, duration, num=len(audio), endpoint=False)
    target_x = np.linspace(0.0, duration, num=target_len, endpoint=False)
    return np.interp(target_x, source_x, audio).astype(np.float32)


def local_stt_model():
    global LOCAL_STT_MODEL
    if LOCAL_STT_MODEL is None:
        started_at = time.perf_counter()
        LOCAL_WHISPER_MODEL_DIR.mkdir(parents=True, exist_ok=True)
        LOCAL_STT_MODEL = whisper.load_model(LOCAL_WHISPER_MODEL_NAME, download_root=str(LOCAL_WHISPER_MODEL_DIR))
        print(f"Local STT model loaded: {LOCAL_WHISPER_MODEL_NAME} in {time.perf_counter() - started_at:.2f}s")
    return LOCAL_STT_MODEL


def stt_language_arg() -> str | None:
    return None if STT_LANGUAGE in {"", "auto", "detect"} else STT_LANGUAGE


def record_prompt(seconds: float = 6.0, sample_rate: int = SAMPLE_RATE) -> Path:
    print("Listening for command...")
    audio = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    path = RECORDINGS / f"command-{int(time.time())}.wav"
    write_wav(path, audio, sample_rate)
    return path


def rms_energy(pcm: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(pcm.astype(np.float32)))))


def calibrate_energy_threshold(sample_seconds: float = 0.6) -> float:
    frame_length = 1024
    frames_needed = max(1, int((SAMPLE_RATE * sample_seconds) / frame_length))
    energies = []

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=frame_length) as stream:
        for _ in range(frames_needed):
            frame, _ = stream.read(frame_length)
            pcm = np.asarray(frame, dtype=np.int16).reshape(-1)
            energies.append(rms_energy(pcm))

    noise_floor = float(np.median(energies)) if energies else 0.0
    threshold = max(SESSION_ENERGY_THRESHOLD, noise_floor * SESSION_NOISE_MULTIPLIER)
    print(f"Mic calibration: noise={noise_floor:.1f} threshold={threshold:.1f}")
    return threshold


def record_utterance() -> Path | None:
    frame_length = 1024
    frames = []
    speech_started = False
    silence_started = None
    started_at = time.time()
    speech_started_at = None
    speech_threshold = calibrate_energy_threshold()
    peak_energy = 0.0

    print("Listening...")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=frame_length) as stream:
        while True:
            frame, _ = stream.read(frame_length)
            now = time.time()
            pcm = np.asarray(frame, dtype=np.int16).reshape(-1)
            energy = rms_energy(pcm)
            peak_energy = max(peak_energy, energy)

            if not speech_started:
                if energy >= speech_threshold:
                    speech_started = True
                    speech_started_at = now
                    frames.append(pcm.copy())
                elif now - started_at >= SESSION_START_TIMEOUT_SECONDS:
                    return None
                continue

            frames.append(pcm.copy())

            if energy < speech_threshold:
                if silence_started is None:
                    silence_started = now
                if (
                    now - silence_started >= SESSION_END_SILENCE_SECONDS
                    and now - speech_started_at >= SESSION_MIN_SPEECH_SECONDS
                ):
                    break
            else:
                silence_started = None

            if now - speech_started_at >= SESSION_MAX_TURN_SECONDS:
                break

    if not frames:
        return None

    audio = np.concatenate(frames)
    duration = audio.shape[0] / SAMPLE_RATE
    if duration < SESSION_MIN_SPEECH_SECONDS:
        print(f"Ignored short capture: {duration:.2f}s peak={peak_energy:.1f}")
        return None

    path = RECORDINGS / f"command-{int(time.time())}.wav"
    write_wav(path, audio, SAMPLE_RATE)
    print(f"Recorded: {duration:.2f}s peak={peak_energy:.1f} file={path.name}")
    return path


def is_bad_transcript(text: str) -> bool:
    normalized = normalize_prompt(text)
    if not normalized:
        return True

    hallucination_markers = [
        "thank you for watching",
        "don't forget to subscribe",
        "happy new year",
        "see you in the next",
    ]
    if any(marker in normalized for marker in hallucination_markers):
        return True

    words = normalized.split()
    if len(words) >= 12:
        bye_count = sum(1 for word in words if word.strip(".,!?") in {"bye", "goodbye"})
        thank_count = sum(1 for word in words if word.strip(".,!?") in {"thank", "thanks"})
        if bye_count >= 4 or thank_count >= 4:
            return True

    return False


def transcribe(token: str, wav_path: Path) -> str:
    global LAST_DETECTED_STT_LANGUAGE
    started_at = time.perf_counter()
    try:
        language_arg = stt_language_arg()
        if STT_ENGINE == "local":
            audio, audio_rate = sf.read(str(wav_path), dtype="float32")
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)
            if audio_rate != SAMPLE_RATE:
                print(f"Local STT resampling {audio_rate} Hz audio to {SAMPLE_RATE} Hz.")
                audio = resample_audio(audio, audio_rate, SAMPLE_RATE)
            result = local_stt_model().transcribe(
                audio,
                language=language_arg,
                fp16=False,
                condition_on_previous_text=False,
                initial_prompt=STT_PROMPT,
                verbose=False,
            )
            LAST_DETECTED_STT_LANGUAGE = result.get("language") or language_arg or "unknown"
            text = str(result.get("text", "")).strip()
        else:
            with wav_path.open("rb") as audio_file:
                response = requests.post(
                    f"{OPEN_WEBUI}/api/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {token}"},
                    files={"file": (wav_path.name, audio_file, "audio/wav")},
                    data={"language": language_arg or "", "prompt": STT_PROMPT},
                    timeout=180,
            )
            response.raise_for_status()
            payload = response.json()
            LAST_DETECTED_STT_LANGUAGE = payload.get("language") or language_arg or "unknown"
            text = payload.get("text", "").strip()
        print(f"STT({STT_ENGINE}, language={LAST_DETECTED_STT_LANGUAGE}): {time.perf_counter() - started_at:.2f}s")
    except Exception as exc:
        print(f"STT failed: {exc}")
        return ""
    if is_bad_transcript(text):
        print(f"Ignored likely STT hallucination: {text}")
        return ""
    return text


def memory_bridge_healthy(timeout: float = 2.0) -> bool:
    try:
        response = requests.get(f"{MEMORY_BRIDGE}/health", timeout=timeout)
        response.raise_for_status()
        return bool(response.json().get("status"))
    except Exception:
        return False


def ensure_memory_bridge() -> bool:
    global MEMORY_START_ATTEMPTED
    if memory_bridge_healthy():
        return True
    if MEMORY_START_ATTEMPTED:
        return False
    MEMORY_START_ATTEMPTED = True
    if not MEMORY_START_SCRIPT.exists():
        print(f"Memory start script missing: {MEMORY_START_SCRIPT}")
        return False

    try:
        print("Memory bridge offline. Starting Mem0 bridge...")
        subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(MEMORY_START_SCRIPT),
            ],
            cwd=str(ROOT),
            timeout=45,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        print(f"Memory bridge auto-start failed: {exc}")
        return False

    for _ in range(10):
        if memory_bridge_healthy(timeout=3.0):
            print("Memory bridge online.")
            return True
        time.sleep(1)
    return False


def search_memory(query: str, category: str | None = None, top_k: int = MEMORY_TOP_K) -> list[str]:
    try:
        if not ensure_memory_bridge():
            print("Memory search skipped: bridge unavailable.")
            return []
        payload = {"query": query, "top_k": top_k}
        if category:
            payload["category"] = category
        response = requests.post(f"{MEMORY_BRIDGE}/memory/search", json=payload, timeout=12)
        response.raise_for_status()
        items = response.json().get("results", [])
        memories = []
        for item in items:
            memory = item.get("memory") or item.get("text") or item.get("raw")
            if memory and memory not in memories:
                memories.append(memory)
        return memories
    except Exception as exc:
        print(f"Memory search skipped: {exc}")
        return []


def add_memory(text: str, category: str, source: str = "voice") -> None:
    try:
        if not ensure_memory_bridge():
            print("Memory store skipped: bridge unavailable.")
            return
        response = requests.post(
            f"{MEMORY_BRIDGE}/memory",
            json={"text": text, "category": category, "source": source, "infer": False},
            timeout=20,
        )
        response.raise_for_status()
        print(f"Memory stored: {category} | {text}")
    except Exception as exc:
        print(f"Memory store skipped: {exc}")


def maybe_store_profile_fact(prompt: str) -> None:
    normalized = normalize_prompt(prompt)
    match = re.search(r"\b(?:my name is|call me)\s+([a-z][a-z]+(?:\s+[a-z][a-z]+){0,3})\b", normalized)
    if not match:
        return

    name = " ".join(part.capitalize() for part in match.group(1).split())
    blocked_names = {
        "friday",
        "jarvis",
        "boss",
        "assistant",
        "going",
        "going to",
        "going to turn",
    }
    if name.lower() in blocked_names:
        return
    add_memory(f"Boss's name is {name}.", "USER_PROFILE", source="voice-profile")


def memory_context_for(prompt: str) -> list[str]:
    if not should_query_memory(prompt):
        return []
    memories = search_memory(prompt)
    if any(word in normalize_prompt(prompt) for word in ["name", "who am i", "know me"]):
        for memory in search_memory("Boss name identity user profile", category="USER_PROFILE"):
            if memory not in memories:
                memories.append(memory)
    return memories[:MEMORY_TOP_K]


def should_query_memory(prompt: str) -> bool:
    if VOICE_ALWAYS_MEMORY:
        return True
    normalized = normalize_prompt(prompt)
    markers = {
        "who am i",
        "do you know me",
        "my name",
        "what is my name",
        "what's my name",
        "remember",
        "memory",
        "preference",
        "goal",
        "project",
        "follow up",
        "follow-up",
    }
    return any(marker in normalized for marker in markers)


def rag_collections(token: str) -> list[str]:
    now = time.time()
    cached = RAG_COLLECTION_CACHE["collections"]
    if cached and now - float(RAG_COLLECTION_CACHE["loaded_at"]) < RAG_COLLECTION_CACHE_SECONDS:
        return list(cached)

    try:
        response = requests.get(
            f"{OPEN_WEBUI}/api/v1/files/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except Exception as exc:
        print(f"RAG collection lookup skipped: {exc}")
        return []

    collections = []
    for item in items:
        data = item.get("data") or {}
        meta = item.get("meta") or {}
        collection_name = meta.get("collection_name")
        if data.get("status") != "completed" or not collection_name:
            continue
        if collection_name not in collections:
            collections.append(collection_name)

    RAG_COLLECTION_CACHE["loaded_at"] = now
    RAG_COLLECTION_CACHE["collections"] = collections
    return collections


def normalize_rag_results(payload: dict) -> list[str]:
    documents = payload.get("documents") or []
    metadatas = payload.get("metadatas") or []
    snippets = []

    for group_index, document_group in enumerate(documents):
        metadata_group = metadatas[group_index] if group_index < len(metadatas) else []
        for doc_index, document in enumerate(document_group or []):
            text = re.sub(r"\s+", " ", document or "").strip()
            if not text:
                continue
            metadata = metadata_group[doc_index] if doc_index < len(metadata_group) else {}
            source = metadata.get("source") or metadata.get("name") or "knowledge-base"
            snippet = f"{text[:700]} Source: {source}"
            if snippet not in snippets:
                snippets.append(snippet)
            if len(snippets) >= RAG_TOP_K:
                return snippets

    return snippets


def query_rag_collection(token: str, prompt: str, collections: list[str]) -> list[str]:
    if not collections:
        return []

    body = {
        "collection_names": collections,
        "query": prompt,
        "k": max(RAG_TOP_K, 3),
        "hybrid": True,
        "hybrid_bm25_weight": 0.45,
        "enable_enriched_texts": True,
    }
    response = requests.post(
        f"{OPEN_WEBUI}/api/v1/retrieval/query/collection",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=RAG_QUERY_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return normalize_rag_results(response.json())


def should_query_rag(prompt: str) -> bool:
    normalized = normalize_prompt(prompt)
    rag_markers = {
        "knowledge base",
        "document",
        "documents",
        "file",
        "files",
        "pdf",
        "docx",
        "note",
        "notes",
        "uploaded",
        "source",
        "sources",
        "according to",
        "from my",
        "in my knowledge",
        "rag",
        "phase 4",
        "codename",
        "verification phrase",
    }
    return any(marker in normalized for marker in rag_markers)


def rag_context_for(token: str | None, prompt: str) -> list[str]:
    if not token or not should_query_rag(prompt):
        return []

    collections = rag_collections(token)
    if not collections:
        return []

    started_at = time.perf_counter()
    try:
        snippets = query_rag_collection(token, prompt, collections)
    except Exception as exc:
        print(f"RAG batch query failed, retrying per collection: {exc}")
        snippets = []
        for collection in collections:
            try:
                for snippet in query_rag_collection(token, prompt, [collection]):
                    if snippet not in snippets:
                        snippets.append(snippet)
                    if len(snippets) >= RAG_TOP_K:
                        break
            except Exception as inner_exc:
                print(f"RAG collection skipped: {collection}: {inner_exc}")
            if len(snippets) >= RAG_TOP_K:
                break

    if snippets:
        print(f"RAG: {time.perf_counter() - started_at:.2f}s snippets={len(snippets)} collections={len(collections)}")
    return snippets[:RAG_TOP_K]


def should_search_web(prompt: str) -> bool:
    normalized = normalize_prompt(prompt)
    current_markers = {
        "today",
        "latest",
        "current",
        "news",
        "khabar",
        "samachar",
        "taaza",
        "taza",
        "headlines",
        "breaking",
        "weather",
        "mausam",
        "price",
        "stock",
        "score",
    }
    return any(marker in normalized for marker in current_markers)


def is_news_prompt(prompt: str) -> bool:
    normalized = normalize_prompt(prompt)
    return any(marker in normalized for marker in {"news", "headline", "headlines", "khabar", "samachar"})


def is_weather_prompt(prompt: str) -> bool:
    normalized = normalize_prompt(prompt)
    return "weather" in normalized or "mausam" in normalized


def requested_result_count(prompt: str, default: int = WEB_SPOKEN_RESULT_COUNT) -> int:
    match = re.search(r"\btop\s+(\d{1,2})\b", normalize_prompt(prompt))
    if not match:
        return default
    return max(1, min(int(match.group(1)), WEB_RESULT_COUNT))


def build_web_query(prompt: str) -> str:
    normalized = normalize_prompt(prompt)
    today = datetime.now().strftime("%B %d %Y")
    if is_news_prompt(prompt):
        return f"India breaking news headlines {today}"
    if is_weather_prompt(prompt):
        if normalized in {"weather", "today weather", "mausam", "today mausam"}:
            return f"India weather today {today}"
        return f"{normalized} India {today}"
    return f"{prompt} {today}"


def source_name(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host.split(":")[0]


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title or "").strip()
    title = re.sub(r"\s*[-|]\s*(Google News|YouTube)$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*\.\.\.$", "", title)
    title = re.sub(r"\s*[-|]\s*(The Hindu|Hindustan Times|The Indian Express|Times of India|India Today|NDTV|News18|ABP LIVE|DD India)$", "", title, flags=re.IGNORECASE)
    return title


def short_title(title: str, max_words: int = 12) -> str:
    words = clean_title(title).split()
    if len(words) <= max_words:
        return " ".join(words).strip(" ,.-")
    return " ".join(words[:max_words]).strip(" ,.-")


def source_label(source: str) -> str:
    for domain, label in SOURCE_LABELS.items():
        if source == domain or source.endswith(f".{domain}"):
            return label
    return source


def is_generic_news_title(title: str) -> bool:
    lowered = title.lower()
    generic_patterns = [
        "top headlines today",
        "real-time news",
        "home |",
        "national portal",
        "history, maps",
        "weather today",
        "temperature and air quality",
        "school assembly",
        "archives |",
        "horoscope",
        "definition & meaning",
    ]
    return any(pattern in lowered for pattern in generic_patterns)


def is_rss_news_skip_title(title: str) -> bool:
    lowered = title.lower()
    return is_generic_news_title(title) or any(pattern in lowered for pattern in NEWS_RSS_SKIP_PATTERNS)


def rss_child_text(item: ElementTree.Element, child_name: str) -> str:
    child = item.find(child_name)
    if child is not None and child.text:
        return re.sub(r"\s+", " ", child.text).strip()
    return ""


def clean_news_summary(summary: str) -> str:
    summary = html.unescape(summary or "")
    summary = re.sub(r"<[^>]+>", " ", summary)
    summary = re.sub(r"\s+", " ", summary).strip()
    return summary.strip(" -|")


def rss_item_summary(item: ElementTree.Element) -> str:
    summary = rss_child_text(item, "description")
    if not summary:
        for child in item:
            if child.tag.lower().endswith("encoded") and child.text:
                summary = child.text
                break
    return clean_news_summary(summary)


def fetch_article_summary(url: str) -> str:
    if not url:
        return ""
    try:
        response = requests.get(url, headers={"User-Agent": "FRIDAY-local-news/1.0"}, timeout=8)
        response.raise_for_status()
    except Exception:
        return ""

    page = response.text
    patterns = [
        r"<meta\s+[^>]*(?:name|property)=[\"'](?:description|og:description|twitter:description)[\"'][^>]*content=[\"']([^\"']+)[\"'][^>]*>",
        r"<meta\s+[^>]*content=[\"']([^\"']+)[\"'][^>]*(?:name|property)=[\"'](?:description|og:description|twitter:description)[\"'][^>]*>",
    ]
    for pattern in patterns:
        match = re.search(pattern, page, flags=re.IGNORECASE)
        if match:
            return clean_news_summary(match.group(1))
    return ""


def fetch_news_feed_headlines(limit: int) -> list[dict[str, str]]:
    started_at = time.perf_counter()
    feed_results = []
    seen_titles = set()
    headers = {"User-Agent": "FRIDAY-local-news/1.0"}

    for source, feed_url in NEWS_FEEDS:
        source_results = []
        try:
            response = requests.get(feed_url, headers=headers, timeout=12)
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
        except Exception as exc:
            print(f"News feed failed: {source}: {exc}")
            continue

        for item in root.findall(".//item")[:20]:
            title = clean_title(rss_child_text(item, "title"))
            link = rss_child_text(item, "link")
            summary = rss_item_summary(item)
            if not title or is_rss_news_skip_title(title):
                continue
            title_key = title.lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            source_results.append({"title": title, "url": link, "source": source, "snippet": summary})
            if len(source_results) >= limit:
                break
        if source_results:
            feed_results.append(source_results)

    results = []
    for index in range(limit):
        added_this_round = False
        for source_results in feed_results:
            if index >= len(source_results):
                continue
            results.append(source_results[index])
            added_this_round = True
            if len(results) >= limit:
                break
        if len(results) >= limit or not added_this_round:
            break

    print(f"News feeds: {time.perf_counter() - started_at:.2f}s results={len(results)}")
    return results


def is_current_year_result(title: str, url: str) -> bool:
    current_year = str(datetime.now().year)
    years = set(re.findall(r"\b20\d{2}\b", f"{title} {url}"))
    return not years or current_year in years


def search_web_results(prompt: str) -> list[dict[str, str]]:
    query = build_web_query(prompt)
    count = max(WEB_RESULT_COUNT, requested_result_count(prompt))
    news_mode = is_news_prompt(prompt)
    started_at = time.perf_counter()
    try:
        params = {"q": query, "format": "json", "language": "en"}
        if news_mode:
            params["categories"] = "news"
        response = requests.get(
            SEARXNG_URL,
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        raw_results = response.json().get("results", [])
    except Exception as exc:
        print(f"Web search failed: {exc}")
        return []

    results = []
    seen_titles = set()
    seen_sources = set()
    seen_urls = set()
    for item in raw_results:
        title = clean_title(item.get("title", ""))
        url = item.get("url", "")
        source = source_name(url)
        canonical_url = url.split("?", 1)[0].rstrip("/")
        if source in WEB_BLOCKED_DOMAINS or any(source.endswith(f".{domain}") for domain in WEB_BLOCKED_DOMAINS):
            continue
        if news_mode and not any(source == domain or source.endswith(f".{domain}") for domain in NEWS_DOMAINS):
            continue
        if news_mode and source in seen_sources:
            continue
        if news_mode and is_generic_news_title(title):
            continue
        if news_mode and not is_current_year_result(title, url):
            continue
        if "definition & meaning" in title.lower():
            continue
        if not title or title.lower() in seen_titles or canonical_url in seen_urls:
            continue
        seen_titles.add(title.lower())
        seen_urls.add(canonical_url)
        seen_sources.add(source)
        results.append(
            {
                "title": title,
                "url": url,
                "source": source,
                "snippet": re.sub(r"\s+", " ", item.get("content", "")).strip(),
            }
        )
        if len(results) >= count:
            break

    print(f"Web search: {time.perf_counter() - started_at:.2f}s query={query!r} results={len(results)}")
    return results


def web_fast_reply(prompt: str) -> str | None:
    if not should_search_web(prompt):
        return None

    news_mode = is_news_prompt(prompt)
    requested = requested_result_count(prompt)
    spoken_limit = min(requested, WEB_RESULT_COUNT) if news_mode else WEB_SPOKEN_RESULT_COUNT
    results = []
    if news_mode:
        results = fetch_news_feed_headlines(spoken_limit)
    if len(results) < spoken_limit:
        fallback_results = search_web_results(prompt)
        seen_titles = {item["title"].lower() for item in results}
        for item in fallback_results:
            if item["title"].lower() in seen_titles:
                continue
            results.append(item)
            seen_titles.add(item["title"].lower())
            if len(results) >= spoken_limit:
                break

    if not results:
        return "I could not reach local web search right now, Boss."

    spoken_count = min(requested, spoken_limit, len(results))
    lines = []
    for index, item in enumerate(results[:spoken_count], start=1):
        title = clean_title(item["title"]) if news_mode else short_title(item["title"], 9)
        snippet = item.get("snippet", "")
        if news_mode and not snippet:
            snippet = fetch_article_summary(item.get("url", ""))
            item["snippet"] = snippet
        if news_mode and snippet:
            lines.append(f"{index}. {source_label(item['source'])}: {title}. {snippet}")
        else:
            lines.append(f"{index}. {source_label(item['source'])}: {title}")

    if requested > spoken_count:
        intro = f"I found {min(requested, len(results))} current news items. Speaking the top {spoken_count}:"
    else:
        intro = f"Here are the top {spoken_count} current news items:"
    return intro + "\n" + "\n".join(lines)


def chat(prompt: str, history: list[dict[str, str]] | None = None, token: str | None = None) -> str:
    messages = history if history is not None else []
    memories = memory_context_for(prompt)
    rag_snippets = rag_context_for(token, prompt)
    system_content = VOICE_SYSTEM_PROMPT
    if uses_hinglish(prompt):
        system_content += "\nBoss used Hinglish in this turn. A short, natural Hinglish reply is allowed, but keep it professional."
    else:
        system_content += "\nBoss used English in this turn. Reply in polished Indian English."
    if memories:
        system_content += "\nKnown memory about Boss:\n" + "\n".join(f"- {memory}" for memory in memories)
    if rag_snippets:
        system_content += (
            "\nRelevant personal knowledge-base context. Use it when it answers Boss's question. "
            "Mention the source name only when Boss asks for sources or the answer depends on a retrieved document:\n"
            + "\n".join(f"- {snippet}" for snippet in rag_snippets)
        )

    if messages and messages[0].get("role") == "system":
        messages[0]["content"] = system_content
    else:
        messages.insert(0, {"role": "system", "content": system_content})

    messages.append({"role": "user", "content": prompt})
    selected_model = CHAT_MODEL
    if VOICE_USE_ROUTER or should_use_router(prompt):
        try:
            route_response = requests.post(
                f"{ROUTER_URL}/route",
                json={"prompt": prompt},
                timeout=5,
            )
            route_response.raise_for_status()
            decision = route_response.json().get("decision") or {}
            routed_model = decision.get("model")
            routed_route = decision.get("route")
            if routed_model and routed_route != "image":
                selected_model = routed_model
            print(f"Router: route={routed_route} model={selected_model}")
        except Exception as exc:
            print(f"Router skipped: {exc}")

    started_at = time.perf_counter()
    response = requests.post(
        f"{OLLAMA}/api/chat",
        json={
            "model": selected_model,
            "stream": False,
            "keep_alive": CHAT_KEEP_ALIVE,
            "options": {
                "num_predict": CHAT_NUM_PREDICT,
                "temperature": CHAT_TEMPERATURE,
            },
            "messages": messages,
        },
        timeout=300,
    )
    response.raise_for_status()
    answer = response.json()["message"]["content"].strip()
    print(f"LLM: {time.perf_counter() - started_at:.2f}s")
    messages.append({"role": "assistant", "content": answer})
    if len(messages) > 20:
        del messages[:-20]
    return answer


def should_use_router(prompt: str) -> bool:
    normalized = normalize_prompt(prompt)
    markers = {
        "complex",
        "reason",
        "architecture",
        "strategy",
        "analyze",
        "debug",
        "code",
        "script",
        "image",
        "screenshot",
    }
    return any(marker in normalized for marker in markers)


def speak(text: str) -> None:
    started_at = time.perf_counter()
    voices = [TTS_VOICE, TTS_FALLBACK_VOICE, "af_bella"]
    if not ALLOW_NON_ENGLISH_TTS:
        voices = [voice for voice in voices if re.match(r"^[ab][fm]_", voice or "")]
        if TTS_VOICE not in voices:
            print(f"TTS voice rejected for English speech: {TTS_VOICE}")
    last_error = None
    try:
        response = None
        for voice in dict.fromkeys(voice for voice in voices if voice):
            try:
                response = requests.post(
                    f"{KOKORO}/audio/speech",
                    json={
                        "model": TTS_MODEL,
                        "voice": voice,
                        "input": text,
                        "response_format": "wav",
                    },
                    timeout=180,
                )
                response.raise_for_status()
                if voice != TTS_VOICE:
                    print(f"TTS fallback voice used: {voice}")
                break
            except Exception as exc:
                last_error = exc
                response = None
        if response is None:
            raise last_error or RuntimeError("No TTS voice was accepted.")
        data, sample_rate = sf.read(io.BytesIO(response.content), dtype="float32")
        sd.play(data, sample_rate)
        sd.wait()
        print(f"TTS+playback: {time.perf_counter() - started_at:.2f}s")
    except Exception as exc:
        print(f"TTS failed, keeping listener alive: {exc}")


def should_exit(prompt: str) -> bool:
    normalized = normalize_prompt(prompt)
    return normalized in {
        "goodbye",
        "bye",
        "exit",
        "quit",
        "stop",
        "stop listening",
        "go to sleep",
        "sleep",
        "shutdown listener",
        "shut down listener",
    }


def normalize_indian_english(text: str) -> str:
    normalized = text.strip().lower().rstrip(".!?")
    normalized = re.sub(r"\s+", " ", normalized)
    replacements = [
        (r"\bwhat'?s\b", "what is"),
        (r"\bpls\b", "please"),
        (r"\bopen google\b", "open chrome"),
        (r"\bweather today\b", "today weather"),
        (r"\bheadlines today\b", "today headlines"),
        (r"\btoday'?s\b", "today"),
    ]
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized)
    return re.sub(r"\s+", " ", normalized).strip()


HINGLISH_MARKERS = {
    "aaj",
    "abhi",
    "band",
    "bandh",
    "batao",
    "bajao",
    "chalao",
    "dikhao",
    "gaana",
    "gana",
    "hai",
    "hoon",
    "karo",
    "kar",
    "kaun",
    "khabar",
    "khabrein",
    "khol",
    "kholo",
    "lagao",
    "mausam",
    "mera",
    "naam",
    "pichla",
    "pichhla",
    "rok",
    "samachar",
    "taaza",
    "taza",
    "tum",
    "tumhara",
}


def uses_hinglish(prompt: str) -> bool:
    words = set(re.findall(r"[a-z]+", prompt.lower()))
    return bool(words & HINGLISH_MARKERS)


def normalize_hinglish_aliases(text: str) -> str:
    normalized = text
    replacements = [
        (r"\b(chrome|google chrome)\s+(khol do|kholo|open karo|open kar do)\b", "open chrome"),
        (r"\b(khol do|kholo|open karo|open kar do)\s+(chrome|google chrome)\b", "open chrome"),
        (r"\byoutube\s+(khol do|kholo|open karo|open kar do)\b", "open youtube"),
        (r"\b(khol do|kholo|open karo|open kar do)\s+youtube\b", "open youtube"),
        (r"\bspotify\s+(khol do|kholo|open karo|open kar do)\b", "open spotify"),
        (r"\b(khol do|kholo|open karo|open kar do)\s+spotify\b", "open spotify"),
        (r"\b(play|chalao|lagao|bajao)\s+(gaana|gana|song|music)\b", "play song"),
        (r"\b(gaana|gana|song|music)\s+(chalao|lagao|bajao)\b", "play song"),
        (r"\bnext\s+(gaana|gana)\b", "next song"),
        (r"\b(pichla|pichhla|peeche wala|last)\s+(gaana|gana|song)\b", "previous song"),
        (r"\b(pause karo|rok do|hold karo)\b", "pause"),
        (r"\b(resume karo|continue karo)\b", "resume"),
        (r"\b(music|song|gaana|gana)\s+(band karo|band kar do|bandh karo|stop karo)\b", "stop music"),
        (r"\b(aaj ki|aaj ka|aaj ke|aaj)\b", "today"),
        (r"\b(taaza|taza)\b", "latest"),
        (r"\b(khabrein|khabar|samachar)\b", "news"),
        (r"\bmausam\b", "weather"),
        (r"\bmain kaun hoon\b", "who am i"),
        (r"\bmera naam kya hai\b", "what is my name"),
        (r"\btum kaun ho\b", "who are you"),
        (r"\btumhara naam kya hai\b", "what is your name"),
        (r"\b(dikhao|batao)\b", " "),
        (r"\bplease\b", " "),
    ]
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_prompt(prompt: str) -> str:
    return normalize_hinglish_aliases(normalize_indian_english(prompt))


def voice_reply(prompt: str, english: str, hinglish: str | None = None) -> str:
    if hinglish and uses_hinglish(prompt):
        return hinglish
    return english


def should_ignore_prompt(prompt: str) -> bool:
    normalized = normalize_prompt(prompt)
    return normalized in {"friday", "hey friday", "hey jarvis", "jarvis"}


VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
KEYEVENTF_KEYUP = 0x0002


def press_windows_key(vk_code: int, presses: int = 1, delay: float = 0.03) -> None:
    for _ in range(max(1, presses)):
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(delay)


def duck_system_audio() -> int:
    if not SESSION_DUCK_AUDIO or SESSION_DUCK_VOLUME_STEPS <= 0:
        return 0
    press_windows_key(VK_VOLUME_DOWN, presses=SESSION_DUCK_VOLUME_STEPS, delay=0.01)
    print(f"Audio ducked: {SESSION_DUCK_VOLUME_STEPS} steps")
    return SESSION_DUCK_VOLUME_STEPS


def restore_system_audio(steps: int) -> None:
    if steps <= 0:
        return
    press_windows_key(VK_VOLUME_UP, presses=steps, delay=0.01)
    print(f"Audio restored: {steps} steps")


def media_play_pause() -> None:
    press_windows_key(VK_MEDIA_PLAY_PAUSE)


def media_stop() -> None:
    press_windows_key(VK_MEDIA_STOP)


def media_next() -> None:
    press_windows_key(VK_MEDIA_NEXT_TRACK)


def media_previous() -> None:
    press_windows_key(VK_MEDIA_PREV_TRACK)


def chrome_executable() -> str | None:
    chrome_candidates = [
        os.getenv("FRIDAY_CHROME_PATH", ""),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    for candidate in chrome_candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def open_chrome(url: str | None = None) -> bool:
    chrome = chrome_executable()
    if chrome:
        command = [chrome]
        if url:
            command.append(url)
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True

    if url:
        subprocess.Popen(
            ["cmd", "/c", "start", "", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True

    subprocess.Popen(
        ["cmd", "/c", "start", "", "chrome"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True


def youtube_watch_url_for(query: str) -> str | None:
    try:
        response = requests.get(
            "https://www.youtube.com/results",
            params={"search_query": query},
            headers={"User-Agent": "Mozilla/5.0 FRIDAY-local-voice/1.0"},
            timeout=12,
        )
        response.raise_for_status()
    except Exception as exc:
        print(f"YouTube resolve failed: {exc}")
        return None

    for video_id in re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', response.text):
        return f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
    return None


def open_youtube_play(query: str) -> bool:
    watch_url = youtube_watch_url_for(query)
    if watch_url:
        print(f"YouTube resolved: {query!r} -> {watch_url}")
        return open_chrome(watch_url)
    return open_chrome(f"https://www.youtube.com/results?search_query={quote(query)}")


def media_query_from_prompt(normalized: str, service: str) -> str:
    query = normalized
    query = re.sub(r"\b(open|launch)\s+chrome\s+(and\s+)?", " ", query)
    query = re.sub(rf"\b(open|launch)\s+{service}\s+(and\s+)?", " ", query)
    query = re.sub(rf"\b(on|in)\s+{service}\b", " ", query)
    query = re.sub(rf"\b{service}\b", " ", query)
    query = re.sub(r"\bsongs?\s+(by|of|from)\b", " ", query)
    query = re.sub(r"\b(by|from)\s+(singer|artist)\b", " ", query)
    query = re.sub(r"\b(open|launch|play|search|for|please|chalao|lagao|bajao|khol do|kholo)\b", " ", query)
    query = re.sub(r"\b(a|the)\s+song\b", " ", query)
    query = re.sub(r"\b(singer|artist|songs|song|music|gaana|gana|ka|ki|ke)\b", " ", query)
    query = re.sub(r"\s+", " ", query).strip(" .,!?:;")
    return query or "popular songs"


def handle_media_command(prompt: str) -> str | None:
    normalized = normalize_prompt(prompt)
    wants_play = bool(re.search(r"\b(play|song|music)\b", normalized))
    wants_media_search = bool(re.search(r"\bsearch\b", normalized) and re.search(r"\b(song|songs|music|singer|artist)\b", normalized))

    if normalized in {"pause", "pause music", "pause song", "pause playback", "hold music"}:
        media_play_pause()
        return voice_reply(prompt, "Playback paused, Boss.", "Playback pause kar diya, Boss.")

    if normalized in {"resume", "resume music", "resume song", "continue music", "continue song"}:
        media_play_pause()
        return voice_reply(prompt, "Playback resumed, Boss.", "Playback resume kar diya, Boss.")

    if normalized in {"play", "play music", "play song", "start music", "start song"}:
        media_play_pause()
        return voice_reply(prompt, "Playback toggled, Boss.", "Music toggle kar diya, Boss.")

    if normalized in {"play a song", "play some music"}:
        open_youtube_play("popular songs")
        return voice_reply(prompt, "Playing popular songs on YouTube, Boss.", "YouTube par gaana chala raha hoon, Boss.")

    if normalized in {"stop music", "stop song", "stop playback"}:
        media_stop()
        return voice_reply(prompt, "Playback stopped, Boss.", "Music band kar diya, Boss.")

    if normalized in {"next", "next song", "next track", "skip", "skip song"}:
        media_next()
        return voice_reply(prompt, "Skipped to the next track, Boss.", "Next track chala diya, Boss.")

    if normalized in {"previous", "previous song", "previous track", "back song", "last song"}:
        media_previous()
        return voice_reply(prompt, "Went back to the previous track, Boss.", "Previous track par aa gaya, Boss.")

    if "youtube" in normalized:
        if wants_play:
            query = media_query_from_prompt(normalized, "youtube")
            open_youtube_play(query)
            return voice_reply(prompt, f"Playing {query} on YouTube, Boss.", f"YouTube par {query} chala raha hoon, Boss.")
        if re.search(r"\b(open|launch)\b", normalized):
            open_chrome("https://www.youtube.com")
            return voice_reply(prompt, "YouTube is open, Boss.", "YouTube khol diya, Boss.")

    if "spotify" in normalized:
        if wants_play:
            query = media_query_from_prompt(normalized, "spotify")
            open_chrome(f"https://open.spotify.com/search/{quote(query)}")
            return voice_reply(prompt, f"Opened Spotify search for {query}, Boss.", f"Spotify par {query} search khol diya, Boss.")
        if re.search(r"\b(open|launch)\b", normalized):
            open_chrome("https://open.spotify.com")
            return voice_reply(prompt, "Spotify is open, Boss.", "Spotify khol diya, Boss.")

    if wants_play and "chrome" in normalized:
        query = media_query_from_prompt(normalized, "youtube")
        open_youtube_play(query)
        return voice_reply(prompt, f"Playing {query} on YouTube, Boss.", f"YouTube par {query} chala raha hoon, Boss.")

    if (wants_play and normalized.startswith("play ")) or wants_media_search:
        query = media_query_from_prompt(normalized, "youtube")
        open_youtube_play(query)
        return voice_reply(prompt, f"Playing {query} on YouTube, Boss.", f"YouTube par {query} chala raha hoon, Boss.")

    return None


def local_fast_reply(prompt: str) -> str | None:
    normalized = normalize_prompt(prompt)
    media_reply = handle_media_command(prompt)
    if media_reply:
        return media_reply
    if normalized in {"open chrome", "launch chrome", "open google chrome", "launch google chrome"}:
        if open_chrome():
            return voice_reply(prompt, "Chrome is open, Boss.", "Chrome khol diya, Boss.")
        return voice_reply(prompt, "I could not open Chrome, Boss.", "Chrome nahi khul paya, Boss.")
    if normalized in {"who are you", "what are you"}:
        return voice_reply(prompt, "I'm FRIDAY, your local personal AI assistant, Boss.", "Main FRIDAY hoon, aapka local personal AI assistant, Boss.")
    if normalized in {"what's your name", "what is your name", "your name"}:
        return voice_reply(prompt, "My name is FRIDAY, Boss.", "Mera naam FRIDAY hai, Boss.")
    if normalized in {"who am i", "do you know me"}:
        for memory in search_memory("Boss name identity user profile", category="USER_PROFILE"):
            if "name is" in memory.lower():
                return memory.replace("Boss's", "Your").replace("Boss", "You")
        return voice_reply(
            prompt,
            "You're Boss, the person this local FRIDAY system is being built for.",
            "Aap Boss hain, jinke liye yeh local FRIDAY system ban raha hai.",
        )
    return None


def run_interactive_session(token: str) -> bool:
    history: list[dict[str, str]] = [{"role": "system", "content": VOICE_SYSTEM_PROMPT}]
    empty_turns = 0
    duck_steps = 0

    if WAKE_ACK_TEXT:
        speak(WAKE_ACK_TEXT)
        time.sleep(SESSION_POST_SPEECH_MUTE_SECONDS)
    duck_steps = duck_system_audio()

    try:
        while True:
            wav_path = record_utterance()
            if wav_path is None:
                empty_turns += 1
                if empty_turns >= SESSION_EMPTY_TURN_LIMIT:
                    speak("Going quiet, Boss.")
                    print("Session idle. Returning to wake-word mode.")
                    return True
                print("No speech detected. Still listening...")
                continue

            empty_turns = 0
            prompt = transcribe(token, wav_path)
            if not prompt:
                print("No transcript returned.")
                empty_turns += 1
                if empty_turns >= SESSION_EMPTY_TURN_LIMIT:
                    speak("I am not catching speech clearly. Going quiet, Boss.")
                    print("Session ended after empty transcripts. Returning to wake-word mode.")
                    return True
                continue

            empty_turns = 0
            print(f"Boss: {prompt}")
            if should_ignore_prompt(prompt):
                print("Ignored wake-word residue.")
                continue
            maybe_store_profile_fact(prompt)
            if should_exit(prompt):
                speak("Standing by, Boss.")
                print("Session ended. Returning to wake-word mode.")
                return True

            answer = local_fast_reply(prompt) or web_fast_reply(prompt) or chat(prompt, history, token)
            print(f"FRIDAY: {answer}")
            speak(answer)
            time.sleep(SESSION_POST_SPEECH_MUTE_SECONDS)
    finally:
        restore_system_audio(duck_steps)


def build_wake_model():
    from openwakeword.model import Model

    if USE_JARVIS_WAKE_WORD and Path(WAKE_WORD_FALLBACK).exists():
        wake_model_path = Path(WAKE_WORD_FALLBACK)
        wake_phrase = "Hey Jarvis"
        if WAKE_WORD_MODEL.exists():
            print(f"Using bundled Jarvis wake model instead of custom Friday model: {WAKE_WORD_MODEL}")
    elif WAKE_WORD_MODEL.exists():
        wake_model_path = WAKE_WORD_MODEL
        wake_phrase = "Hey Friday"
    elif Path(WAKE_WORD_FALLBACK).exists():
        wake_model_path = Path(WAKE_WORD_FALLBACK)
        wake_phrase = "Hey Jarvis"
        print(f"Hey Friday model not found: {WAKE_WORD_MODEL}")
        print(f"Using bundled openWakeWord fallback: {wake_model_path}")
    else:
        die(
            "No openWakeWord model found. Run "
            "D:\\Friday\\voice\\.venv\\Scripts\\python.exe "
            "-c \"from openwakeword.utils import download_models; "
            "download_models(['hey_jarvis'], target_directory=r'D:\\Friday\\voice\\wakewords\\openwakeword')\""
        )

    model = Model(
        wakeword_models=[str(wake_model_path)],
        inference_framework="onnx",
        melspec_model_path=str(WAKEWORD_ROOT / "melspectrogram.onnx"),
        embedding_model_path=str(WAKEWORD_ROOT / "embedding_model.onnx"),
    )
    return model, wake_phrase


def wait_for_wake(model, wake_phrase: str) -> None:
    frame_length = 1280
    last_detection = 0.0
    confirmed_frames = 0
    confirmed_label = ""
    print(f"FRIDAY wake listener armed. Say: {wake_phrase}")

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=frame_length) as stream:
        while True:
            frame, _ = stream.read(frame_length)
            now = time.time()
            pcm = np.asarray(frame, dtype=np.int16).reshape(-1)
            predictions = model.predict(pcm)
            score = max(predictions.values()) if predictions else 0.0
            label = max(predictions, key=predictions.get) if predictions else ""
            if WAKE_DEBUG and score >= WAKE_DEBUG_SCORE_THRESHOLD:
                print(f"Wake candidate: {label} score={score:.3f} confirmed={confirmed_frames}")
            if score >= WAKE_THRESHOLD and label == confirmed_label:
                confirmed_frames += 1
            elif score >= WAKE_THRESHOLD:
                confirmed_label = label
                confirmed_frames = 1
            else:
                confirmed_label = ""
                confirmed_frames = 0

            if confirmed_frames >= WAKE_CONFIRM_FRAMES and (now - last_detection) >= WAKE_COOLDOWN_SECONDS:
                last_detection = now
                confirmed_frames = 0
                confirmed_label = ""
                print(f"Wake word detected: {label} score={score:.3f}")
                return


def warm_ollama_model() -> None:
    try:
        started_at = time.perf_counter()
        response = requests.post(
            f"{OLLAMA}/api/generate",
            json={
                "model": CHAT_MODEL,
                "prompt": "",
                "stream": False,
                "keep_alive": CHAT_KEEP_ALIVE,
                "options": {"num_predict": 1},
            },
            timeout=300,
        )
        response.raise_for_status()
        print(f"Model warm-up: {time.perf_counter() - started_at:.2f}s")
    except Exception as exc:
        print(f"Model warm-up skipped: {exc}")


def run_wake_loop() -> None:
    model, wake_phrase = build_wake_model()
    token = signin()
    if STT_ENGINE == "local":
        local_stt_model()
    warm_ollama_model()
    if STARTUP_GREETING:
        print(f"Startup greeting: {STARTUP_GREETING}")
        speak(STARTUP_GREETING)

    while True:
        wait_for_wake(model, wake_phrase)
        run_interactive_session(token)
        time.sleep(WAKE_POST_RESPONSE_MUTE_SECONDS)


if __name__ == "__main__":
    run_wake_loop()
