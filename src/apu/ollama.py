"""Minimal Ollama client over its native HTTP API (stdlib only).

The native API is used instead of the OpenAI-compatible one because it reports the
engine's own timings (prompt and generation, in nanoseconds) and the memory split
between GPU and CPU, which is what `apu stats` and `apu bench` are built on.
"""

import json
import urllib.error
import urllib.request


class EngineDown(Exception):
    pass


class Ollama:
    def __init__(self, host: str):
        self.host = host.rstrip("/")

    def _request(self, path: str, body: dict | None = None, timeout: float = 10):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.host + path, data=data, headers={"Content-Type": "application/json"})
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.URLError as e:
            raise EngineDown(f"No engine answering at {self.host} ({e.reason})") from e

    def _json(self, path: str, body: dict | None = None, timeout: float = 10) -> dict:
        with self._request(path, body, timeout) as r:
            return json.load(r)

    def version(self) -> str:
        return self._json("/api/version")["version"]

    def models(self) -> list[dict]:
        return self._json("/api/tags").get("models", [])

    def loaded(self) -> list[dict]:
        return self._json("/api/ps").get("models", [])

    def show(self, model: str) -> dict:
        return self._json("/api/show", {"model": model})

    def chat(self, model: str, messages: list[dict], *, ctx: int, think: bool,
             max_tokens: int | None = None, temperature: float | None = None,
             keep_alive: str | None = None):
        """Streams the reply. Yields ("thinking"|"content", text) pairs, then ("done", stats)."""
        options = {"num_ctx": ctx}
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if temperature is not None:
            options["temperature"] = temperature
        body = {"model": model, "messages": messages, "stream": True, "think": think, "options": options}
        if keep_alive is not None:
            body["keep_alive"] = keep_alive
        with self._request("/api/chat", body, timeout=900) as r:
            for line in r:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if "error" in chunk:
                    raise RuntimeError(chunk["error"])
                msg = chunk.get("message", {})
                if msg.get("thinking"):
                    yield "thinking", msg["thinking"]
                if msg.get("content"):
                    yield "content", msg["content"]
                if chunk.get("done"):
                    yield "done", Stats.from_chunk(chunk)


class Stats:
    """The engine's own timings for one request."""

    def __init__(self, load_s, prompt_tokens, prompt_s, gen_tokens, gen_s, total_s):
        self.load_s = load_s
        self.prompt_tokens = prompt_tokens
        self.prompt_s = prompt_s
        self.gen_tokens = gen_tokens
        self.gen_s = gen_s
        self.total_s = total_s

    @classmethod
    def from_chunk(cls, c: dict) -> "Stats":
        ns = 1e9
        return cls(
            load_s=c.get("load_duration", 0) / ns,
            prompt_tokens=c.get("prompt_eval_count", 0),
            prompt_s=c.get("prompt_eval_duration", 0) / ns,
            gen_tokens=c.get("eval_count", 0),
            gen_s=c.get("eval_duration", 0) / ns,
            total_s=c.get("total_duration", 0) / ns,
        )

    @property
    def prompt_tps(self) -> float:
        return self.prompt_tokens / self.prompt_s if self.prompt_s else 0.0

    @property
    def gen_tps(self) -> float:
        return self.gen_tokens / self.gen_s if self.gen_s else 0.0

    def line(self) -> str:
        parts = [f"{self.gen_tokens} tok at {self.gen_tps:.1f} tok/s",
                 f"prompt {self.prompt_tokens} tok at {self.prompt_tps:.0f} tok/s"]
        if self.load_s > 0.5:
            parts.append(f"load {self.load_s:.1f}s")
        parts.append(f"total {self.total_s:.1f}s")
        return " · ".join(parts)

    def as_dict(self) -> dict:
        return {
            "load_s": round(self.load_s, 3),
            "prompt_tokens": self.prompt_tokens,
            "prompt_tps": round(self.prompt_tps, 2),
            "gen_tokens": self.gen_tokens,
            "gen_tps": round(self.gen_tps, 2),
            "total_s": round(self.total_s, 3),
        }
