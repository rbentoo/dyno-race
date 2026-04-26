<!-- markdownlint-disable MD060 -->
# 🦖 Dyno Race

Clone do jogo do dinossauro do Chrome, em Python, com um modo onde uma rede neural **aprende a jogar sozinha** ao longo de gerações usando **NEAT** (NeuroEvolution of Augmenting Topologies). Uma segunda janela mostra a rede neural ao vivo, com nós ativando e pesos mudando.

## Por que NEAT?

**NEAT (NeuroEvolution of Augmenting Topologies)** é um algoritmo de neuroevolução: em vez de treinar uma rede com gradiente descendente, ele evolui uma população de redes via seleção natural (mutação, crossover, especiação). Cada geração mantém os melhores indivíduos e gera novos a partir deles.

A particularidade do NEAT é que ele evolui **a topologia junto com os pesos**: começa com a rede mínima (só inputs ligados aos outputs) e, ao longo das gerações, adiciona nós e conexões só quando isso melhora o fitness. O resultado são redes pequenas, interpretáveis e pedagogicamente ideais — dá pra desenhar todos os neurônios em tela e ver o cérebro evoluir.

Serve bem pra problemas onde:

- não há dataset rotulado, só uma função de fitness (ex.: jogos, controle, robótica simulada);
- a topologia ideal da rede não é conhecida de antemão;
- queremos algo leve, sem GPU.

Referência: Stanley & Miikkulainen, *"Evolving Neural Networks through Augmenting Topologies"* (2002) — [paper original](https://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf). Implementação usada aqui: [neat-python](https://neat-python.readthedocs.io/).

## Setup

Pré-requisitos: Python 3.11+, `make`.

```bash
make install      # cria .venv e instala pygame + neat-python + dotenv
```

## Como rodar

```bash
make run          # você joga (ESPAÇO pula, ↓ abaixa)
make ai           # NEAT do zero — abre 2 janelas (jogo + cérebro)
make ai-resume    # continua treinando do melhor genoma salvo em checkpoints/
make clean        # remove .venv e checkpoints
```

`ESC` fecha qualquer modo.

## Configuração via `.env`

Tudo ajustável sem mexer em código (`.env.example` lista os defaults):

| Variável | Default | O que faz |
|---|---|---|
| `POINTS_PER_OBSTACLE` | 10 | pontos por obstáculo ultrapassado |
| `TROPHY_BASE` | 8 | base dos troféus (8, 16, 32, 64…) |
| `POPULATION_SIZE` | 50 | tamanho da população NEAT |
| `AUTO_RESTART_DELAY` | 3 | segundos de pausa entre gerações |
| `GAME_SPEED_INITIAL` | 6 | velocidade inicial do mundo |
| `GAME_SPEED_MAX` | 20 | velocidade máxima |
| `WINDOW_WIDTH` / `_HEIGHT` | 900 / 300 | janela do jogo |
| `BRAIN_WINDOW_WIDTH` / `_HEIGHT` | 800 / 600 | janela do cérebro |
| `LOG_LEVEL` | INFO | nível de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `STATS_SAMPLE_INTERVAL` | 1.0 | intervalo do painel CPU/RAM na janela do cérebro |

Hiperparâmetros do NEAT (mutação, especiação, etc.) ficam em [`src/neat_config/neat-config.ini`](src/neat_config/neat-config.ini).

Pra **personalizar de verdade** (mudar tamanho da rede, pesos iniciais, taxas de mutação, sentidos da IA, função de fitness) → veja [INSTRUCTIONS.md](INSTRUCTIONS.md).

## Estrutura

```text
src/
├── main.py              # CLI: --mode {human,ai,ai-resume}
├── config.py            # carrega .env
├── game/                # engine, dino, obstáculos, mundo, HUD
├── ai/
│   ├── sensors.py       # 6 features normalizadas → entrada da rede
│   ├── trainer.py       # loop NEAT, fitness, geração
│   └── checkpoint.py    # salva/carrega o melhor genoma
└── viz/
    └── brain.py         # segunda janela com a rede ao vivo
src/neat_config/neat-config.ini   # hiperparâmetros NEAT
```

## Limitações conhecidas

- Sprites são retângulos coloridos (substituível por arte depois).
- A segunda janela usa `pygame._sdl2.Window` (pygame ≥ 2.5). Em sistemas sem essa API, cai num fallback que renderiza no buffer mas pode não mostrar.
- O modo `ai-resume` injeta o melhor genoma salvo numa nova população — bom pra continuar evoluindo, mas não restaura o estado completo das espécies.
