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
make results      # abre dashboard live que atualiza enquanto o treino roda
make clean        # remove .venv e checkpoints
```

`ESC` fecha qualquer modo. No modo IA, o dashboard live dos resultados abre automaticamente no navegador.

No modo IA, cada geração concluída adiciona uma linha em `results/dyno-race.csv`. O dashboard local lê o CSV a cada 2 minutos para comparar execuções pelo `run_id`; recarregue a página manualmente para ver uma geração recém-finalizada antes do próximo refresh automático. O comando `make results` abre o mesmo dashboard sem iniciar o treino.

O dashboard tem botão 🌙/☀️ no canto superior direito pra alternar entre tema claro e escuro — a escolha fica salva no `localStorage` do navegador, então persiste entre sessões.

## Configuração via `.env`

O [`.env.example`](.env.example) é dividido em **duas seções**: a simples e a avançada (hiperparâmetros do NEAT). Tudo ajustável sem mexer em código.

### Seção 1 — Config simples

| Variável | Default | O que faz |
|---|---|---|
| `POINTS_PER_OBSTACLE` | 10 | pontos por obstáculo ultrapassado |
| `TROPHY_BASE` | 8 | base dos troféus (8, 16, 32, 64…) |
| `POPULATION_SIZE` | 50 | tamanho da população NEAT |
| `AUTO_RESTART_DELAY` | 3 | segundos de pausa entre gerações |
| `GAME_SPEED_INITIAL` | 6 | velocidade inicial do mundo |
| `GAME_SPEED_MAX` | 20 | velocidade máxima |
| `WINDOW_WIDTH` / `_HEIGHT` | 1024 / 768 | janela do jogo |
| `BRAIN_WINDOW_WIDTH` / `_HEIGHT` | 1024 / 768 | janela do cérebro |
| `LOG_LEVEL` | INFO | nível de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `STATS_SAMPLE_INTERVAL` | 1.0 | intervalo do painel CPU/RAM na janela do cérebro |

### Seção 2 — Config avançada (NEAT)

Vêm comentadas no `.env.example`. **Descomentar = sobrescreve** o valor de [`src/neat_config/neat-config.ini`](src/neat_config/neat-config.ini) sem precisar editar o arquivo.

| Variável | Default `.ini` | O que faz |
|---|---|---|
| `NEAT_COMPATIBILITY_THRESHOLD` | 3.0 | distância máxima pra duas redes serem da mesma espécie |
| `NEAT_MAX_STAGNATION` | 20 | gerações sem melhora antes de uma espécie morrer |
| `NEAT_SPECIES_ELITISM` | 2 | espécies "elite" protegidas da extinção |
| `NEAT_ELITISM` | 2 | melhores genomas que passam intactos pra próxima geração |
| `NEAT_SURVIVAL_THRESHOLD` | 0.2 | fração que sobrevive pra reproduzir |
| `NEAT_NODE_ADD_PROB` / `_DELETE_PROB` | 0.2 / 0.2 | prob. de adicionar/remover um nó oculto |
| `NEAT_CONN_ADD_PROB` / `_DELETE_PROB` | 0.5 / 0.5 | prob. de adicionar/remover uma conexão |
| `NEAT_WEIGHT_MUTATE_RATE` | 0.8 | prob. de cada peso ser perturbado |
| `NEAT_WEIGHT_MUTATE_POWER` | 0.5 | magnitude da perturbação dos pesos |

Cada override aplicado aparece no log do treino (`NEAT override aplicado: …`).

Pra **personalizar de verdade** (mudar tamanho da rede, pesos iniciais, sentidos da IA, função de fitness) → veja [INSTRUCTIONS.md](INSTRUCTIONS.md).

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
