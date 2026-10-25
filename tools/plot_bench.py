"""Draw the benchmark plots of the InfraPhysics write-up from bench/results/*.json.

Writes SVG with a light and a dark look (prefers-color-scheme), in English and Spanish:

  python tools/plot_bench.py --out <dir>

  first-run-vs-clean-run[-es].svg   the withdrawn first comparison against the clean rerun
  engines-and-models[-es].svg       every clean configuration: two engines, two models, GPU and CPU

Every point is one run. Most come straight from the JSON files; the Ollama rows of the first
comparison were never saved as a file and are copied from docs/journal.md (Finding 3).
Standard library only.
"""

import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "bench" / "results"

STYLE = (".bg{fill:#fcfcfb}.t1{fill:#0b0b0b}.t2{fill:#52514e}.grid{stroke:#e4e3df}.base{stroke:#c9c8c2}"
         ".local{fill:#2a78d6}.lstroke{stroke:#2a78d6}.cloud{fill:#9c9b95}.cstroke{stroke:#9c9b95}.hollow{fill:#fcfcfb}.ring{stroke:#fcfcfb}"
         "@media (prefers-color-scheme:dark){.bg{fill:#1a1a19}.t1{fill:#f0efec}.t2{fill:#c3c2b7}.grid{stroke:#343431}"
         ".base{stroke:#4a4945}.local{fill:#3987e5}.lstroke{stroke:#3987e5}.cloud{fill:#7a7973}.cstroke{stroke:#7a7973}"
         ".hollow{fill:#1a1a19}.ring{stroke:#1a1a19}}")

TEXT = {
    "en": {
        "write": "Writing (tok/s)", "read": "Reading a 2,900-token prompt (tok/s)", "na": "not comparable",
        "t1": "The first comparison against the clean rerun",
        "s1": "Qwen3.6 35B-A3B, same weights. Each dot is one run; the number is the median.",
        "first": "First comparison (withdrawn)", "clean": "Clean rerun",
        "rows1": ["Ollama, Vulkan iGPU", "LM Studio, Vulkan iGPU", "Ollama, CPU only"],
        "f1": "Data: bench/results 133107, 135731 and 140315 in apu-llm; the Ollama rows of the first comparison from docs/journal.md.",
        "t2": "Two engines, two models, GPU and CPU",
        "s2": "Clean runs on the Radeon 860M laptop. Each dot is one run; the number is the median.",
        "gpu": "Vulkan iGPU", "cpu": "CPU only",
        "moe": "Qwen3.6 35B-A3B (MoE, ~3B active)", "dense": "Qwen3.8 27B (dense)",
        "rows2": ["Ollama, iGPU", "Ollama, CPU", "LM Studio, iGPU", "Ollama, iGPU", "Ollama, CPU"],
        "f2": "Data: bench/results 135731, 140315 and 143115 in apu-llm (three runs each for the 35B, two for the 27B).",
        "dec": ".", "thou": ",",
    },
    "es": {
        "write": "Escritura (tok/s)", "read": "Lectura de un prompt de 2.900 tokens (tok/s)", "na": "no comparable",
        "t1": "La primera comparación frente a la medida limpia",
        "s1": "Qwen3.6 35B-A3B, mismos pesos. Cada punto es una ejecución; el número es la mediana.",
        "first": "Primera comparación (retirada)", "clean": "Medida limpia",
        "rows1": ["Ollama, GPU integrada", "LM Studio, GPU integrada", "Ollama, solo CPU"],
        "f1": "Datos: bench/results 133107, 135731 y 140315 en apu-llm; las filas de Ollama de la primera comparación, de docs/journal.md.",
        "t2": "Dos motores, dos modelos, GPU y CPU",
        "s2": "Medidas limpias en el portátil de la Radeon 860M. Cada punto es una ejecución; el número es la mediana.",
        "gpu": "GPU integrada (Vulkan)", "cpu": "Solo CPU",
        "moe": "Qwen3.6 35B-A3B (MoE, ~3B activos)", "dense": "Qwen3.8 27B (denso)",
        "rows2": ["Ollama, GPU", "Ollama, CPU", "LM Studio, GPU", "Ollama, GPU", "Ollama, CPU"],
        "f2": "Datos: bench/results 135731, 140315 y 143115 en apu-llm (tres ejecuciones por configuración del 35B, dos del 27B).",
        "dec": ",", "thou": ".",
    },
}


