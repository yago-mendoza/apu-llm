# Claude Code hands a task to the local model (2026-10-21)

First end-to-end run of the `apu` MCP server, registered with
`claude mcp add --scope user apu -- <path>\apu.exe mcp` (`claude mcp get apu`: *Connected*).

Command, from a fresh headless Claude Code session:

```powershell
claude -p "Usa la herramienta local_llm_ask para que el modelo local resuma en 3 viñetas, en español, el archivo C:\Users\yagom\dev\apu-llm\docs\article-notes.md (pásalo en files). Luego devuélveme tal cual su respuesta y la línea de estadísticas del final, y en una frase tu valoración de la calidad del resumen." --allowedTools "mcp__apu__local_llm_ask"
```

Output, verbatim:

> Respuesta del modelo local, sin cambios:
>
> *   Establece requisitos de documentación rigurosa (notas de contexto, mediciones verificadas) y aclara explícitamente la relación entre Ollama y LM Studio: comparten el motor GGML y archivos GGUF, pero difieren en su implementación (servicio vs. aplicación), configuración de GPU por defecto y licenciamiento, manteniendo Ollama como principal por ser open source y scriptable a menos que los benchmarks indiquen lo contrario.
> *   Detalla las mediciones técnicas en la máquina de referencia (860M), contrastando el uso de memoria GPU (47,6 GiB en Ollama frente a 31,76 GiB en LM Studio), tiempos de descarga y rendimiento de generación bajo condiciones idénticas.
> *   Justifica decisiones de arquitectura como la selección del repositorio `apu-llam`, la elección de modelos específicos (Qwen) frente a alternativas menos adecuadas (Gemma 4), y el beneficio económico de contar con 64 GB de RAM en laptops para ejecutar grandes modelos de lenguaje.
>
> `[local model qwen3.6:35b-a3b · 228 tok at 14.7 tok/s · prompt 870 tok at 137 tok/s · load 29.2s · total 51.0s]`
>
> **Valoración:** La estructura es buena y cubre las tres partes del archivo, pero tiene errores que lo hacen poco fiable sin revisarlo. Dice "tiempos de descarga" donde el archivo habla del tiempo hasta descargar el modelo de memoria por inactividad (5 min frente a 1 h). Presenta la velocidad de generación como medida, cuando el archivo la marca como "pending". Escribe `apu-llam` en lugar de `apu-llm`. Y da como justificada la compra de 64 GB, cuando el archivo solo la plantea como pregunta pendiente.

What it shows: the delegation path works (cold load 29 s, then 14.7 tok/s on a short prompt), and the local model's summary has the shape right and four facts wrong, which the delegating model caught. The division of labour the tool description asks for: the local model drafts, the stronger model checks.
