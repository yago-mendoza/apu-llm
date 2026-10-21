# Article notes (InfraPhysics, bits2bricks)

Working notes for the article that will tell this build. Not the article itself: requirements, the outline, and what each section must prove. The article is written in English (canonical) with a Spanish sibling, in the site's syntax, after the measurements exist.

## Requirements from the author

- Every decision gets a context note (`>>` ctx) saying why, including options seriously considered and rejected.
- Vary the writing: no formula repeated section after section.
- Screenshots of everything, interfaces included (`docs/assets/screens/`).
- Rigorous: every claim measured on the reference machine or sourced beside it.
- Easy above all: the reader should end with one command that works.
- **Make the relationship between Ollama and LM Studio clear** (requested 2026-10-21): what they share, where they differ, and why the guide keeps one running and uses the other as a cross-check.

## Ollama and LM Studio: what the section must establish

- Shared base: both run ggml (llama.cpp's tensor library) and read GGUF files, so the same weights can feed both (hard link, `lms import -L`). Ollama runs newer architectures on its own ggml engine, not llama.cpp proper: verify whether LM Studio loads Ollama's blob unchanged.
- Different shape: Ollama is a background service plus CLI, with a thin desktop app; LM Studio is a desktop app with a server and a CLI (`lms`) added.
- Measured on the 860M:
  - integrated GPU off by default in Ollama (`OLLAMA_IGPU_ENABLE`), on by default in LM Studio (Vulkan runtime selected automatically);
  - usable GPU memory reported: 47.6 GiB (Ollama) vs 31.76 GiB (LM Studio), and which is real;
  - idle unload: 5 min vs 1 h;
  - generation and prompt speed on byte-identical weights (pending).
- Licences: Ollama MIT. LM Studio's desktop app is proprietary (its FAQ: the GUI is not open source; [lmstudio.ai](https://lmstudio.ai)); the `lms` CLI is MIT ([docs](https://lmstudio.ai/docs/cli), [github.com/lmstudio-ai/lms](https://github.com/lmstudio-ai/lms)), and per the same FAQ so are the Core SDK and the MLX engine.
- Why the guide keeps Ollama: open source, scriptable service, API with engine timings and GPU/CPU split, and `ollama launch` integrations. Unless the benchmark says LM Studio is much faster on this GPU, in which case the guide says so.

## Other ctx candidates

- Why the repo name is `apu-llm` (the chip class, not the brand), and the rejected names.
- Why not reserve dedicated GPU memory in the BIOS/AMD software (memory reserved for the GPU vanishes for every other program).
- Why Qwen3.6 35B-A3B as the everyday model and Qwen3.8 27B as the strong one (MoE vs dense, measured).
- Why not Gemma 4 E4B on a 64 GB machine (only for 16 GB machines and bulk trivial tasks).
- Was a 64 GB laptop worth it? What the RAM buys here, priced.
- Will running big models get cheaper (memory prices, MoE, quantization)? Sourced.
- Why `apu` talks to Ollama's native API, not the OpenAI-compatible one (engine timings, GPU/CPU split).
- Why an MCP server and not only a CLI note in CLAUDE.md.
