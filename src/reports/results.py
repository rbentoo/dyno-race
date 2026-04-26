"""Gera um relatório HTML a partir de results/dyno-race.csv."""
import argparse
import csv
import html
import statistics
import webbrowser
from collections import defaultdict
from pathlib import Path

from src import config


CSV_PATH = config.ROOT / "results" / "dyno-race.csv"
HTML_PATH = config.ROOT / "results" / "dyno-race-report.html"

HELP_TEXTS = {
    "summary": (
        "Resumo por execução. Use melhor fit para comparar resultado máximo, fit final para saber onde o run parou, "
        "max speed para dificuldade alcançada, max species para diversidade e max nodes para complexidade da melhor rede."
    ),
    "top_generations": (
        "As 10 gerações com maior fitness da própria geração. Útil para descobrir em qual run e configuração apareceram os saltos."
    ),
    "config": (
        "Configuração registrada para cada run do top 10. Use esta tabela para comparar quais parâmetros geraram melhores resultados "
        "e decidir o próximo experimento."
    ),
    "best_fitness_run": (
        "Recorde histórico dentro do run até aquela geração. Deve subir em degraus; longos trechos planos indicam platô."
    ),
    "avg_fitness": (
        "Média da população na geração. Quando sobe junto com o recorde, a população inteira está melhorando; "
        "quando só o recorde sobe, pode ter sido um campeão isolado."
    ),
    "species_count": (
        "Quantidade de espécies. Mais espécies costuma indicar maior diversidade; poucas espécies por muito tempo podem limitar exploração."
    ),
    "best_nodes": (
        "Número de nós na melhor rede da geração. Crescimento pode indicar que o NEAT criou neurônios ocultos úteis; "
        "mais nós não é automaticamente melhor."
    ),
    "best_speed_reached": (
        "Maior velocidade alcançada pelo melhor dino da geração. Ajuda a ver se a IA está vencendo fases mais difíceis."
    ),
    "max_species_stagnation": (
        "Maior estagnação entre as espécies. Valor alto significa muitas gerações sem melhora naquela espécie; "
        "se fitness também não sobe, o treino pode estar preso."
    ),
}


def _float(row: dict, key: str, default: float = 0.0) -> float:
    try:
        value = row.get(key, "")
        return default if value == "" else float(value)
    except (TypeError, ValueError):
        return default


def _int(row: dict, key: str, default: int = 0) -> int:
    return int(_float(row, key, default))


def _fmt(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}"


def _help_button(text: str) -> str:
    return (
        '<button class="help" type="button" aria-label="Ajuda" '
        f'data-tooltip="{html.escape(text)}">?</button>'
    )


def _section_head(title: str, subtitle: str, help_text: str) -> str:
    return (
        '<div class="section-head">'
        f'<h2>{html.escape(title)}</h2>'
        '<div class="head-meta">'
        f'<span>{html.escape(subtitle)}</span>'
        f'{_help_button(help_text)}'
        '</div>'
        '</div>'
    )


def _load_rows(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"Nenhum CSV encontrado em {path}. Rode `make ai` primeiro.")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _group_runs(rows: list[dict]) -> dict[str, list[dict]]:
    runs: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        runs[row.get("run_id", "sem-run-id")].append(row)
    for run_rows in runs.values():
        run_rows.sort(key=lambda r: _int(r, "generation"))
    return dict(sorted(runs.items()))


def _run_summary(run_id: str, rows: list[dict]) -> dict:
    best_row = max(rows, key=lambda r: _float(r, "best_fitness_run"))
    last = rows[-1]
    gen_times = [_float(r, "generation_time_seconds") for r in rows]
    return {
        "run_id": run_id,
        "generations": len(rows),
        "best_fitness": _float(best_row, "best_fitness_run"),
        "best_generation": _int(best_row, "generation"),
        "last_fitness": _float(last, "best_fitness_run"),
        "max_speed": max(_float(r, "best_speed_reached") for r in rows),
        "max_species": max(_int(r, "species_count") for r in rows),
        "max_nodes": max(_int(r, "best_nodes") for r in rows),
        "avg_generation_time": statistics.mean(gen_times) if gen_times else 0.0,
        "population": _int(last, "population_size"),
        "speed": f"{_fmt(_float(last, 'game_speed_initial'), 0)}/{_fmt(_float(last, 'game_speed_max'), 0)}",
        "points": _int(last, "points_per_obstacle"),
        "resume": "sim" if _int(last, "resume") else "não",
    }


