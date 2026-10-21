"""apu: one command for a local LLM on an APU laptop.

  apu ask "question"            ask the local model (files with -f, or pipe text in)
  apu ping                      is it alive, and how fast is it right now
  apu stats                     what is loaded, where it lives (GPU/CPU), recent speed
  apu bench                     a repeatable benchmark, saved with the machine's specs
  apu models / apu use <model>  list downloaded models / change the default
  apu doctor                    check every piece of the setup, with the fix for each failure
  apu setup                     install and configure everything (Windows)
  apu mcp                       run as an MCP server, so Claude Code can hand it tasks
"""

import argparse
import json
import os
import platform
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, config, machine
from .ollama import EngineDown, Ollama

DATA_DIR = Path.home() / ".apu"
LOG_PATH = DATA_DIR / "log.jsonl"
BENCH_DIR = DATA_DIR / "bench"


def _engine(cfg) -> Ollama:
    return Ollama(cfg["host"])


def _err(*a):
    print(*a, file=sys.stderr)


def _log(record: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _gb(n: int) -> str:
    return f"{n / 2**30:.1f} GB"


# ---------------------------------------------------------------- ask

def build_messages(prompt: str, files: list[str], stdin_text: str | None, system: str | None) -> list[dict]:
    parts = []
    for path in files:
        p = Path(path)
        parts.append(f"File: {p.name}\n```\n{p.read_text(encoding='utf-8', errors='replace')}\n```")
    if stdin_text:
        parts.append(f"Input:\n```\n{stdin_text}\n```")
    if prompt:
        parts.append(prompt)
    messages = [{"role": "system", "content": system}] if system else []
    messages.append({"role": "user", "content": "\n\n".join(parts)})
    return messages


def run_chat(cfg, messages, *, model=None, think=None, ctx=None, max_tokens=None,
             temperature=None, on_text=None, on_thinking=None, source="cli"):
    """Sends one chat, streams it through the callbacks, logs the timings. Returns (text, stats)."""
    model = model or cfg["model"]
    ctx = ctx or cfg["ctx"]
    think = cfg["think"] if think is None else think
    text, stats = [], None
    for kind, value in _engine(cfg).chat(model, messages, ctx=ctx, think=think,
                                         max_tokens=max_tokens, temperature=temperature):
        if kind == "content":
            text.append(value)
            if on_text:
                on_text(value)
        elif kind == "thinking" and on_thinking:
            on_thinking(value)
        elif kind == "done":
            stats = value
    if stats:
        _log({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source": source,
              "model": model, "ctx": ctx, "think": think, **stats.as_dict()})
    return "".join(text), stats


def cmd_ask(args, cfg):
    stdin_text = None if sys.stdin.isatty() else sys.stdin.read()
    prompt = " ".join(args.prompt)
    if not (prompt or stdin_text or args.file):
        _err('Nothing to ask. Try: apu ask "explain this error" -f log.txt')
        return 2
    messages = build_messages(prompt, args.file, stdin_text, args.system)

    approx_tokens = sum(len(m["content"]) for m in messages) // 4
    ctx = args.ctx or cfg["ctx"]
    if approx_tokens > ctx * 0.9:
        _err(f"warning: the input is ~{approx_tokens} tokens and the context is {ctx}; "
             f"the start will be cut. Raise it with --ctx {min(131072, 2 ** (approx_tokens * 2).bit_length())}")

    def write(t):
        sys.stdout.write(t)
        sys.stdout.flush()

    def think_out(t):
        sys.stderr.write(f"\x1b[2m{t}\x1b[0m")
        sys.stderr.flush()

    text, stats = run_chat(cfg, messages, model=args.model, think=args.think or None, ctx=args.ctx,
                           max_tokens=args.max_tokens, on_text=None if args.json else write,
                           on_thinking=think_out if args.think and not args.json else None)
    if args.json:
        print(json.dumps({"text": text, "model": args.model or cfg["model"],
                          "stats": stats.as_dict() if stats else None}, ensure_ascii=False))
    else:
        if not text.endswith("\n"):
            print()
        if stats and not args.quiet:
            _err(f"\x1b[2m[{args.model or cfg['model']} · {stats.line()}]\x1b[0m")
    return 0


# ---------------------------------------------------------------- ping / stats / models

def cmd_ping(args, cfg):
    eng = _engine(cfg)
    t0 = time.perf_counter()
    version = eng.version()
    rtt = (time.perf_counter() - t0) * 1000
    print(f"engine   Ollama {version} at {cfg['host']} ({rtt:.0f} ms)")
    names = {m["name"] for m in eng.models()}
    if cfg["model"] not in names:
        print(f"model    {cfg['model']} is not downloaded. Run: apu setup  (or ollama pull {cfg['model']})")
        return 1
    _, stats = run_chat(cfg, [{"role": "user", "content": "Reply with the single word: pong"}],
                        max_tokens=8, think=False, temperature=0, source="ping")
    loaded = next((m for m in eng.loaded() if m["name"] == cfg["model"]), None)
    where = _placement(loaded) if loaded else "?"
    print(f"model    {cfg['model']} · {where}")
    print(f"speed    {stats.line()}")
    if stats.load_s > 0.5:
        print("         (the first call loads the model from disk; the next ones skip that)")
    return 0


def _placement(m: dict) -> str:
    size, vram = m.get("size", 0), m.get("size_vram", 0)
    if not size:
        return "?"
    pct = 100 * vram / size
    where = "GPU" if pct > 99 else "CPU" if pct < 1 else f"{pct:.0f}% GPU / {100 - pct:.0f}% CPU"
    return f"{_gb(size)} in memory, {where}, context {m.get('context_length', '?')}"


def cmd_stats(args, cfg):
    eng = _engine(cfg)
    print(f"engine     Ollama {eng.version()} at {cfg['host']}")
    print(f"default    {cfg['model']} · ctx {cfg['ctx']} · think {'on' if cfg['think'] else 'off'}")
    free = machine.free_ram_gb()
    if free is not None:
        print(f"free RAM   {free:.1f} GB")
    loaded = eng.loaded()
    if not loaded:
        print("loaded     nothing (models unload after 5 idle minutes; the next call reloads)")
    for m in loaded:
        until = m.get("expires_at", "")[:19].replace("T", " ")
        print(f"loaded     {m['name']} · {_placement(m)} · unloads at {until}")

    if LOG_PATH.exists():
        rows = [json.loads(l) for l in LOG_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
        rows = [r for r in rows if r.get("source") != "bench"][-args.last:]
        if rows:
            gen = [r["gen_tps"] for r in rows if r["gen_tokens"] >= 16]
            pp = [r["prompt_tps"] for r in rows if r["prompt_tokens"] >= 256]
            print(f"\nlast {len(rows)} requests ({LOG_PATH})")
            if gen:
                print(f"  generation   median {statistics.median(gen):.1f} tok/s  (min {min(gen):.1f}, max {max(gen):.1f})")
            if pp:
                print(f"  prompt read  median {statistics.median(pp):.0f} tok/s")
            print(f"  tokens       {sum(r['gen_tokens'] for r in rows)} written, {sum(r['prompt_tokens'] for r in rows)} read")
            by_source = {}
            for r in rows:
                by_source[r["source"]] = by_source.get(r["source"], 0) + 1
            print("  from         " + ", ".join(f"{k} {v}" for k, v in sorted(by_source.items())))

    benches = sorted(BENCH_DIR.glob("*.json")) if BENCH_DIR.exists() else []
    if benches:
        b = json.loads(benches[-1].read_text(encoding="utf-8"))
        print(f"\nlast bench  {b['at'][:16]} · {b['model']} · "
              f"{b['summary']['gen_tps']} tok/s writing, {b['summary']['prompt_tps']} tok/s reading")
    return 0


def cmd_models(args, cfg):
    models = _engine(cfg).models()
    if not models:
        print("No models downloaded. Run: apu setup")
        return 1
    for m in sorted(models, key=lambda m: m["name"]):
        d = m.get("details", {})
        mark = "*" if m["name"] == cfg["model"] else " "
        print(f"{mark} {m['name']:<32} {_gb(m['size']):>8}  {d.get('parameter_size', ''):>7}  {d.get('quantization_level', '')}")
    print("\n* default. Change it with: apu use <model>")
    return 0


def cmd_use(args, cfg):
    names = {m["name"] for m in _engine(cfg).models()}
    if args.model not in names:
        _err(f"{args.model} is not downloaded. Get it with: ollama pull {args.model}")
        return 1
    config.save({"model": args.model})
    print(f"default model is now {args.model} (saved in {config.CONFIG_PATH})")
    return 0


# ---------------------------------------------------------------- bench

FILLER = ("The cooling loop of a small laboratory reactor is described here in plain words. Water leaves the pump, "
          "passes a flow meter, enters the jacket around the vessel, and returns through a plate exchanger. "
          "Every sensor reports once per second, and the controller adjusts the pump speed to hold the outlet "
          "temperature near its set point. ")


def cmd_bench(args, cfg):
    model = args.model or cfg["model"]
    eng = _engine(cfg)
    print(f"bench  {model} · {args.runs} runs · ctx {cfg['ctx']}")
    print("       unloading first, so run 1 measures a cold load from disk")
    try:
        eng._json("/api/generate", {"model": model, "keep_alive": 0})
    except Exception:
        pass
    time.sleep(2)

    runs = []
    long_text = FILLER * 45  # about 3,500 tokens
    for i in range(1, args.runs + 1):
        # A random prefix per run: the engine keeps a prompt cache, and a prompt it has seen before
        # (even in an earlier invocation) would read in milliseconds and fake the reading speed.
        nonce = uuid.uuid4().hex[:12]
        _, gen = run_chat(cfg, [{"role": "user", "content": f"Run {i}, nonce {nonce}. Write a detailed, 300-word "
                                 "explanation of how a heat pump moves heat from a cold room to a warm one."}],
                          model=model, think=False, max_tokens=256, temperature=0, source="bench")
        _, pp = run_chat(cfg, [{"role": "user", "content": f"Run {i}, nonce {nonce}.\n\n{long_text}\n\nIn one "
                                "sentence: what does the controller adjust?"}],
                         model=model, think=False, max_tokens=24, temperature=0, source="bench")
        runs.append({"gen": gen.as_dict(), "prompt": pp.as_dict()})
        print(f"  run {i}: writing {gen.gen_tps:5.1f} tok/s · reading {pp.prompt_tps:6.0f} tok/s"
              + (f" · cold load {gen.load_s:.1f}s" if gen.load_s > 0.5 else ""))

    loaded = next((m for m in eng.loaded() if m["name"] == model), {})
    details = eng.show(model).get("details", {})
    summary = {
        "gen_tps": round(statistics.median(r["gen"]["gen_tps"] for r in runs), 1),
        "prompt_tps": round(statistics.median(r["prompt"]["prompt_tps"] for r in runs)),
        "cold_load_s": runs[0]["gen"]["load_s"],
    }
    result = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "apu_version": __version__,
        "engine": {"name": "ollama", "version": eng.version(),
                   "igpu_enable": os.environ.get("OLLAMA_IGPU_ENABLE")},
        "model": model,
        "model_details": details,
        "ctx": cfg["ctx"],
        "memory": {"size": loaded.get("size"), "size_vram": loaded.get("size_vram")},
        "machine": machine.info(),
        "free_ram_gb_after": round(machine.free_ram_gb() or 0, 1),
        "summary": summary,
        "runs": runs,
    }
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = BENCH_DIR / f"{stamp}_{model.replace(':', '_').replace('/', '_')}.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nmedian writing {summary['gen_tps']} tok/s · reading {summary['prompt_tps']} tok/s · "
          f"cold load {summary['cold_load_s']:.1f}s · {_placement(loaded) if loaded else ''}")
    print(f"saved  {out}")
    return 0


