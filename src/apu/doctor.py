"""`apu doctor` checks every piece of the setup; `apu setup` puts the missing pieces in place (Windows)."""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import config, machine
from .ollama import EngineDown, Ollama

OK, BAD, WARN = "\x1b[32m✓\x1b[0m", "\x1b[31m✗\x1b[0m", "\x1b[33m!\x1b[0m"
WINDOWS = platform.system() == "Windows"
OLLAMA_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama"
OLLAMA_LOGS = Path(os.environ.get("LOCALAPPDATA", "")) / "Ollama"

# The largest model that still leaves room for a browser and an editor, by installed RAM.
# MoE models first: they hold many parameters but read few per token, which is what a
# shared-memory iGPU (lots of memory, modest bandwidth) is best at.
RECOMMENDED = [
    (48, "qwen3.6:35b-a3b"),
    (28, "gemma4:26b-a4b"),
    (14, "gemma4:e4b"),
    (0, "gemma4:e2b"),
]


def recommended_model(total_ram_gb: float) -> str:
    return next(m for floor, m in RECOMMENDED if total_ram_gb >= floor)


def _ollama_exe() -> str | None:
    found = shutil.which("ollama")
    if found:
        return found
    exe = OLLAMA_DIR / "ollama.exe"
    return str(exe) if exe.exists() else None


def _user_env(name: str) -> str | None:
    if not WINDOWS:
        return os.environ.get(name)
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def _set_user_env(name: str, value: str) -> None:
    import ctypes
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
    # Tell running programs (Explorer, so apps started from now on) that the environment changed.
    ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 2, 5000, None)
    os.environ[name] = value