def _run_config_rows(summaries: list[dict], runs: dict[str, list[dict]]) -> list[list[str]]:
    config_rows = []
    for summary in summaries[:10]:
        row = runs[summary["run_id"]][-1]
        config_rows.append([
            summary["run_id"],
            row.get("population_size", ""),
            row.get("game_speed_initial", ""),
            row.get("game_speed_max", ""),
            row.get("points_per_obstacle", ""),
            row.get("auto_restart_delay", ""),
            row.get("resume", ""),
            row.get("compatibility_threshold", ""),
            row.get("max_stagnation", ""),
            row.get("species_elitism", ""),
            row.get("elitism", ""),
            row.get("survival_threshold", ""),
            row.get("node_add_prob", ""),
            row.get("conn_add_prob", ""),
            row.get("weight_mutate_rate", ""),
            row.get("weight_mutate_power", ""),
        ])
    return config_rows


def _scaled_points(points: list[tuple[float, float]], width: int, height: int, pad: int,
                   min_x: float, max_x: float, min_y: float, max_y: float) -> list[tuple[float, float, float, float]]:
    if not points:
        return []
    span_x = max(max_x - min_x, 1)
    span_y = max(max_y - min_y, 1)
    scaled = []
    for x, y in points:
        sx = pad + ((x - min_x) / span_x) * (width - pad * 2)
        sy = height - pad - ((y - min_y) / span_y) * (height - pad * 2)
        scaled.append((sx, sy, x, y))
    return scaled