# ---------------------------------------------------------------- entry point

def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    if platform.system() == "Windows":
        os.system("")  # turns on ANSI colours in the classic Windows console

    p = argparse.ArgumentParser(prog="apu", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"apu {__version__}")
    sub = p.add_subparsers(dest="cmd")

    a = sub.add_parser("ask", help="ask the local model")
    a.add_argument("prompt", nargs="*")
    a.add_argument("-f", "--file", action="append", default=[], help="add a text file as context (repeatable)")
    a.add_argument("-m", "--model")
    a.add_argument("-s", "--system", help="system prompt")
    a.add_argument("--think", action="store_true", help="let the model reason first (slower, better on hard questions)")
    a.add_argument("--ctx", type=int, help="context window in tokens for this call")
    a.add_argument("--max-tokens", type=int)
    a.add_argument("--json", action="store_true", help="print one JSON object with the text and the timings")
    a.add_argument("-q", "--quiet", action="store_true", help="no timings line")

    sub.add_parser("ping", help="is it alive, and how fast")
    s = sub.add_parser("stats", help="what is loaded and how fast it has been")
    s.add_argument("--last", type=int, default=50, help="how many recent requests to summarise")
    b = sub.add_parser("bench", help="repeatable benchmark, saved to ~/.apu/bench")
    b.add_argument("-m", "--model")
    b.add_argument("--runs", type=int, default=3)
    sub.add_parser("models", help="downloaded models")
    u = sub.add_parser("use", help="set the default model")
    u.add_argument("model")
    sub.add_parser("doctor", help="check the setup")
    st = sub.add_parser("setup", help="install and configure (Windows)")
    st.add_argument("-y", "--yes", action="store_true", help="do not ask before each step")
    sub.add_parser("mcp", help="serve as an MCP server over stdio (for Claude Code)")

    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help()
        return 0

    cfg = config.load()
    try:
        if args.cmd == "doctor":
            from .doctor import doctor
            return doctor(cfg)
        if args.cmd == "setup":
            from .doctor import setup
            return setup(cfg, assume_yes=args.yes)
        if args.cmd == "mcp":
            from .mcp import serve
            return serve(cfg)
        return {"ask": cmd_ask, "ping": cmd_ping, "stats": cmd_stats, "bench": cmd_bench,
                "models": cmd_models, "use": cmd_use}[args.cmd](args, cfg)
    except EngineDown as e:
        _err(f"{e}\nIs Ollama running? Start the Ollama app, or run: apu doctor")
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
