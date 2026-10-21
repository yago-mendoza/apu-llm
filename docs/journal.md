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

**Downloads.** `qwen3.6:35b-a3b` (21 GB, Q4_K_M) and `qwen3.8:27b` (18 GB) pulled in parallel over home Wi-Fi at 7 to 9 MB/s combined, about an hour in total. Pitfall: the first pull stalled at 2 % with no error, while the blob on disk already measured 20.2 GB. Ollama preallocates the whole file, so its size says nothing about progress; the real progress is in the `-partial-N` JSON files next to it (`Completed` / `Size`), or in the `ollama pull` progress line. Restarting the pull resumed where it stopped.

- Decision: download Qwen3.8 27B as well. On the Artificial Analysis Intelligence Index v4.3.2 it scores 33.7 against 18.2 for Qwen3.6 35B-A3B, but it is dense, so every token reads all 27B weights instead of ~3B: expected to be several times slower. The point is to measure both and keep the fast one for everyday work and the strong one for hard tasks.

**LM Studio** installed with `winget install ElementLabs.LMStudio`, as the second engine for the comparison.

- Decision: feed LM Studio the GGUF files Ollama already downloaded instead of downloading them again. Both engines are built on ggml and read the same GGUF format (Ollama runs newer architectures on its own ggml-based engine rather than llama.cpp, so whether LM Studio accepts Ollama's file unchanged is checked below, not assumed); Ollama stores each model as content-addressed blobs under `~/.ollama/models/blobs`, and the largest blob of a model is the GGUF itself. Reusing it saves ~40 GB of downloads and, more importantly for the comparison, guarantees both engines run byte-identical weights.

First run of LM Studio 0.4.26: it offers a first model (Gemma 4 E4B, 6.33 GB, `screens/03-lmstudio-first-run.png`), skipped; then *Advanced settings* (`screens/04-lmstudio-home.png`) with *Start local LLM service on login* **on by default**.

- Decision: turn Developer Mode on (it hides the engine, GPU offload and server settings otherwise) and the start-on-login service off. Ollama is the engine this guide keeps running; two servers resident from boot would each hold memory for nothing.

**Finding 2: LM Studio needs no GPU switch, and sees less memory than Ollama.** `lms runtime ls` shows it ships CPU, CUDA and Vulkan builds of llama.cpp and selected `llama.cpp-win-x86_64-vulkan-avx2@2.61.0` by itself. `lms runtime survey`:

```
AMD Radeon(TM) 860M Graphics (Vulkan, Integrated)   31.76 GiB
RAM: 63.14 GiB
```

31.76 GiB is half the RAM plus the 512 MB dedicated carve-out: the *shared GPU memory* ceiling Windows' display driver model sets for an integrated GPU. Ollama reported 47.6 GiB for the same GPU. Which number is the real ceiling is tested below by loading models larger than 32 GB.

Settings confirmed in `~/.lmstudio/settings.json`: `developerMode: true`, `enableLocalService: false`. Two defaults worth knowing: a model loaded on demand through the API stays in memory for an hour (`jitModelTTL: 3600 s`, against Ollama's 5 minutes), and a *loading guardrail* (`modelLoadingGuardrails.mode: high`) refuses models it estimates will not fit.

- Pitfall: `lms import <file>` **moves** the file by default, which would pull the GGUF out from under Ollama. `lms import --hard-link` (`-L`) gives LM Studio a second directory entry for the same bytes: no extra disk, no admin rights (unlike `--symbolic-link` on Windows), and deleting the model in one engine leaves the other intact. Hard links need both stores on the same NTFS volume; here both live on `C:`.

**First answers.** `qwen3.6:35b-a3b` is Q4_K_M, 35.5B parameters, family `qwen35moe`, and Ollama reports `runner: llamacpp` for it: on this model both engines run llama.cpp, so the comparison is engine packaging and defaults, not two different inference codes. Cold load from the NVMe: 55 s in Ollama, 124 s in LM Studio. Loaded size 20.6 GB, 100 % on the GPU, context 16384.

The GGUF went to LM Studio as a hard link (`New-Item -ItemType HardLink`, the blob starts with the `GGUF` magic bytes; `fsutil hardlink list` shows both paths). LM Studio lists it as `qwen3.6-35b-a3b, 35B, qwen35moe, 21.72 GB` with no conversion.

**Finding 3 (withdrawn, kept for the record; see Finding 4): on the shared-memory path, the iGPU is slower than the CPU.** Same weights, same prompts (`tools/compare_engines.py`; 256 generated tokens; a 2,906-token prompt for reading), temperature 0, thinking off, engines measured one at a time:

| Engine, device | Writing (tok/s) | Reading (tok/s) |
|---|---|---|
| LM Studio 0.4.26, Vulkan iGPU | 7.1 (runs 6.1, 7.1, 7.1) | 62 |
| Ollama 0.40.7, Vulkan iGPU | 7.6 (one `apu ask`, 129 tokens) | 28 (35-token prompt, not comparable) |
| Ollama 0.40.7, CPU only (`num_gpu: 0`) | 11.3, 10.8 | 55, 52 |

During generation the GPU's compute engine sat near 48 % busy, CPU 23 to 51 % (with Chrome and a download running), and `GPU Adapter Memory\Shared Usage` read 23.4 GB: the weights were in GPU-mapped memory and the GPU was working, just slowly. 7 tok/s with ~3B active parameters at ~4.8 bits is roughly 2 GB read per token, about 14 GB/s, against a theoretical ~128 GB/s for 128-bit LPDDR5X-8000.

- Hypothesis: on Windows, an iGPU's *shared* memory (system pages mapped through the GPU's address translation) is a slower path than memory the firmware carves out as *dedicated*, even though both are the same DRAM chips. Supporting evidence: AMD's own LM Studio tests report Variable Graphics Memory adding 17 to 22 % on top of Vulkan offload ([AMD](https://www.amd.com/en/blogs/2024/accelerating-llama-cpp-performance-in-consumer-llm.html)), and a llama.cpp report of GPU + shared memory running slower than CPU + RAM on Windows ([llama.cpp #10330](https://github.com/ggml-org/llama.cpp/issues/10330)). Ollama's vendored llama.cpp also trails upstream on AMD Vulkan ([ollama #15601](https://github.com/ollama/ollama/issues/15601)), but LM Studio, on a newer llama.cpp, is just as slow here, so that is not the main cause.
- Next test: reserve dedicated memory with AMD Software (Performance, Tuning, Variable Graphics Memory), reboot, rerun the same comparison.

**Finding 4: the comparison above was contaminated three ways; cleaned, the iGPU ties the CPU at writing and wins 1.8× at reading.**

1. *Background load.* The iGPU numbers of Finding 3 were taken while `qwen3.8:27b` was still downloading (network, disk writes, hashing on the CPU). The CPU-only numbers were taken after.
2. *Prompt cache.* Prompts started with `Run 1.`, `Run 2.`, identical across script invocations. Ollama keeps a prompt cache, so a later invocation re-read a 2,908-token prompt at 7,000 to 9,000 tok/s (`prompt_eval_count` still reports all 2,908 tokens). Fixed with a random nonce at the start of every prompt (`tools/compare_engines.py`, `apu bench`).
3. *Stale placement.* A request with default options reused a model still loaded with `num_gpu: 0` from the previous test, so a run labelled GPU was 0 % on the GPU (`/api/ps` `size_vram: 0`). Fixed by unloading (`keep_alive: 0`) before each configuration and recording `/api/ps` after it.

Clean run, nothing else downloading, Chrome and Cursor still open (`bench/results/20261021-135731_engines.json`):

| Ollama 0.40.7, `qwen3.6:35b-a3b` | Writing (tok/s), median (runs) | Reading (tok/s), median (runs) | Placement checked |
|---|---|---|---|
| Vulkan iGPU | 11.7 (9.5, 11.7, 12.8) | 93 (96, 93, 77) | 20.6 GB, 100 % GPU |
| CPU only | 11.2 (11.6, 11.2, 10.5) | 53 (54, 52, 53) | 20.9 GB, 0 % GPU |

Writing is a tie within the run-to-run spread; reading a long prompt is 1.8× faster on the iGPU. 11.7 tok/s at ~2 GB per token is ~23 GB/s of effective weight traffic, a fifth of the theoretical bandwidth, on both devices: whatever limits generation is not specific to the GPU.

LM Studio 0.4.26 under the same clean conditions, same hard-linked weights, `--gpu max`, context 16384 (`bench/results/20261021-140315_engines.json`): writing 9.4 tok/s (7.8, 9.4, 9.7), reading 83 tok/s (84, 78, 83). Ollama is ~25 % faster writing and ~12 % faster reading. LM Studio loads with 4 parallel slots by default (`lms ps`: `PARALLEL 4`), which may account for part of the gap; not isolated.

- Decision: Ollama is the engine the guide keeps. It is faster here on byte-identical weights, open source, runs as a service, and its API reports the GPU/CPU split. LM Studio's advantage is that it needs no GPU switch.

**Qwen3.8 27B, dense** (`qwen3.8:27b`, `bench/results/20261021-143115_engines.json`, 2 runs each):

| Ollama 0.40.7, `qwen3.8:27b` | Writing (tok/s) | Reading (tok/s) | Placement checked |
|---|---|---|---|
| Vulkan iGPU | 2.6 (2.3, 2.8) | 13.8 (14, 14) | 16.3 GB, 100 % GPU |
| CPU only | 2.2 (2.1, 2.3) | 9.1 (9, 9) | 17.0 GB, 0 % GPU |

A 256-token answer takes about 100 s; a 2,900-token prompt takes about 3.5 min to read before the first word. Every token reads all ~16 GB of weights: 2.6 tok/s is ~42 GB/s of weight traffic, twice the MoE model's effective rate, but nine times as much data per token. On this machine it is for short, hard questions where waiting is acceptable, not for documents.