def runs(stamp, engine):
    d = json.loads((RESULTS / f"{stamp}_engines.json").read_text(encoding="utf-8"))["results"][engine]
    return [r["gen"]["gen_tps"] for r in d["runs"]], [r["read"]["prompt_tps"] for r in d["runs"]]


def fmt(v, t):
    s = f"{v + 1e-9:.0f}" if v >= 20 else f"{v + 1e-9:.1f}"
    return s.replace(".", t["dec"])


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Plot:
    """Two panels side by side (writing, reading), one horizontal lane per row of dots."""

    W, LABEL, GAP, RIGHT = 760, 196, 40, 24

    def __init__(self, t, title, sub, wmax, rmax, wticks, rticks):
        self.t, self.out = t, []
        pw = (self.W - self.LABEL - self.GAP - self.RIGHT) / 2
        self.panels = [(self.LABEL, pw, wmax, wticks), (self.LABEL + pw + self.GAP, pw, rmax, rticks)]
        self.title, self.sub = title, sub

    def x(self, p, v):
        x0, pw, vmax, _ = self.panels[p]
        return x0 + pw * v / vmax

    def lane(self, y, label, values, cls, hollow=False, bold=False, note=None):
        """values: (writing runs, reading runs); an empty list prints the note instead."""
        if label:
            w = ' font-weight="600"' if bold else ""
            self.out.append(f'<text class="t1" x="{self.LABEL - 12}" y="{y + 4.5}" font-size="13" text-anchor="end"{w}>{esc(label)}</text>')
        for p, vals in enumerate(values):
            if not vals:
                if note:
                    self.out.append(f'<text class="t2" x="{self.x(p, 0) + 6}" y="{y + 4}" font-size="11.5" font-style="italic">{esc(note)}</text>')
                continue
            m = statistics.median(vals)
            xm = self.x(p, m)
            stroke = "lstroke" if cls == "local" else "cstroke"
            self.out.append(f'<line class="{stroke}" x1="{xm:.1f}" y1="{y - 8}" x2="{xm:.1f}" y2="{y + 8}" stroke-width="2"/>')
            for v in vals:
                xv = self.x(p, v)
                tip = f"<title>{fmt(v, self.t)} tok/s</title>"
                if hollow:
                    self.out.append(f'<circle class="hollow {stroke}" cx="{xv:.1f}" cy="{y}" r="4.5" stroke-width="2">{tip}</circle>')
                else:
                    self.out.append(f'<circle class="{cls} ring" cx="{xv:.1f}" cy="{y}" r="5" stroke-width="1.5">{tip}</circle>')
            xr = self.x(p, max(vals)) + 10
            self.out.append(f'<text class="t2" x="{xr:.1f}" y="{y + 4}" font-size="12">{fmt(m, self.t)}</text>')

    def group(self, y, label):
        self.out.append(f'<text class="t2" x="24" y="{y}" font-size="12" font-weight="600">{esc(label)}</text>')

    def render(self, top, bottom, legend, footer):
        H = bottom + 70
        head = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {H}" width="{self.W}" height="{H}" '
                f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
                f"<style>{STYLE}</style>",
                f'<rect class="bg" width="{self.W}" height="{H}" rx="8"/>',
                f'<text class="t1" x="24" y="34" font-size="18" font-weight="600">{esc(self.title)}</text>',
                f'<text class="t2" x="24" y="56" font-size="13">{esc(self.sub)}</text>']
        for p, name in enumerate((self.t["write"], self.t["read"])):
            x0, pw, vmax, ticks = self.panels[p]
            head.append(f'<text class="t1" x="{x0}" y="{top - 14}" font-size="12.5" font-weight="600">{esc(name)}</text>')
            for v in ticks:
                xv = self.x(p, v)
                cls = "base" if v == 0 else "grid"
                head.append(f'<line class="{cls}" x1="{xv:.1f}" y1="{top}" x2="{xv:.1f}" y2="{bottom}"/>')
                head.append(f'<text class="t2" x="{xv:.1f}" y="{bottom + 16}" font-size="11" text-anchor="middle">{v}</text>')
        lx, ly = 24, bottom + 40
        for label, cls, hollow in legend:
            stroke = "lstroke" if cls == "local" else "cstroke"
            if hollow:
                head.append(f'<circle class="hollow {stroke}" cx="{lx + 5}" cy="{ly - 4}" r="4.5" stroke-width="2"/>')
            else:
                head.append(f'<circle class="{cls}" cx="{lx + 5}" cy="{ly - 4}" r="5"/>')
            head.append(f'<text class="t2" x="{lx + 16}" y="{ly}" font-size="12">{esc(label)}</text>')
            lx += 30 + 7 * len(label)
        head.append(f'<text class="t2" x="24" y="{bottom + 60}" font-size="10.5">{esc(footer)}</text>')
        return "\n".join(head + self.out + ["</svg>", ""])