def _last_gpu_detection() -> str | None:
    """The engine's own verdict, from its log: which device it decided to compute on."""
    logs = sorted(OLLAMA_LOGS.glob("server*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for log in logs:
        lines = [l for l in log.read_text(encoding="utf-8", errors="replace").splitlines()
                 if 'msg="inference compute"' in l]
        if lines:
            return lines[-1]
    return None


def doctor(cfg) -> int:
    problems = 0

    def report(ok, text, fix=None):
        nonlocal problems
        mark = OK if ok is True else WARN if ok is None else BAD
        print(f" {mark} {text}")
        if fix and ok is not True:
            print(f"     fix: {fix}")
        if ok is False:
            problems += 1

    info = machine.info()
    print(f"machine   {info.get('vendor', '')} {info.get('model', '')} · {info.get('cpu', '')}")
    print(f"          {info.get('ram_gb', '?')} GB RAM at {info.get('ram_mts', '?')} MT/s · "
          + "; ".join(info.get("gpus", [])) + "\n")

    exe = _ollama_exe()
    report(bool(exe), f"Ollama installed{f' ({exe})' if exe else ''}", "apu setup  (or: winget install Ollama.Ollama)")

    if WINDOWS:
        igpu = _user_env("OLLAMA_IGPU_ENABLE")
        report(igpu == "1", f"OLLAMA_IGPU_ENABLE={igpu or '(unset)'}: Ollama skips integrated GPUs unless this is 1",
               "apu setup, then quit Ollama from the tray and open it again")

    eng = Ollama(cfg["host"])
    try:
        report(True, f"engine answering at {cfg['host']} (Ollama {eng.version()})")
    except EngineDown:
        report(False, f"no engine answering at {cfg['host']}", "open the Ollama app (Start menu), wait ~30 s")
        print(f"\n{problems} problem(s).")
        return 1

    det = _last_gpu_detection()
    if det:
        lib = re.search(r"library=(\S+)", det)
        name = re.search(r'description="([^"]+)"', det)
        total = re.search(r'total="([^"]+)"', det)
        on_gpu = lib and lib.group(1).lower() != "cpu"
        report(bool(on_gpu), f"engine computes on: {name.group(1) if name else '?'} via {lib.group(1) if lib else '?'}"
               + (f", {total.group(1)} usable" if total else ""),
               "set OLLAMA_IGPU_ENABLE=1 (apu setup) and restart Ollama")
    else:
        report(None, "could not read the engine's GPU detection from its log")

    names = {m["name"]: m for m in eng.models()}
    model = cfg["model"]
    report(model in names, f"default model {model} downloaded" + (f" ({names[model]['size'] / 2**30:.1f} GB)" if model in names else ""),
           f"ollama pull {model}   (or pick another: apu models, apu use <model>)")

    free = machine.free_ram_gb()
    if model in names and free is not None:
        need = names[model]["size"] / 2**30 + 2
        loaded = any(m["name"] == model for m in eng.loaded())
        report(True if loaded or free > need else None,
               f"free RAM {free:.1f} GB" + (" (model already loaded)" if loaded else f", model needs ~{need:.0f} GB"),
               "close something heavy, or use a smaller model")

    for m in eng.loaded():
        size, vram = m.get("size", 0), m.get("size_vram", 0)
        report(vram / size > 0.99 if size else None, f"{m['name']} is {100 * vram / size:.0f}% on the GPU" if size else m["name"],
               "part of the model spilled to the CPU: lower the context (apu ask --ctx) or free memory")

    if shutil.which("claude"):
        r = subprocess.run(["claude", "mcp", "get", "apu"], capture_output=True, text=True, timeout=30)
        report(r.returncode == 0, "Claude Code knows the apu MCP server",
               "claude mcp add --scope user apu -- apu mcp")
    else:
        report(None, "Claude Code not found on PATH (optional)")

    print(f"\n{'all good.' if not problems else f'{problems} problem(s).'}")
    return 1 if problems else 0


def _ask(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    return input(f"{question} [Y/n] ").strip().lower() in ("", "y", "yes", "s", "si", "sí")


def _restart_ollama():
    subprocess.run(["taskkill", "/F", "/IM", "ollama app.exe"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], capture_output=True)
    time.sleep(2)
    app = OLLAMA_DIR / "ollama app.exe"
    env = dict(os.environ, OLLAMA_IGPU_ENABLE="1")
    subprocess.Popen([str(app)], env=env, close_fds=True)


def _wait_engine(eng: Ollama, seconds: int = 90) -> bool:
    # GPU discovery takes 20-30 s on a Radeon 860M before the server answers.
    for _ in range(seconds):
        try:
            eng.version()
            return True
        except EngineDown:
            time.sleep(1)
    return False


def _pull(eng: Ollama, model: str):
    last = ""
    with eng._request("/api/pull", {"model": model, "stream": True}, timeout=3600) as r:
        for line in r:
            c = json.loads(line)
            if "error" in c:
                raise RuntimeError(c["error"])
            status = c.get("status", "")
            if c.get("total"):
                pct = 100 * c.get("completed", 0) / c["total"]
                print(f"\r  {status[:30]:<30} {pct:5.1f}% of {c['total'] / 2**30:.1f} GB", end="", flush=True)
            elif status != last:
                print(f"\n  {status}", end="", flush=True)
            last = status
    print()


def setup(cfg, assume_yes: bool = False) -> int:
    if not WINDOWS:
        print("apu setup automates Windows. On Linux/macOS: install Ollama (https://ollama.com/download), "
              "then: ollama pull " + recommended_model((machine.info().get("ram_gb") or 16)))
        return 1

    print("apu setup: each step says what it does and asks first.\n")

    if not _ollama_exe():
        print("1. Ollama is the engine that runs the model. It is not installed.")
        if not _ask("   Install it with winget?", assume_yes):
            return 1
        subprocess.run(["winget", "install", "--id", "Ollama.Ollama", "-e", "--silent",
                        "--accept-source-agreements", "--accept-package-agreements"], check=True)
    else:
        print(f"1. Ollama is installed ({_ollama_exe()}).")

    restart = False
    if _user_env("OLLAMA_IGPU_ENABLE") != "1":
        print("2. Ollama ignores integrated GPUs unless OLLAMA_IGPU_ENABLE=1; without it everything runs on the CPU.")
        if _ask("   Set it for your user?", assume_yes):
            _set_user_env("OLLAMA_IGPU_ENABLE", "1")
            restart = True
    else:
        print("2. OLLAMA_IGPU_ENABLE=1 is already set.")

    eng = Ollama(cfg["host"])
    if restart:
        print("   Restarting Ollama so it picks the setting up (GPU discovery takes ~30 s)...")
        _restart_ollama()
    else:
        try:
            eng.version()
        except EngineDown:
            print("   Starting Ollama...")
            _restart_ollama()
    if not _wait_engine(eng):
        print("   Ollama did not answer within 90 s. Open it from the Start menu and run apu setup again.")
        return 1

    ram = machine.info().get("ram_gb") or 16
    model = cfg["model"] if config.CONFIG_PATH.exists() else recommended_model(ram)
    have = {m["name"] for m in eng.models()}
    if model in have:
        print(f"3. {model} is downloaded.")
    else:
        print(f"3. With {ram:.0f} GB of RAM the recommended model is {model}.")
        if not _ask("   Download it now? (it is large: 3 to 25 GB)", assume_yes):
            return 1
        _pull(eng, model)
    config.save({"model": model})

    if shutil.which("claude"):
        r = subprocess.run(["claude", "mcp", "get", "apu"], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            print("4. Claude Code is installed. Registering apu as an MCP server lets it hand tasks to the local model.")
            if _ask("   Register it (user scope, all projects)?", assume_yes):
                # The absolute path, not "apu": a Claude Code started before the PATH change
                # would not find the bare name.
                exe = shutil.which("apu") or sys.argv[0]
                subprocess.run(["claude", "mcp", "add", "--scope", "user", "apu", "--", exe, "mcp"], check=True)
        else:
            print("4. Claude Code already has the apu MCP server.")

    print("\nDone. Try:  apu ping")
    return 0
