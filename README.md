<p align="center">
  <a href="https://infraphysics.net"><img src="docs/assets/infraphysics.svg" width="72" alt="InfraPhysics"></a>
</p>

<h1 align="center">apu-llm</h1>

<p align="center">
  Local LLMs on laptops whose GPU shares the system RAM.<br>
  One command to set it up, ask it things, measure it, and let Claude Code hand it work.
</p>

<p align="center">
  <b>A side project of <a href="https://infraphysics.net">InfraPhysics</a>.</b>
</p>

---

> [!NOTE]
> Work in progress, built live on 2026-10-21. The reference machine is set up and the `apu` command works;
> measured benchmarks, the engine comparison and the full guide are landing next. The build log is in
> [`docs/journal.md`](docs/journal.md).

## TL;DR

```powershell
pip install --user git+https://github.com/yago-mendoza/apu-llm
apu setup      # installs Ollama, turns the integrated GPU on, downloads the right model for your RAM
apu ping       # alive? how fast?
apu ask "explain this error" -f build.log
```

<p align="center">
  <img src="docs/assets/intelligence-vs-frontier.svg" width="700" alt="Bar chart of the Artificial Analysis Intelligence Index, October 2026: GPT-5.6 Sol 58.9, Claude Opus 5.5 57.6, DeepSeek V4 Pro 53.2, Gemini 4 Argon 52.6 do not fit in 64 GB; Qwen3.8 27B 33.7, Qwen3.6 35B-A3B 18.2, Gemma 4 26B-A4B 16.7 and gpt-oss-20b 9.0 do">
</p>

## License

- **Code** (`src/`, `tools/`): [MIT](LICENSE).
- **Content** (guide, journal, measurements, figures): [CC BY 4.0](LICENSE-CONTENT).
