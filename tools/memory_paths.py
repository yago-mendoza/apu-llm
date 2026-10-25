from pathlib import Path

OUT = Path(r"C:\Users\yagom\dev\infraphysics\media\articles\6471205\figures")

STYLE = (".bg{fill:#fcfcfb}.t1{fill:#0b0b0b}.t2{fill:#52514e}.line{stroke:#9c9b95}.box{fill:#f1f0ec;stroke:#c9c8c2}"
         ".acc{fill:#2a78d6}.accs{stroke:#2a78d6}.acct{fill:#ffffff}.chip{fill:#d9d8d2;stroke:#b9b8b2}"
         ".shared{fill:#e4e3df;stroke:#c9c8c2}.outline{fill:none;stroke:#9c9b95}"
         "@media (prefers-color-scheme:dark){.bg{fill:#1a1a19}.t1{fill:#f0efec}.t2{fill:#c3c2b7}.line{stroke:#7a7973}"
         ".box{fill:#262624;stroke:#4a4945}.acc{fill:#3987e5}.accs{stroke:#3987e5}.acct{fill:#ffffff}"
         ".chip{fill:#3a3936;stroke:#5c5b56}.shared{fill:#2e2e2b;stroke:#4a4945}.outline{fill:none;stroke:#7a7973}}")

T = {
    "en": dict(
        title="Where the GPU's memory is",
        left="Desktop PC with a graphics card", right="This laptop: an integrated GPU",
        cpu="CPU", ram="System RAM", own="its own bus", card="Graphics card, its own board",
        gpu="GPU", gddr="GDDR7 chips, 32 GB", wide="wide bus to the GPU only, 1,792 GB/s", pcie="PCIe",
        die="One piece of silicon: Ryzen AI 7 PRO 450", cores="CPU cores", igpu="Radeon 860M",
        bus1="one 128-bit bus,", bus2="128 GB/s for both",
        mem="LPDDR5X, 4 × 16 GB, soldered",
        carve1="512 MB carve-out,", carve2="set by the firmware at boot",
        sh1="the rest, lent to the GPU on demand (shared)",
        foot="Desktop figures are an RTX 5090's. Not to scale."),
    "es": dict(
        title="Dónde está la memoria de la GPU",
        left="PC de sobremesa con tarjeta gráfica", right="Este portátil: una GPU integrada",
        cpu="CPU", ram="RAM del sistema", own="su propio bus", card="Tarjeta gráfica, en su propia placa",
        gpu="GPU", gddr="Chips GDDR7, 32 GB", wide="bus ancho, solo a la GPU, 1.792 GB/s", pcie="PCIe",
        die="Una sola pieza de silicio: Ryzen AI 7 PRO 450", cores="Núcleos de CPU", igpu="Radeon 860M",
        bus1="un bus de 128 bits,", bus2="128 GB/s para las dos",
        mem="LPDDR5X, 4 × 16 GB, soldada",
        carve1="512 MB reservados,", carve2="los fija el firmware al arrancar",
        sh1="el resto, prestado a la GPU según la pide (compartida)",
        foot="Las cifras de sobremesa son las de una RTX 5090. Sin escala."),
}


def svg(t):
    W, H = 760, 352
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
         f"<title>{t['title']}</title>", f"<style>{STYLE}</style>",
         f'<rect class="bg" width="{W}" height="{H}" rx="8"/>',
         f'<text class="t1" x="24" y="34" font-size="18" font-weight="600">{t["title"]}</text>',
         f'<text class="t1" x="24" y="68" font-size="13" font-weight="600">{t["left"]}</text>',
         f'<text class="t1" x="392" y="68" font-size="13" font-weight="600">{t["right"]}</text>',
         '<line class="line" x1="376" y1="56" x2="376" y2="320" stroke-dasharray="2 4"/>']
    # left: desktop
    o += [
        '<rect class="box" x="24" y="110" width="104" height="48" rx="6"/>',
        f'<text class="t1" x="76" y="139" font-size="14" text-anchor="middle">{t["cpu"]}</text>',
        '<line class="line" x1="76" y1="158" x2="76" y2="232" stroke-width="3"/>',
        f'<text class="t2" x="84" y="200" font-size="11.5">{t["own"]}</text>',
        '<rect class="chip" x="24" y="232" width="104" height="40" rx="4"/>',
        f'<text class="t1" x="76" y="257" font-size="12.5" text-anchor="middle">{t["ram"]}</text>',
        '<rect class="outline" x="168" y="86" width="192" height="226" rx="10" stroke-dasharray="5 4"/>',
        f'<text class="t2" x="180" y="104" font-size="11.5">{t["card"]}</text>',
        '<line class="line" x1="128" y1="134" x2="196" y2="134" stroke-width="2"/>',
        f'<text class="t2" x="148" y="127" font-size="11.5" text-anchor="middle">{t["pcie"]}</text>',
        '<rect class="acc" x="196" y="114" width="140" height="44" rx="6"/>',
        f'<text class="acct" x="266" y="141" font-size="14" text-anchor="middle" font-weight="600">{t["gpu"]}</text>',
    ]
    for x in (214, 244, 274, 304):
        o.append(f'<line class="accs" x1="{x + 8}" y1="158" x2="{x + 8}" y2="236" stroke-width="4"/>')
    for x in (208, 238, 268, 298):
        o.append(f'<rect class="chip" x="{x}" y="236" width="28" height="30" rx="3"/>')
    o.append(f'<text class="t1" x="266" y="286" font-size="12.5" text-anchor="middle">{t["gddr"]}</text>')
    o.append(f'<text class="t2" x="264" y="302" font-size="11" text-anchor="middle">{t["wide"]}</text>')
    # right: APU
    o += [
        '<rect class="outline" x="392" y="86" width="344" height="92" rx="10" stroke-width="1.5"/>',
        f'<text class="t2" x="404" y="104" font-size="11.5">{t["die"]}</text>',
        '<rect class="box" x="404" y="116" width="150" height="48" rx="6"/>',
        f'<text class="t1" x="479" y="145" font-size="14" text-anchor="middle">{t["cores"]}</text>',
        '<rect class="acc" x="574" y="116" width="150" height="48" rx="6"/>',
        f'<text class="acct" x="649" y="145" font-size="14" text-anchor="middle" font-weight="600">{t["igpu"]}</text>',
        '<line class="line" x1="564" y1="178" x2="564" y2="226" stroke-width="5"/>',
        f'<text class="t2" x="576" y="198" font-size="11.5">{t["bus1"]}</text>',
        f'<text class="t2" x="576" y="212" font-size="11.5">{t["bus2"]}</text>',
        '<rect class="shared" x="392" y="226" width="344" height="56" rx="4"/>',
        '<rect class="acc" x="392" y="226" width="12" height="56" rx="3"/>',
        f'<text class="t1" x="570" y="248" font-size="12.5" text-anchor="middle">{t["mem"]}</text>',
        f'<text class="t2" x="570" y="268" font-size="11" text-anchor="middle">{t["sh1"]}</text>',
        '<line class="line" x1="398" y1="282" x2="398" y2="290"/>',
        f'<text class="t2" x="392" y="302" font-size="11.5">{t["carve1"]}</text>',
        f'<text class="t2" x="392" y="316" font-size="11.5">{t["carve2"]}</text>',
        f'<text class="t2" x="24" y="338" font-size="10.5">{t["foot"]}</text>',
        "</svg>", ""]
    return "\n".join(o)


for lang, t in T.items():
    (OUT / f"memory-paths{'' if lang == 'en' else '-es'}.svg").write_text(svg(t), encoding="utf-8")
