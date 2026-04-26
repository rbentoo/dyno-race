"""Dashboard live para acompanhar results/dyno-race.csv no navegador."""
import argparse
import csv
import json
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from src import config


CSV_PATH = config.ROOT / "results" / "dyno-race.csv"
ICON_PATH = config.ROOT / "assets" / "icon.png"
DINO_RUN_DIR = config.ROOT / "assets" / "dino"
REFRESH_SECONDS = 120


def _dino_run_frame_count() -> int:
    i = 1
    while (DINO_RUN_DIR / f"Run ({i}).png").exists():
        i += 1
    return i - 1


def _float(row: dict, key: str, default: float = 0.0) -> float:
    try:
        value = row.get(key, "")
        return default if value == "" else float(value)
    except (TypeError, ValueError):
        return default


def _read_rows() -> list[dict]:
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


CONFIG_FIELDS = [
    ("population_size", "população"),
    ("game_speed_initial", "speed inicial"),
    ("game_speed_max", "speed max"),
    ("points_per_obstacle", "pts / obst."),
    ("auto_restart_delay", "delay restart"),
    ("resume", "resume"),
    ("compatibility_threshold", "compat. threshold"),
    ("max_stagnation", "max stagnation"),
    ("species_elitism", "species elitism"),
    ("elitism", "elitism"),
    ("survival_threshold", "survival threshold"),
    ("node_add_prob", "node add prob"),
    ("node_delete_prob", "node del prob"),
    ("conn_add_prob", "conn add prob"),
    ("conn_delete_prob", "conn del prob"),
    ("weight_mutate_rate", "weight mut. rate"),
    ("weight_mutate_power", "weight mut. power"),
]


def _summaries(rows: list[dict]) -> list[dict]:
    runs: dict[str, list[dict]] = {}
    for row in rows:
        runs.setdefault(row.get("run_id", "sem-run-id"), []).append(row)
    summaries = []
    for run_id, run_rows in runs.items():
        best = max(run_rows, key=lambda r: _float(r, "best_fitness_run"))
        last = run_rows[-1]
        config_snapshot = {key: last.get(key, "") for key, _ in CONFIG_FIELDS}
        summaries.append({
            "run_id": run_id,
            "generations": len(run_rows),
            "best_fitness": _float(best, "best_fitness_run"),
            "best_generation": int(_float(best, "generation")),
            "last_fitness": _float(last, "best_fitness_run"),
            "population_size": last.get("population_size", ""),
            "speed": f"{last.get('game_speed_initial', '')}/{last.get('game_speed_max', '')}",
            "points_per_obstacle": last.get("points_per_obstacle", ""),
            "config": config_snapshot,
        })
    return sorted(summaries, key=lambda s: s["best_fitness"], reverse=True)


def _payload() -> dict:
    rows = _read_rows()
    return {
        "csv_path": str(CSV_PATH),
        "rows": rows,
        "summaries": _summaries(rows),
        "config_fields": CONFIG_FIELDS,
    }


def _html() -> str:
    return _HTML_TEMPLATE.replace("__DINO_FRAME_COUNT__", str(_dino_run_frame_count()))


