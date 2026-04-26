<!-- markdownlint-disable MD060 MD013 -->
# AGENTS.md

Instruções para harnesses de IA (Claude Code, Codex, Cursor, etc.) trabalhando neste repositório. Segue o spec [agents.md](https://agents.md/).

## O que é o projeto

**Dyno Race** — clone do dino do Chrome em Python + pygame, com um modo de IA que evolui redes neurais via **NEAT** (NeuroEvolution of Augmenting Topologies). Uma segunda janela mostra a rede neural ao vivo. Existe também um dashboard local com gráficos do treino.

**Contexto de uso**: o autor usa o projeto em **mentorias de IA com o time** — toda mudança deve preservar a clareza didática (visualizações ao vivo, parâmetros fáceis de ajustar, código legível em sessão de pareamento).

## Idioma

Toda comunicação com o usuário, comentários no código, mensagens de log, mensagens de commit, docs e textos de UI são em **português brasileiro** com acentuação correta. Nunca substitua acentos por ASCII.

## Stack

- Python 3.11+
- `pygame` (jogo + visualização da rede)
- `neat-python` (NEAT)
- `python-dotenv` (config via `.env`)
- Frontend do dashboard: HTML/CSS/JS estáticos servidos por `http.server` + Chart.js via CDN. Sem framework, sem build step.

## Comandos

Use sempre o `Makefile` (não chame `python -m` direto a menos que esteja debugando):

```bash
make install      # cria .venv e instala deps
make run          # modo humano
make ai           # treina NEAT do zero (abre 3 superfícies: jogo, cérebro, dashboard no browser)
make ai-resume    # continua do melhor genoma salvo
make results      # só abre o dashboard (sem treinar)
make clean        # limpa .venv e checkpoints
```

Python do venv: `.venv/bin/python`. Não há suite de testes formal — validação é visual (rodar `make ai` e ver se carrega).

## Estrutura

```text
src/
├── main.py                       # CLI: --mode {human,ai,ai-resume}
├── config.py                     # carrega .env + NEAT_OVERRIDES
├── logger.py
├── game/                         # engine, dino, obstáculos, mundo, HUD
├── ai/
│   ├── sensors.py                # 6 features → entrada da rede
│   ├── trainer.py                # loop NEAT, ExperimentReporter (CSV), fitness
│   └── checkpoint.py
├── viz/
│   └── brain.py                  # janela com a rede ao vivo
├── reports/
│   └── live.py                   # dashboard HTTP local + HTML/JS embutido
└── neat_config/neat-config.ini   # hiperparâmetros NEAT default
```

Resultados em `results/dyno-race.csv` (uma linha por geração concluída, schema definido em `ExperimentReporter.FIELDNAMES`).

## Documentação no repo

Antes de mexer em algo, confirme se já há doc:

- [README.md](README.md) — overview, setup, tabela de envs.
- [INSTRUCTIONS.md](INSTRUCTIONS.md) — como personalizar (sensores, fitness, hiperparâmetros NEAT).
- [BRAIN.md](BRAIN.md) — anatomia da janela do cérebro.
- [ASSETS.md](ASSETS.md) — onde colocar PNGs / sprites.
- [CHANGELOG.md](CHANGELOG.md) — histórico de mudanças (atualize ao concluir uma feature relevante).

Mudanças visíveis ao usuário (env nova, alvo de Make novo, comportamento do dashboard) precisam aparecer em README/CHANGELOG.

## Configuração

`.env.example` é dividido em **duas seções**:

1. **Simples** — vars do dia-a-dia (já existentes desde o início).
2. **Avançada** — overrides do NEAT (`NEAT_*`), todas comentadas; descomentar sobrescreve `src/neat_config/neat-config.ini`. Os overrides são aplicados em `src/ai/trainer.py::_apply_neat_overrides`.

Pra adicionar um novo override do NEAT:

1. Adicione a entrada em `config.NEAT_OVERRIDES` (caminho `section_config.attr` → `_opt_float("NEAT_X")`).
2. Se for atributo `int` (raros: `elitism`, `species_elitism`, `max_stagnation`), inclua no set `_INT_NEAT_ATTRS` em `trainer.py`.
3. Adicione a linha comentada com descrição na seção avançada do `.env.example`.
4. Adicione na tabela do `README.md`.

## Convenções de código

- Sem comentários a menos que expliquem **por quê** algo não-óbvio. Não comente o que o código já mostra.
- Sem docstrings longas. Linha única quando ajuda.
- Sem abstrações prematuras. Função simples > classe genérica.
- Nada de feature flags ou camadas de compatibilidade — esse é um projeto pessoal/didático, sem usuários externos.
- Tipagem: use type hints quando óbvio (`int`, `str`, `dict`, `list[X]`, `X | None`). Não importe `Optional`/`Union`.
- Logs em `pt-BR`, nível `INFO` por padrão. Use `log = logger.get(__name__)`.

## Privacidade / arquivos sensíveis

Há um hook do harness do usuário que **bloqueia leitura de `.env*`** mesmo via `cat`/`Read`. Para escrever no `.env.example`:

1. Escreva o conteúdo em `/tmp/claude/<arquivo>.txt` (ou `$TMPDIR`).
2. Copie usando expansão pra escapar do filtro literal: `cp /tmp/.../x.txt $(printf '.%s.example' env)`.

Nunca leia ou modifique o `.env` real do usuário sem autorização explícita.

## Dashboard live

[src/reports/live.py](src/reports/live.py) tem o HTML/CSS/JS embutido como string Python (`_HTML_TEMPLATE`). Cuidados:

- Variáveis CSS em `:root` controlam o tema claro; `[data-theme="dark"]` sobrescreve. Cores novas devem usar variáveis (nunca hardcode hex no CSS) pra que o tema escuro funcione automaticamente.
- Tema persiste em `localStorage['dyno-theme']`. Há um script anti-flash no `<head>` que aplica o atributo antes do CSS pintar.
- Cores do Chart.js são atualizadas via `applyChartTheme()` no toggle.
- O HTML usa template tags `__DINO_FRAME_COUNT__` substituídas por `_html()` a cada request — adicione novos placeholders no mesmo padrão se precisar.
- Endpoints: `/`, `/api/results`, `/icon.png`, `/dino-run/{N}.png`. Pra adicionar um novo, edite `LiveHandler.do_GET`.

## Git / commits

- Commits em português, voz ativa, descritivos.
- Não faça commit a menos que o usuário peça explicitamente.
- Não use `git add -A` / `git add .` — adicione arquivos por nome.
- Não faça `--no-verify`, `--amend`, `push --force` sem permissão.
- Quando concluir uma feature relevante, ofereça atualização do `CHANGELOG.md` na seção `[Unreleased]`.

## Mentalidade

- Pequeno, didático, ao vivo. Se uma mudança torna o código menos legível em sessão de pareamento, ela está errada.
- Quando em dúvida sobre escopo, pergunte. O usuário prefere recomendações curtas (2-3 frases) com tradeoff claro do que planos longos.