def _chart(title: str, runs: dict[str, list[dict]], y_key: str, y_label: str) -> str:
    width, height, pad = 960, 300, 42
    colors = ["#2f6fed", "#1f9d55", "#dc3a3a", "#8b5cf6", "#d97706", "#0891b2", "#be2a5b"]
    raw_series = []
    all_x = []
    all_y = []
    for idx, (run_id, rows) in enumerate(runs.items()):
        points = [(_int(r, "generation"), _float(r, y_key)) for r in rows]
        if not points:
            continue
        all_x.extend(x for x, _ in points)
        all_y.extend(y for _, y in points)
        color = colors[idx % len(colors)]
        raw_series.append((run_id, points, color))
    if not raw_series:
        return ""
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    if min_y == max_y:
        min_y = max(0, min_y - 1)
        max_y += 1

    grid = []
    for i in range(5):
        y = pad + i * ((height - pad * 2) / 4)
        value = max_y - i * ((max_y - min_y) / 4)
        grid.append(
            f'<line x1="{pad}" y1="{y:.1f}" x2="{width - pad}" y2="{y:.1f}" class="grid" />'
            f'<text x="8" y="{y + 4:.1f}" class="tick">{_fmt(value)}</text>'
        )

    svg_parts = []
    legend_parts = []
    for run_id, points, color in raw_series:
        scaled = _scaled_points(points, width, height, pad, min_x, max_x, min_y, max_y)
        poly = " ".join(f"{sx:.1f},{sy:.1f}" for sx, sy, _, _ in scaled)
        safe_run = html.escape(run_id)
        svg_parts.append(
            f'<polyline class="series-line" data-run="{safe_run}" points="{poly}" '
            f'fill="none" stroke="{color}" stroke-width="2.6" />'
        )
        for sx, sy, gen, value in scaled:
            tooltip = html.escape(f"{run_id} | gen {int(gen)} | {y_label}: {_fmt(value, 3)}")
            svg_parts.append(
                f'<circle class="point" cx="{sx:.1f}" cy="{sy:.1f}" r="4.2" '
                f'fill="{color}" data-run="{safe_run}" data-x="{gen}" data-y="{value}" data-tooltip="{tooltip}">'
                f'<title>{tooltip}</title></circle>'
            )
        legend_parts.append(
            f'<button class="legend-item" type="button" data-run="{safe_run}" aria-pressed="true">'
            f'<span style="background:{color}"></span>{safe_run}</button>'
        )
    svg_lines = "\n".join(svg_parts)
    legend = "\n".join(legend_parts)
    grid_lines = "\n".join(grid)
    return f"""
    <section class="panel chart-panel" data-pad="{pad}" data-width="{width}" data-height="{height}" data-y-label="{html.escape(y_label)}">
      {_section_head(title, f"{y_label} por geração", HELP_TEXTS.get(y_key, ""))}
      <div class="chart-wrap">
        <svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">
          {grid_lines}
          <line x1="{pad}" y1="{height - pad}" x2="{width - pad}" y2="{height - pad}" class="axis" />
          <line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height - pad}" class="axis" />
          <text x="{pad}" y="{height - 10}" class="axis-label x-label">geração {int(min_x)} - {int(max_x)}</text>
          {svg_lines}
        </svg>
      </div>
      <div class="legend">{legend}</div>
    </section>
    """


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _build_html(rows: list[dict]) -> str:
    runs = _group_runs(rows)
    summaries = sorted(
        (_run_summary(run_id, run_rows) for run_id, run_rows in runs.items()),
        key=lambda s: s["best_fitness"],
        reverse=True,
    )
    best = summaries[0]
    summary_rows = [
        [
            s["run_id"], s["generations"], _fmt(s["best_fitness"]), s["best_generation"],
            _fmt(s["last_fitness"]), _fmt(s["max_speed"]), s["max_species"],
            s["max_nodes"], _fmt(s["avg_generation_time"], 2), s["population"],
            s["speed"], s["points"], s["resume"],
        ]
        for s in summaries[:10]
    ]
    top_generation_rows = sorted(rows, key=lambda r: _float(r, "best_fitness_generation"), reverse=True)[:10]
    top_generation_table = _table(
        ["run_id", "gen", "fit ger", "fit max", "avg", "species", "nodes", "speed", "stag"],
        [
            [
                r.get("run_id", ""), r.get("generation", ""),
                r.get("best_fitness_generation", ""), r.get("best_fitness_run", ""),
                r.get("avg_fitness", ""), r.get("species_count", ""),
                r.get("best_nodes", ""), r.get("best_speed_reached", ""),
                r.get("max_species_stagnation", ""),
            ]
            for r in top_generation_rows
        ],
    )
    summary_table = _table(
        ["run", "gens", "melhor fit", "gen melhor", "fit final", "max speed", "max species",
         "max nodes", "s/gen", "pop", "speed", "pts", "resume"],
        summary_rows,
    )
    config_table = _table(
        ["run", "pop", "speed ini", "speed max", "pts obst", "pausa", "resume",
         "compat", "max stag", "spec elit", "elitism", "survival", "node add",
         "conn add", "weight mut", "mut power"],
        _run_config_rows(summaries, runs),
    )
    chart_runs = {s["run_id"]: runs[s["run_id"]] for s in summaries[:10]}
    charts = "\n".join([
        _chart("Fitness Max Por Geração", chart_runs, "best_fitness_run", "fitness"),
        _chart("Fitness Médio Por Geração", chart_runs, "avg_fitness", "fitness médio"),
        _chart("Espécies Por Geração", chart_runs, "species_count", "espécies"),
        _chart("Complexidade Da Melhor Rede", chart_runs, "best_nodes", "nós"),
        _chart("Velocidade Alcançada Pelo Melhor", chart_runs, "best_speed_reached", "speed"),
        _chart("Estagnação Máxima", chart_runs, "max_species_stagnation", "stag"),
    ])
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>Dyno Race - Results</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f3f6fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #667085;
      --line: #d7deea;
      --line-soft: #edf1f7;
      --accent: #2f6fed;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 30px 22px 48px; }}
    header {{ display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 18px; }}
    h1 {{ margin: 0 0 4px; font-size: 32px; letter-spacing: 0; }}
    h2 {{ margin: 0; font-size: 18px; }}
    .muted {{ color: var(--muted); margin: 0; font-size: 13px; }}
    .badge {{ border: 1px solid var(--line); background: #fff; border-radius: 999px; padding: 7px 11px; color: var(--muted); font-size: 12px; white-space: nowrap; }}
    .cards {{ display: grid; grid-template-columns: repeat(4, minmax(150px, 1fr)); gap: 12px; margin: 18px 0; }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px 16px;
      background: var(--panel);
      box-shadow: 0 8px 24px rgba(23, 32, 51, 0.05);
      color: var(--muted);
      font-size: 13px;
    }}
    .card b {{ display: block; font-size: 24px; margin-top: 4px; color: var(--ink); }}
    .panel {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 16px;
      margin: 16px 0;
      box-shadow: 0 8px 24px rgba(23, 32, 51, 0.045);
    }}
    .section-head {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 12px; }}
    .section-head span {{ color: var(--muted); font-size: 12px; }}
    .head-meta {{ display: flex; align-items: center; gap: 8px; text-align: right; }}
    .help {{
      width: 24px;
      height: 24px;
      border: 1px solid var(--line);
      border-radius: 50%;
      background: #f8fafc;
      color: var(--accent);
      font-weight: 800;
      line-height: 1;
      cursor: help;
      flex: 0 0 auto;
    }}
    .help:hover {{ background: #eef5ff; border-color: #b9cff8; }}
    .table-wrap {{ overflow: auto; border: 1px solid var(--line); border-radius: 8px; }}
    table {{ border-collapse: collapse; width: 100%; min-width: 880px; font-size: 13px; background: #fff; }}
    th, td {{ border-bottom: 1px solid var(--line-soft); padding: 9px 10px; text-align: right; white-space: nowrap; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ background: #f8fafc; position: sticky; top: 0; color: #475467; font-weight: 650; }}
    tbody tr:hover {{ background: #f8fbff; }}
    .chart-wrap {{ border: 1px solid var(--line); border-radius: 8px; padding: 8px; overflow-x: auto; background: #fbfdff; }}
    svg {{ width: 100%; min-width: 760px; height: 300px; display: block; }}
    .axis {{ stroke: #98a2b3; stroke-width: 1.1; }}
    .grid {{ stroke: #e7edf5; stroke-width: 1; }}
    .axis-label, .tick {{ fill: #667085; font-size: 12px; }}
    .point {{ cursor: crosshair; stroke: #fff; stroke-width: 1.5; transition: r 120ms ease, stroke-width 120ms ease; }}
    .point:hover {{ r: 6.5; stroke-width: 2.5; }}
    .legend {{ margin: 10px 0 2px; display: flex; flex-wrap: wrap; gap: 8px; font-size: 12px; color: var(--muted); }}
    .legend-item {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      color: var(--muted);
      padding: 5px 9px;
      cursor: pointer;
      font: inherit;
    }}
    .legend-item:hover {{ border-color: #b9cff8; background: #f8fbff; }}
    .legend-item[aria-pressed="false"] {{ opacity: 0.45; text-decoration: line-through; }}
    .legend-item span {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; }}
    #tooltip {{
      position: fixed;
      z-index: 20;
      pointer-events: none;
      display: none;
      background: rgba(23, 32, 51, 0.94);
      color: #fff;
      padding: 7px 9px;
      border-radius: 6px;
      font-size: 12px;
      box-shadow: 0 10px 30px rgba(23, 32, 51, 0.25);
      max-width: 360px;
    }}
    @media (max-width: 780px) {{
      header {{ align-items: flex-start; flex-direction: column; }}
      .cards {{ grid-template-columns: repeat(2, minmax(140px, 1fr)); }}
      main {{ padding: 22px 14px 36px; }}
    }}
  </style>
</head>
<body>
  <main>
  <header>
    <div>
      <h1>Dyno Race Results</h1>
      <p class="muted">Fonte: {html.escape(str(CSV_PATH))}</p>
    </div>
    <div class="badge">Gerado localmente</div>
  </header>
  <div class="cards">
    <div class="card">Runs<b>{len(runs)}</b></div>
    <div class="card">Gerações<b>{len(rows)}</b></div>
    <div class="card">Melhor Fitness<b>{_fmt(best["best_fitness"])}</b></div>
    <div class="card">Melhor Run<b>{html.escape(best["run_id"])}</b></div>
  </div>
  <section class="panel">
    {_section_head("Top 10 Runs", "ordenado pelo melhor fitness histórico", HELP_TEXTS["summary"])}
    {summary_table}
  </section>
  {charts}
  <section class="panel">
    {_section_head("Top 10 Gerações", "maiores fitness de geração", HELP_TEXTS["top_generations"])}
    {top_generation_table}
  </section>
  <section class="panel">
    {_section_head("Config Das Top 10 Runs", "parâmetros gravados no CSV", HELP_TEXTS["config"])}
    {config_table}
  </section>
  </main>
  <div id="tooltip"></div>
  <script>
    const tooltip = document.getElementById('tooltip');
    const fmt = (value) => {{
      if (!Number.isFinite(value)) return '0';
      return Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(1);
    }};

    function scalePoint(x, y, bounds, width, height, pad) {{
      const spanX = Math.max(bounds.maxX - bounds.minX, 1);
      const spanY = Math.max(bounds.maxY - bounds.minY, 1);
      return {{
        sx: pad + ((x - bounds.minX) / spanX) * (width - pad * 2),
        sy: height - pad - ((y - bounds.minY) / spanY) * (height - pad * 2),
      }};
    }}

    function updateChart(panel) {{
      const width = Number(panel.dataset.width);
      const height = Number(panel.dataset.height);
      const pad = Number(panel.dataset.pad);
      const points = Array.from(panel.querySelectorAll('.point'));
      const lines = Array.from(panel.querySelectorAll('.series-line'));
      const buttons = Array.from(panel.querySelectorAll('.legend-item'));
      const activeRuns = new Set(buttons.filter((button) => button.getAttribute('aria-pressed') === 'true').map((button) => button.dataset.run));

      points.forEach((point) => {{
        point.style.display = activeRuns.has(point.dataset.run) ? '' : 'none';
      }});
      lines.forEach((line) => {{
        line.style.display = activeRuns.has(line.dataset.run) ? '' : 'none';
      }});

      const visiblePoints = points.filter((point) => activeRuns.has(point.dataset.run));
      if (visiblePoints.length === 0) return;

      const xs = visiblePoints.map((point) => Number(point.dataset.x));
      const ys = visiblePoints.map((point) => Number(point.dataset.y));
      let bounds = {{
        minX: Math.min(...xs),
        maxX: Math.max(...xs),
        minY: Math.min(...ys),
        maxY: Math.max(...ys),
      }};
      if (bounds.minY === bounds.maxY) {{
        bounds = {{ ...bounds, minY: Math.max(0, bounds.minY - 1), maxY: bounds.maxY + 1 }};
      }}

      panel.querySelectorAll('.tick').forEach((tick, index) => {{
        const value = bounds.maxY - index * ((bounds.maxY - bounds.minY) / 4);
        tick.textContent = fmt(value);
      }});
      const xLabel = panel.querySelector('.x-label');
      if (xLabel) xLabel.textContent = `geração ${{Math.round(bounds.minX)}} - ${{Math.round(bounds.maxX)}}`;

      const runs = new Set(points.map((point) => point.dataset.run));
      runs.forEach((run) => {{
        const runPoints = points
          .filter((point) => point.dataset.run === run)
          .sort((a, b) => Number(a.dataset.x) - Number(b.dataset.x));
        const coords = [];
        runPoints.forEach((point) => {{
          const scaled = scalePoint(Number(point.dataset.x), Number(point.dataset.y), bounds, width, height, pad);
          point.setAttribute('cx', scaled.sx.toFixed(1));
          point.setAttribute('cy', scaled.sy.toFixed(1));
          coords.push(`${{scaled.sx.toFixed(1)}},${{scaled.sy.toFixed(1)}}`);
        }});
        const line = lines.find((item) => item.dataset.run === run);
        if (line) line.setAttribute('points', coords.join(' '));
      }});
    }}

    document.querySelectorAll('.chart-panel').forEach((panel) => {{
      panel.querySelectorAll('.legend-item').forEach((button) => {{
        button.addEventListener('click', () => {{
          button.setAttribute('aria-pressed', button.getAttribute('aria-pressed') === 'true' ? 'false' : 'true');
          updateChart(panel);
        }});
      }});
      updateChart(panel);
    }});

    document.querySelectorAll('[data-tooltip]').forEach((item) => {{
      item.addEventListener('mouseenter', () => {{
        tooltip.textContent = item.dataset.tooltip;
        tooltip.style.display = 'block';
      }});
      item.addEventListener('mousemove', (event) => {{
        tooltip.style.left = `${{event.clientX + 12}}px`;
        tooltip.style.top = `${{event.clientY + 12}}px`;
      }});
      item.addEventListener('mouseleave', () => {{
        tooltip.style.display = 'none';
      }});
    }});
  </script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(prog="dyno-results")
    parser.add_argument("--no-open", action="store_true", help="gera o HTML sem abrir o navegador")
    args = parser.parse_args()
    rows = _load_rows(CSV_PATH)
    if not rows:
        raise SystemExit(f"CSV vazio em {CSV_PATH}. Rode `make ai` até pelo menos uma geração terminar.")
    HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    HTML_PATH.write_text(_build_html(rows), encoding="utf-8")
    print(f"Relatório gerado: {HTML_PATH}")
    if not args.no_open:
        webbrowser.open(HTML_PATH.as_uri())


if __name__ == "__main__":
    main()
