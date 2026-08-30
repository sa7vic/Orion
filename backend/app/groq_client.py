"""
Thin wrapper around the Groq SDK that makes the free tier survivable:

- In-process token-bucket rate limiter (default: 20 req/min, under Groq's
  ~30 req/min free-tier cap, leaving headroom for judge Q&A / concurrent demo
  traffic).
- Exponential backoff + retry on 429 / transient errors (tenacity).
- Response caching (identical prompt -> identical model -> cached result) so
  repeated demo runs and identical simulation requests don't burn quota.
- JSON-mode helper that asks the model for structured output and safely
  parses it, since several specialists depend on structured reasons/scores
  rather than free text.

If GROQ_API_KEY is not set, calls fall back to a deterministic offline mock
so the rest of the app (router, specialists, UI) still runs end-to-end
without any API key -- useful for local dev / grading without secrets.
"""
import hashlib
import json
import logging
import time
import threading
from collections import deque

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger("orion.groq_client")

try:
    from groq import Groq
    _GROQ_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover
    _GROQ_SDK_AVAILABLE = False


class _RateLimiter:
    """Simple sliding-window token bucket, thread-safe."""

    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self._calls = deque()
        self._lock = threading.Lock()

    def acquire(self):
        with self._lock:
            now = time.time()
            while self._calls and now - self._calls[0] > 60:
                self._calls.popleft()
            if len(self._calls) >= self.max_per_minute:
                sleep_for = 60 - (now - self._calls[0]) + 0.05
                time.sleep(max(sleep_for, 0))
            self._calls.append(time.time())


class GroqRateLimitError(Exception):
    pass


class OrionGroqClient:
    def __init__(self):
        self._limiter = _RateLimiter(settings.groq_max_requests_per_minute)
        self._cache: dict[str, tuple[float, str]] = {}
        self._cache_lock = threading.Lock()
        self._client = None
        if _GROQ_SDK_AVAILABLE and settings.groq_api_key:
            self._client = Groq(api_key=settings.groq_api_key)

    @property
    def online(self) -> bool:
        return self._client is not None

    def _cache_key(self, model: str, prompt: str, system: str) -> str:
        raw = f"{model}::{system}::{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _cache_get(self, key: str) -> str | None:
        with self._cache_lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            ts, value = entry
            if time.time() - ts > settings.groq_cache_ttl_seconds:
                del self._cache[key]
                return None
            return value

    def _cache_set(self, key: str, value: str):
        with self._cache_lock:
            self._cache[key] = (time.time(), value)

    def clear_cache(self):
        with self._cache_lock:
            self._cache.clear()

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type(GroqRateLimitError),
        reraise=True,
    )
    def _call(self, model: str, system: str, prompt: str, json_mode: bool) -> str:
        self._limiter.acquire()
        try:
            kwargs = dict(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=800,
            )
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = self._client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content
        except Exception as e:  # noqa: BLE001
            msg = str(e).lower()
            if "429" in msg or "rate" in msg:
                raise GroqRateLimitError(str(e)) from e
            raise

    def complete(
        self,
        prompt: str,
        system: str = "You are a precise fraud-analysis assistant.",
        model: str | None = None,
        json_mode: bool = False,
        offline_fallback: str = "{}",
        use_cache: bool = True,
    ) -> str:
        model = model or settings.groq_model_fast
        key = self._cache_key(model, prompt, system)
        if use_cache:
            cached = self._cache_get(key)
            if cached is not None:
                return cached

        if not self.online:
            # Deterministic offline mode: keeps every endpoint functional
            # without an API key (dev/grading convenience).
            if use_cache:
                self._cache_set(key, offline_fallback)
            return offline_fallback

        try:
            result = self._call(model, system, prompt, json_mode)
        except Exception as e:  # noqa: BLE001 -- ANY Groq failure (rate limit
            # exhausted after retries, malformed JSON the API itself rejects
            # with json_validate_failed, transient 5xx, network blip, etc.)
            # must degrade to the offline fallback, not crash the caller's
            # endpoint. A 500 from an LLM hiccup on a single specialist call
            # is strictly worse than a slightly-generic fallback answer --
            # online mode should never be LESS robust than offline mode.
            logger.warning(
                f"Groq call failed after retries ({type(e).__name__}: {e}) -- "
                f"falling back to offline_fallback for model={model}"
            )
            if use_cache:
                self._cache_set(key, offline_fallback)
            return offline_fallback

        if use_cache:
            self._cache_set(key, result)
        return result

    def complete_json(
        self,
        prompt: str,
        system: str,
        model: str | None = None,
        offline_fallback: dict | None = None,
        use_cache: bool = True,
    ) -> dict:
        fallback = offline_fallback or {}
        raw = self.complete(
            prompt,
            system=system + " Respond ONLY with valid JSON, no markdown fences, no commentary.",
            model=model,
            json_mode=True,
            offline_fallback=json.dumps(fallback),
            use_cache=use_cache,
        )
        try:
            cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(cleaned)
        except (json.JSONDecodeError, AttributeError):
            return fallback


groq_client = OrionGroqClient()
