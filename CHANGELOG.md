<!-- markdownlint-disable MD024 MD060 -->
# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Datas no formato `YYYY-MM-DD`.

## [Unreleased]

### Adicionado

- **Dashboard live** ([src/reports/live.py](src/reports/live.py)) substitui o antigo gerador estático `src/reports/results.py`. Servidor HTTP local serve `/`, `/api/results`, `/icon.png` e `/dino-run/{N}.png`; auto-refresh a cada 2 minutos.
- Tema claro/escuro no dashboard com botão 🌙/☀️ no canto superior direito; preferência persistida em `localStorage['dyno-theme']` com script anti-flash no `<head>`.
- Animação do dino no header do dashboard ciclando os frames de `assets/dino/Run (N).png` a cada 90 ms; contagem de frames calculada a cada request por `_dino_run_frame_count()`.
- Filtro de runs no dashboard (dropdown com checkboxes) e card de configuração detalhada por run (parâmetros do `.env` + `neat-config.ini`).
- Seção avançada no [`.env.example`](.env.example) com 11 overrides opcionais do NEAT (`NEAT_COMPATIBILITY_THRESHOLD`, `NEAT_MAX_STAGNATION`, `NEAT_SPECIES_ELITISM`, `NEAT_ELITISM`, `NEAT_SURVIVAL_THRESHOLD`, `NEAT_NODE_ADD_PROB`, `NEAT_NODE_DELETE_PROB`, `NEAT_CONN_ADD_PROB`, `NEAT_CONN_DELETE_PROB`, `NEAT_WEIGHT_MUTATE_RATE`, `NEAT_WEIGHT_MUTATE_POWER`). Todas comentadas por padrão; descomentar sobrescreve o `src/neat_config/neat-config.ini` sem precisar editar código.
- Helper `config.NEAT_OVERRIDES` em [src/config.py](src/config.py) e função `_apply_neat_overrides()` em [src/ai/trainer.py](src/ai/trainer.py) que aplicam as overrides após carregar o `.ini`. Cada override aplicado é logada (`NEAT override aplicado: …`).
- `STATS_SAMPLE_INTERVAL` no `.env` controla o intervalo de amostragem do painel CPU/RAM da janela do cérebro.
- Tempo decorrido no HUD durante o treino.
- Tabela das overrides do NEAT no [README.md](README.md) e atalho documentado no [INSTRUCTIONS.md](INSTRUCTIONS.md).

### Alterado

- `.env.example` reorganizado em duas seções: **Simples** (uso diário) e **Avançada** (NEAT). A simples mantém o que já existia.
- `make results` agora abre o dashboard live em vez de gerar HTML estático.
- README atualizado com a tabela completa do `.env`, menção ao tema claro/escuro do dashboard e à seção avançada.

### Removido

- `src/reports/results.py` (gerador HTML estático) — substituído pelo dashboard live com auto-refresh.

## [0.3.0] — 2026-04-26

### Adicionado

- Geração de relatórios HTML a partir dos resultados da IA.
- Novos alvos no `Makefile` para rodar e visualizar relatórios.

_Commit: `dcf44ec`_

## [0.2.1] — 2026-04-26

### Alterado

- Tamanho default da população NEAT ajustado para 50 (`pop_size` em `src/neat_config/neat-config.ini`).

_Commit: `2af7efb`_

## [0.2.0] — 2026-04-26

### Adicionado

- Suporte a `STATS_SAMPLE_INTERVAL` no `.env` para o painel de CPU/RAM da janela do cérebro.
- Exibição do tempo decorrido no HUD durante o treino.

### Alterado

- Variáveis de ambiente e documentação atualizadas.

_Commit: `d35433b`_

## [0.1.0] — 2026-04-26

### Adicionado

- Versão inicial do Dyno Race: clone do dino do Chrome em Python/pygame.
- Modo humano (`make run`).
- Modo IA com NEAT (`make ai`, `make ai-resume`) e janela secundária com visualização da rede neural ao vivo.
- Configuração via `.env` (pontos, troféus, dificuldade, janelas, log).
- Hiperparâmetros NEAT em `src/neat_config/neat-config.ini`.

_Commit: `2927447`_
