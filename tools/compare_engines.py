"""Same weights, same prompts, two engines: Ollama vs LM Studio.

Both engines must have the model loaded (or loadable) and both servers running:
  Ollama on :11434, LM Studio on :1234 (lms server start).
Each engine reports its own timings, so client-side network and JSON overhead is excluded.

  python tools/compare_engines.py --ollama qwen3.6:35b-a3b --lmstudio qwen3.6-35b-a3b
"""

import argparse
import json
import statistics
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from apu import machine  # noqa: E402
from apu.cli import FILLER  # noqa: E402

GEN = "Run {i}. Write a detailed, 300-word explanation of how a heat pump moves heat from a cold room to a warm one."
READ = "Run {i}.\n\n" + FILLER * 45 + "\n\nIn one sentence: what does the controller adjust?"


def post(url, body, timeout=900):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def ollama(model, prompt, max_tokens, ctx):
    r = post("http://127.0.0.1:11434/api/chat", {
        "model": model, "messages": [{"role": "user", "content": prompt}], "stream": False, "think": False,
        "options": {"num_ctx": ctx, "num_predict": max_tokens, "temperature": 0}})
    return {"gen_tps": r["eval_count"] / (r["eval_duration"] / 1e9),
            "prompt_tps": r["prompt_eval_count"] / (r["prompt_eval_duration"] / 1e9),
            "gen_tokens": r["eval_count"], "prompt_tokens": r["prompt_eval_count"]}


def lmstudio(model, prompt, max_tokens, ctx):
    # LM Studio's own REST API (/api/v0) returns engine-side stats; the OpenAI-compatible /v1 does not.
    r = post("http://127.0.0.1:1234/api/v0/chat/completions", {
        "model": model, "messages": [{"role": "user", "content": prompt}], "stream": False,
        "max_tokens": max_tokens, "temperature": 0,
        "chat_template_kwargs": {"enable_thinking": False}})
    s, u = r["stats"], r["usage"]
    # time_to_first_token is the prompt-processing time
    return {"gen_tps": s["tokens_per_second"],
            "prompt_tps": u["prompt_tokens"] / s["time_to_first_token"] if s.get("time_to_first_token") else 0,
            "gen_tokens": u["completion_tokens"], "prompt_tokens": u["prompt_tokens"],
            "reasoning_tokens": u.get("completion_tokens_details", {}).get("reasoning_tokens")}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ollama")
    p.add_argument("--lmstudio")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--ctx", type=int, default=16384)
    p.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "bench" / "results"))
    a = p.parse_args()

    engines = [(n, f, m) for n, f, m in (("ollama", ollama, a.ollama), ("lmstudio", lmstudio, a.lmstudio)) if m]
    results = {}
    for name, fn, model in engines:
        fn(model, "Say ok.", 4, a.ctx)  # warm-up: loads the model, not measured
        runs = []
        for i in range(1, a.runs + 1):
            g = fn(model, GEN.format(i=i), 256, a.ctx)
            r = fn(model, READ.format(i=i), 24, a.ctx)
            runs.append({"gen": g, "read": r})
            print(f"{name:9} run {i}: writing {g['gen_tps']:5.1f} tok/s ({g['gen_tokens']} tok) · "
                  f"reading {r['prompt_tps']:6.0f} tok/s ({r['prompt_tokens']} tok)", flush=True)
        results[name] = {
            "model": model, "runs": runs,
            "median_gen_tps": round(statistics.median(x["gen"]["gen_tps"] for x in runs), 2),
            "median_prompt_tps": round(statistics.median(x["read"]["prompt_tps"] for x in runs), 1),
        }

    print()
    for name, r in results.items():
        print(f"{name:9} median: writing {r['median_gen_tps']} tok/s · reading {r['median_prompt_tps']} tok/s")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{datetime.now():%Y%m%d-%H%M%S}_engines.json"
    f.write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ctx": a.ctx,
                             "machine": machine.info(), "results": results}, indent=2) + "\n", encoding="utf-8")
    print(f"saved {f}")


if __name__ == "__main__":
    main()
