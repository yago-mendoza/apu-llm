# Build journal

What was done, in order, on the reference machine, with the evidence for each step. Raw material for the guide and for the InfraPhysics article; the guide itself is in the README and `docs/`.

Reference machine: Lenovo ThinkPad (type 21YW), AMD Ryzen AI 7 PRO 450 (8 cores, 16 threads), Radeon 860M integrated GPU, 64 GB LPDDR5X (4 × 16 GB, soldered, configured at 8000 MT/s), 1 TB NVMe (YMTC), Windows 11 Pro 26200.

## 2026-10-21

**Baseline, before installing anything.** 63.1 GB visible to Windows. With a normal working session open (Chrome with ~49 processes, Cursor, Claude Code, Anki) 32 GB were in use and 31.2 GB free. The iGPU reports 512 MB of dedicated memory (`AdapterRAM`), the BIOS default; everything else it uses is borrowed from system RAM on demand.

- Decision: do not reserve more dedicated GPU memory (AMD *Variable Graphics Memory*) yet. Memory reserved for the GPU disappears from Windows for every other program; the engine may not need it if it can borrow shared memory. Measure first.

**Ollama 0.40.7** installed with `winget install Ollama.Ollama`. First window: an optional account screen (`screens/01-ollama-app-first-run.png`); local use needs no account. After it, the app lists *integrations* that launch coding agents against a local model (`screens/02-ollama-app-integrations.png`).

**Finding 1: out of the box, Ollama runs on the CPU only.** The server log (`evidence/ollama-0.40.7-default-gpu-detection.log`) shows two separate rejections:

1. ROCm drops the GPU: `no rocblas support for gfx target gfx1152`. The Radeon 860M is `gfx1152`; Ollama's bundled ROCm supports `gfx1150` and `gfx1151` (the 890M and the Ryzen AI Max) but not this one.
2. Vulkan finds it, then drops it on purpose: `dropping integrated GPU; to enable, set OLLAMA_IGPU_ENABLE=1`.

The result: `inference compute id=cpu ... available="30.3 GiB"`, and a default context of 4096 tokens.

**Fix:** `OLLAMA_IGPU_ENABLE=1` as a user environment variable. After a restart (`evidence/ollama-0.40.7-igpu-enabled-detection.log`):
`library=Vulkan ... description="AMD Radeon(TM) 860M Graphics" type=iGPU total="47.6 GiB" available="45.3 GiB"`. GPU discovery takes 20 to 30 s, long enough that the desktop app's 10 s readiness check gives up once (`app.log`: *ollama server not ready, continuing anyway*).

- Note: with 47.6 GiB counted as VRAM, Ollama raises its default context to 262144 tokens. The KV cache for that is several GB. `apu` asks for 16384 per request instead.

**`apu` installed** with `pip install --user -e .`. Pitfall: pip puts `apu.exe` in `%APPDATA%\Python\Python314\Scripts`, which is not on PATH by default; added to the user PATH.