_HTML_TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI Dyno Race Live</title>
  <script>
    (function () {
      try {
        const saved = localStorage.getItem('dyno-theme');
        if (saved === 'dark' || saved === 'light') {
          document.documentElement.setAttribute('data-theme', saved);
        }
      } catch (e) {}
    })();
  </script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    :root {
      --bg: #f3f6fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #667085;
      --line: #d7deea;
      --soft: #edf1f7;
      --accent: #2f6fed;
      --panel-soft: #f8fafc;
      --row-hover: #f8fbff;
      --shadow: 0 8px 24px rgba(23, 32, 51, 0.045);
    }
    [data-theme="dark"] {
      --bg: #0f1420;
      --panel: #161c2c;
      --ink: #e6ebf5;
      --muted: #8a93a6;
      --line: #2a3245;
      --soft: #1d2535;
      --accent: #6aa0ff;
      --panel-soft: #1b2333;
      --row-hover: #1f2839;
      --shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main { max-width: 1220px; margin: 0 auto; padding: 28px 20px 42px; }
    header { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-bottom: 16px; }
    .brand { display: flex; align-items: center; gap: 14px; }
    .brand img { width: 64px; height: 64px; image-rendering: pixelated; flex-shrink: 0; object-fit: contain; }
    h1 { margin: 0 0 4px; font-size: 32px; }
    h2 { margin: 0; font-size: 17px; }
    .muted { color: var(--muted); font-size: 13px; }
    .badge { border: 1px solid var(--line); background: var(--panel); border-radius: 999px; padding: 7px 11px; color: var(--muted); font-size: 12px; white-space: nowrap; }
    .header-actions { display: flex; align-items: center; gap: 10px; }
    .theme-toggle { width: 38px; height: 38px; border-radius: 50%; border: 1px solid var(--line); background: var(--panel); color: var(--ink); cursor: pointer; font-size: 18px; line-height: 1; display: inline-flex; align-items: center; justify-content: center; box-shadow: var(--shadow); transition: transform 0.15s ease, background 0.15s ease; }
    .theme-toggle:hover { transform: scale(1.06); background: var(--panel-soft); }
    .notice { border: 1px solid #c8d7f2; background: #eef5ff; color: #31527f; border-radius: 8px; padding: 10px 12px; margin: 12px 0 16px; font-size: 13px; }
    [data-theme="dark"] .notice { border-color: #2a3a5c; background: #182338; color: #b9cdf0; }
    [data-theme="dark"] #tooltip { background: rgba(230, 235, 245, 0.94); color: #0f1420; }
    .cards { display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 12px; margin: 16px 0; }
    .card { border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; background: var(--panel); color: var(--muted); box-shadow: var(--shadow); }
    .card b { display: block; color: var(--ink); font-size: 24px; margin-top: 4px; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
    .panel { border: 1px solid var(--line); border-radius: 8px; padding: 16px; background: var(--panel); box-shadow: var(--shadow); }
    .panel.full { grid-column: 1 / -1; }
    .panel-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; gap: 12px; }
    .help { width: 24px; height: 24px; border: 1px solid var(--line); border-radius: 50%; background: var(--panel-soft); color: var(--accent); font-weight: 800; cursor: help; }
    .chart-box { height: 300px; }
    .table-wrap { overflow: auto; border: 1px solid var(--line); border-radius: 8px; }
    table { border-collapse: collapse; width: 100%; min-width: 920px; font-size: 13px; }
    th, td { border-bottom: 1px solid var(--soft); padding: 8px 10px; text-align: right; white-space: nowrap; }
    th:first-child, td:first-child { text-align: left; }
    th { background: var(--panel-soft); color: var(--muted); }
    tbody tr:hover { background: var(--row-hover); }
    #tooltip { position: fixed; pointer-events: none; display: none; z-index: 20; max-width: 360px; background: rgba(23, 32, 51, 0.94); color: #fff; padding: 7px 9px; border-radius: 6px; font-size: 12px; }
    .config-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
    .config-card { border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; background: var(--panel-soft); }
    .config-card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px dashed var(--line); }
    .config-card-head .swatch { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
    .config-card-head .run { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; color: var(--ink); flex: 1; overflow: hidden; text-overflow: ellipsis; }
    .config-card-head .fit { font-weight: 700; color: var(--accent); font-size: 13px; }
    .config-card dl { display: grid; grid-template-columns: 1fr auto; gap: 4px 10px; margin: 0; font-size: 12px; }
    .config-card dt { color: var(--muted); }
    .config-card dd { margin: 0; color: var(--ink); font-variant-numeric: tabular-nums; }
    .filter-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 0 0 14px; }
    .filter-bar .label { font-size: 13px; color: var(--muted); }
    .filter-toggle { position: relative; }
    .filter-toggle > button { border: 1px solid var(--line); background: var(--panel); padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 13px; color: var(--ink); display: inline-flex; align-items: center; gap: 8px; }
    .filter-toggle > button:hover { background: var(--panel-soft); }
    .filter-toggle > button .caret { color: var(--muted); }
    .filter-panel { display: none; position: absolute; top: calc(100% + 6px); left: 0; z-index: 30; min-width: 320px; max-width: 460px; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; box-shadow: var(--shadow); padding: 10px; }
    .filter-panel.open { display: block; }
    .filter-panel-actions { display: flex; gap: 6px; padding: 0 4px 8px; border-bottom: 1px dashed var(--line); margin-bottom: 8px; }
    .filter-panel-actions button { border: 1px solid var(--line); background: var(--panel-soft); border-radius: 6px; padding: 5px 10px; font-size: 12px; cursor: pointer; color: var(--ink); }
    .filter-panel-actions button:hover { background: var(--row-hover); }
    .filter-list { max-height: 280px; overflow-y: auto; }
    .filter-item { display: flex; align-items: center; gap: 8px; padding: 5px 6px; border-radius: 6px; cursor: pointer; font-size: 13px; }
    .filter-item:hover { background: var(--row-hover); }
    .filter-item input { accent-color: var(--accent); }
    .filter-item .swatch { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
    .filter-item code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; color: var(--ink); }
    .filter-summary { font-size: 12px; color: var(--muted); }
    @media (max-width: 900px) {
      header { align-items: flex-start; flex-direction: column; }
      .cards { grid-template-columns: repeat(2, minmax(140px, 1fr)); }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div class="brand">
        <img id="dinoRun" src="/dino-run/1.png" alt="Dyno" onerror="this.style.display='none'" />
        <div>
          <h1>AI Dyno Race Live</h1>
          <div class="muted" id="source">Aguardando CSV...</div>
        </div>
      </div>
      <div class="header-actions">
        <div class="badge" id="status">atualizando...</div>
        <button class="theme-toggle" id="themeToggle" type="button" title="Alternar tema" aria-label="Alternar tema">🌙</button>
      </div>
    </header>
    <div class="notice">
      Atualiza automaticamente a cada 2 minutos. Para ver a última geração imediatamente, recarregue esta página manualmente.
    </div>

    <div class="filter-bar">
      <span class="label">Filtrar runs:</span>
      <div class="filter-toggle">
        <button id="filterButton" type="button">
          <span id="filterButtonLabel">Todas as runs</span>
          <span class="caret">▾</span>
        </button>
        <div class="filter-panel" id="filterPanel">
          <div class="filter-panel-actions">
            <button type="button" data-filter-action="all">Selecionar todas</button>
            <button type="button" data-filter-action="none">Limpar</button>
          </div>
          <div class="filter-list" id="filterList"></div>
        </div>
      </div>
      <span class="filter-summary" id="filterSummary"></span>
    </div>

    <div class="cards">
      <div class="card">Runs<b id="runsCount">0</b></div>
      <div class="card">Gerações<b id="rowsCount">0</b></div>
      <div class="card">Melhor Fitness<b id="bestFitness">0</b></div>
      <div class="card">Última Geração<b id="lastGeneration">0</b></div>
    </div>

    <div class="grid">
      <section class="panel full">
        <div class="panel-head">
          <h2>Fitness Max Por Geração</h2>
          <button class="help" data-tooltip="Recorde histórico do run. Clique nas legendas do gráfico para ocultar/mostrar runs.">?</button>
        </div>
        <div class="chart-box"><canvas id="fitnessChart"></canvas></div>
      </section>
      <section class="panel">
        <div class="panel-head">
          <h2>Fitness Médio</h2>
          <button class="help" data-tooltip="Mostra se a população inteira está melhorando, não só um campeão isolado.">?</button>
        </div>
        <div class="chart-box"><canvas id="avgChart"></canvas></div>
      </section>
      <section class="panel">
        <div class="panel-head">
          <h2>Espécies</h2>
          <button class="help" data-tooltip="Quantidade de espécies. Mais diversidade pode ajudar a escapar de platôs.">?</button>
        </div>
        <div class="chart-box"><canvas id="speciesChart"></canvas></div>
      </section>
      <section class="panel">
        <div class="panel-head">
          <h2>Velocidade Alcançada</h2>
          <button class="help" data-tooltip="Maior velocidade alcançada pelo melhor dino da geração.">?</button>
        </div>
        <div class="chart-box"><canvas id="speedChart"></canvas></div>
      </section>
      <section class="panel">
        <div class="panel-head">
          <h2>Complexidade</h2>
          <button class="help" data-tooltip="Nós da melhor rede. Crescer pode indicar surgimento de neurônios ocultos úteis.">?</button>
        </div>
        <div class="chart-box"><canvas id="nodesChart"></canvas></div>
      </section>
      <section class="panel full">
        <div class="panel-head">
          <h2>Top 10 Runs</h2>
          <button class="help" data-tooltip="Config e resultados dos 10 melhores runs, ordenados por melhor fitness histórico.">?</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>run</th><th>gens</th><th>melhor fit</th><th>gen melhor</th><th>fit final</th><th>pop</th><th>speed</th><th>pts obst</th></tr></thead>
            <tbody id="runsTable"></tbody>
          </table>
        </div>
      </section>
      <section class="panel full">
        <div class="panel-head">
          <h2>Configuração dos Top Runs</h2>
          <button class="help" data-tooltip="Parâmetros (.env + neat-config) usados em cada um dos 10 melhores runs. A bolinha colorida casa com a cor da linha nos gráficos.">?</button>
        </div>
        <div class="config-grid" id="configGrid"></div>
      </section>
    </div>
  </main>
  <div id="tooltip"></div>
  <script>
    const DINO_FRAME_COUNT = __DINO_FRAME_COUNT__;
    (function animateDino() {
      const img = document.getElementById('dinoRun');
      if (!img || DINO_FRAME_COUNT < 2) return;
      let frame = 1;
      setInterval(() => {
        frame = (frame % DINO_FRAME_COUNT) + 1;
        img.src = `/dino-run/${frame}.png`;
      }, 90);
    })();
    const charts = {};
    function currentTheme() {
      return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    }
    function applyChartTheme() {
      const dark = currentTheme() === 'dark';
      Chart.defaults.color = dark ? '#c5cce0' : '#475467';
      Chart.defaults.borderColor = dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';
      Object.values(charts).forEach((chart) => chart.update('none'));
    }
    applyChartTheme();
    const themeToggle = document.getElementById('themeToggle');
    function syncToggleIcon() {
      themeToggle.textContent = currentTheme() === 'dark' ? '☀️' : '🌙';
    }
    syncToggleIcon();
    themeToggle.addEventListener('click', () => {
      const next = currentTheme() === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('dyno-theme', next); } catch (e) {}
      syncToggleIcon();
      applyChartTheme();
    });

    const colors = ['#2f6fed', '#1f9d55', '#dc3a3a', '#8b5cf6', '#d97706', '#0891b2', '#be2a5b', '#4f46e5', '#0f766e', '#be185d'];
    const tooltip = document.getElementById('tooltip');
    const state = {
      payload: { rows: [], summaries: [], config_fields: [] },
      knownRuns: [],
      selected: null, // null = "all" (default), Set = filtro ativo
      colorByRun: new Map(),
    };

    function num(value) {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : 0;
    }

    function groupRows(rows) {
      const groups = new Map();
      rows.forEach((row) => {
        const run = row.run_id || 'sem-run-id';
        if (!groups.has(run)) groups.set(run, []);
        groups.get(run).push(row);
      });
      groups.forEach((items) => items.sort((a, b) => num(a.generation) - num(b.generation)));
      return groups;
    }

    function topRunIds(summaries) {
      return summaries.slice(0, 10).map((item) => item.run_id);
    }

    function colorForRun(runId) {
      return state.colorByRun.get(runId) || '#94a3b8';
    }

    function datasets(rows, summaries, key) {
      const groups = groupRows(rows);
      return topRunIds(summaries).map((runId) => {
        const color = colorForRun(runId);
        return {
          label: runId,
          data: (groups.get(runId) || []).map((row) => ({ x: num(row.generation), y: num(row[key]) })),
          borderColor: color,
          backgroundColor: color,
          borderWidth: 2,
          pointRadius: 3,
          pointHoverRadius: 6,
          tension: 0.18,
        };
      });
    }

    function chartOptions(yLabel) {
      return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'nearest', intersect: false },
        plugins: {
          legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label} | gen ${ctx.parsed.x} | ${yLabel}: ${ctx.parsed.y}`,
            },
          },
        },
        scales: {
          x: { type: 'linear', title: { display: true, text: 'geração' }, ticks: { precision: 0 } },
          y: { title: { display: true, text: yLabel }, beginAtZero: true },
        },
      };
    }

    function upsertChart(id, rows, summaries, key, label) {
      const data = { datasets: datasets(rows, summaries, key) };
      if (!charts[id]) {
        charts[id] = new Chart(document.getElementById(id), {
          type: 'line',
          data,
          options: chartOptions(label),
        });
        return;
      }
      charts[id].data = data;
      charts[id].update('none');
    }

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
      }[ch]));
    }

    function renderConfigs(summaries, configFields) {
      const fields = configFields || [];
      document.getElementById('configGrid').innerHTML = summaries.slice(0, 10).map((item, idx) => {
        const color = colors[idx % colors.length];
        const cfg = item.config || {};
        const rows = fields.map(([key, label]) => {
          const raw = cfg[key];
          const value = raw === '' || raw === undefined || raw === null ? '—' : raw;
          return `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd>`;
        }).join('');
        return `
          <div class="config-card">
            <div class="config-card-head">
              <span class="swatch" style="background:${color}"></span>
              <span class="run" title="${escapeHtml(item.run_id)}">${escapeHtml(item.run_id)}</span>
              <span class="fit">${item.best_fitness.toFixed(1)}</span>
            </div>
            <dl>${rows}</dl>
          </div>
        `;
      }).join('');
    }

    function renderTable(summaries) {
      document.getElementById('runsTable').innerHTML = summaries.slice(0, 10).map((item) => `
        <tr>
          <td>${escapeHtml(item.run_id)}</td>
          <td>${item.generations}</td>
          <td>${item.best_fitness.toFixed(1)}</td>
          <td>${item.best_generation}</td>
          <td>${item.last_fitness.toFixed(1)}</td>
          <td>${escapeHtml(item.population_size)}</td>
          <td>${escapeHtml(item.speed)}</td>
          <td>${escapeHtml(item.points_per_obstacle)}</td>
        </tr>
      `).join('');
    }

    function isSelected(runId) {
      return state.selected === null || state.selected.has(runId);
    }

    function applyFilter(payload) {
      const filteredRows = (payload.rows || []).filter((row) => isSelected(row.run_id || 'sem-run-id'));
      const filteredSummaries = (payload.summaries || []).filter((s) => isSelected(s.run_id));
      return { rows: filteredRows, summaries: filteredSummaries };
    }

    function syncKnownRuns(summaries) {
      // mantém ordem por melhor fitness; runs novas entram no fim
      const seen = new Set(state.knownRuns);
      summaries.forEach((s) => {
        if (!seen.has(s.run_id)) {
          state.knownRuns.push(s.run_id);
          seen.add(s.run_id);
        }
      });
      // atribui cor estável (índice no top 10 atual = cor; demais = cinza)
      state.colorByRun = new Map();
      summaries.forEach((s, idx) => {
        state.colorByRun.set(s.run_id, colors[idx % colors.length]);
      });
    }

    function renderFilterUi() {
      const summariesById = new Map((state.payload.summaries || []).map((s) => [s.run_id, s]));
      const list = document.getElementById('filterList');
      list.innerHTML = state.knownRuns.map((runId) => {
        const checked = isSelected(runId) ? 'checked' : '';
        const summary = summariesById.get(runId);
        const fit = summary ? `<span class="filter-summary">fit ${summary.best_fitness.toFixed(0)}</span>` : '';
        const color = colorForRun(runId);
        return `
          <label class="filter-item">
            <input type="checkbox" data-run="${escapeHtml(runId)}" ${checked} />
            <span class="swatch" style="background:${color}"></span>
            <code>${escapeHtml(runId)}</code>
            ${fit}
          </label>
        `;
      }).join('');
      const total = state.knownRuns.length;
      const active = state.selected === null ? total : state.selected.size;
      const label = state.selected === null
        ? `Todas as runs (${total})`
        : (active === 0 ? 'Nenhuma selecionada' : `${active} de ${total} runs`);
      document.getElementById('filterButtonLabel').textContent = label;
      document.getElementById('filterSummary').textContent = active === total ? '' : `mostrando ${active} de ${total}`;
    }

    function renderAll() {
      const filtered = applyFilter(state.payload);
      const best = filtered.summaries[0];
      document.getElementById('runsCount').textContent = filtered.summaries.length;
      document.getElementById('rowsCount').textContent = filtered.rows.length;
      document.getElementById('bestFitness').textContent = best ? best.best_fitness.toFixed(1) : '0';
      const lastRow = filtered.rows[filtered.rows.length - 1];
      document.getElementById('lastGeneration').textContent = lastRow ? lastRow.generation : '0';
      renderTable(filtered.summaries);
      renderConfigs(filtered.summaries, state.payload.config_fields);
      upsertChart('fitnessChart', filtered.rows, filtered.summaries, 'best_fitness_run', 'fitness max');
      upsertChart('avgChart', filtered.rows, filtered.summaries, 'avg_fitness', 'fitness médio');
      upsertChart('speciesChart', filtered.rows, filtered.summaries, 'species_count', 'espécies');
      upsertChart('speedChart', filtered.rows, filtered.summaries, 'best_speed_reached', 'speed');
      upsertChart('nodesChart', filtered.rows, filtered.summaries, 'best_nodes', 'nós');
      renderFilterUi();
    }

    async function refresh() {
      try {
        const response = await fetch('/api/results', { cache: 'no-store' });
        const payload = await response.json();
        state.payload = payload;
        syncKnownRuns(payload.summaries || []);
        document.getElementById('source').textContent = payload.csv_path;
        document.getElementById('status').textContent = `atualizado ${new Date().toLocaleTimeString()}`;
        renderAll();
      } catch (error) {
        document.getElementById('status').textContent = `erro: ${error.message}`;
      }
    }

    // ---- filtro: abrir/fechar dropdown, marcar/desmarcar, ações em lote ----
    const filterButton = document.getElementById('filterButton');
    const filterPanel = document.getElementById('filterPanel');
    filterButton.addEventListener('click', (event) => {
      event.stopPropagation();
      filterPanel.classList.toggle('open');
    });
    document.addEventListener('click', (event) => {
      if (!filterPanel.contains(event.target) && event.target !== filterButton) {
        filterPanel.classList.remove('open');
      }
    });
    filterPanel.addEventListener('click', (event) => {
      const action = event.target.dataset.filterAction;
      if (action === 'all') {
        state.selected = null;
        renderAll();
        return;
      }
      if (action === 'none') {
        state.selected = new Set();
        renderAll();
        return;
      }
      const checkbox = event.target.closest('input[type="checkbox"]');
      if (!checkbox) return;
      const runId = checkbox.dataset.run;
      if (state.selected === null) {
        state.selected = new Set(state.knownRuns);
      }
      if (checkbox.checked) {
        state.selected.add(runId);
      } else {
        state.selected.delete(runId);
      }
      // se voltou a ter todas marcadas, normaliza pra "all" (mostra label "Todas")
      if (state.selected.size === state.knownRuns.length) {
        state.selected = null;
      }
      renderAll();
    });

    document.querySelectorAll('[data-tooltip]').forEach((item) => {
      item.addEventListener('mouseenter', () => {
        tooltip.textContent = item.dataset.tooltip;
        tooltip.style.display = 'block';
      });
      item.addEventListener('mousemove', (event) => {
        tooltip.style.left = `${event.clientX + 12}px`;
        tooltip.style.top = `${event.clientY + 12}px`;
      });
      item.addEventListener('mouseleave', () => {
        tooltip.style.display = 'none';
      });
    });

    refresh();
    setInterval(refresh, """ + str(REFRESH_SECONDS * 1000) + """);
  </script>
</body>
</html>
"""


class LiveHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _send(self, body: str | bytes, content_type: str, status: int = 200):
        payload = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send(_html(), "text/html; charset=utf-8")
            return
        if path == "/api/results":
            self._send(json.dumps(_payload()), "application/json; charset=utf-8")
            return
        if path == "/icon.png" and ICON_PATH.exists():
            self._send(ICON_PATH.read_bytes(), "image/png")
            return
        if path.startswith("/dino-run/"):
            try:
                frame = int(path.rsplit("/", 1)[-1].split(".")[0])
            except ValueError:
                self._send("not found", "text/plain; charset=utf-8", 404)
                return
            frame_path = DINO_RUN_DIR / f"Run ({frame}).png"
            if frame_path.exists():
                self._send(frame_path.read_bytes(), "image/png")
                return
        self._send("not found", "text/plain; charset=utf-8", 404)


def _free_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class LiveServer:
    def __init__(self, server: ThreadingHTTPServer, thread: threading.Thread, url: str):
        self.server = server
        self.thread = thread
        self.url = url

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def start_background(port: int = 8765, open_browser: bool = True) -> LiveServer:
    port = _free_port(port)
    server = ThreadingHTTPServer(("127.0.0.1", port), LiveHandler)
    url = f"http://127.0.0.1:{port}/"
    thread = threading.Thread(target=server.serve_forever, name="dyno-results-live", daemon=True)
    thread.start()
    if open_browser:
        webbrowser.open(url)
    return LiveServer(server, thread, url)


def main():
    parser = argparse.ArgumentParser(prog="dyno-results-live")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    live_server = start_background(port=args.port, open_browser=not args.no_open)
    print(f"Dashboard live: {live_server.url}")
    print("Ctrl+C encerra o servidor.")
    try:
        live_server.thread.join()
    except KeyboardInterrupt:
        print("\nEncerrando dashboard live.")
    finally:
        live_server.close()


if __name__ == "__main__":
    main()