def first_vs_clean(t):
    # First comparison. LM Studio: the saved file. Ollama: docs/journal.md, Finding 3
    # (iGPU: one `apu ask` of 129 tokens, its reading taken on a 35-token prompt, so left out;
    #  CPU only: two runs, 11.3 and 10.8 writing, 55 and 52 reading).
    first = [([7.6], []), runs("20261021-133107", "lmstudio"), ([11.3, 10.8], [55, 52])]
    clean = [runs("20261021-135731", "ollama"), runs("20261021-140315", "lmstudio"), runs("20261021-135731", "ollama-cpu")]
    p = Plot(t, t["t1"], t["s1"], 14, 100, [0, 2, 4, 6, 8, 10, 12, 14], [0, 20, 40, 60, 80, 100])
    top, y = 96, 118
    for i, label in enumerate(t["rows1"]):
        p.lane(y, label, first[i], "cloud", hollow=True, note=t["na"])
        p.lane(y + 22, None, clean[i], "local")
        y += 66
    bottom = y - 30
    return p.render(top, bottom, [(t["first"], "cloud", True), (t["clean"], "local", False)], t["f1"])


def engines_and_models(t):
    rows = [(runs("20261021-135731", "ollama"), "local"), (runs("20261021-135731", "ollama-cpu"), "cloud"),
            (runs("20261021-140315", "lmstudio"), "local"),
            (runs("20261021-143115", "ollama"), "local"), (runs("20261021-143115", "ollama-cpu"), "cloud")]
    p = Plot(t, t["t2"], t["s2"], 14, 100, [0, 2, 4, 6, 8, 10, 12, 14], [0, 20, 40, 60, 80, 100])
    top, y = 96, 0
    y = 128
    p.group(y - 22, t["moe"])
    for i in range(3):
        p.lane(y, t["rows2"][i], rows[i][0], rows[i][1])
        y += 28
    y += 30
    p.group(y - 22, t["dense"])
    for i in range(3, 5):
        p.lane(y, t["rows2"][i], rows[i][0], rows[i][1])
        y += 28
    bottom = y - 12
    return p.render(top, bottom, [(t["gpu"], "local", False), (t["cpu"], "cloud", False)], t["f2"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "assets" / "plots"))
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    for lang, t in TEXT.items():
        suffix = "" if lang == "en" else "-es"
        for name, fn in (("first-run-vs-clean-run", first_vs_clean), ("engines-and-models", engines_and_models)):
            f = out / f"{name}{suffix}.svg"
            f.write_text(fn(t), encoding="utf-8")
            print(f"wrote {f}")


if __name__ == "__main__":
    main()
