<!-- markdownlint-disable MD060 -->
# 🛠 Como personalizar o Dyno Race

Guia prático pra quem clona o repo e quer mexer. Vai do mais fácil (mudar um número no `.env`) ao mais avançado (adicionar novos sentidos pra rede).

## Camadas de personalização

| Camada | Onde | Pra quê |
|---|---|---|
| **1. Comportamento do jogo** | [.env](.env.example) | pontos, dificuldade, troféus, tamanho de janela |
| **2. Hiperparâmetros do NEAT** | [src/neat_config/neat-config.ini](src/neat_config/neat-config.ini) | tamanho da rede, taxas de mutação, especiação |
| **3. Sentidos da IA** | [src/ai/sensors.py](src/ai/sensors.py) | o que a rede "vê" (entradas) |
| **4. Função de fitness** | [src/ai/trainer.py](src/ai/trainer.py) | o que conta como "jogar bem" |

---

## 1) Mudar comportamento do jogo (`.env`)

Já está documentado no próprio [.env.example](.env.example). Os mais úteis pra demo:

- `POPULATION_SIZE=50` → quantos dinos correm em paralelo. O `.env` sobrescreve o `pop_size` do `neat-config.ini`.
- `AUTO_RESTART_DELAY=3` → tempo da tela "Geração X encerrada". Aumenta pra você comentar ao vivo.
- `GAME_SPEED_INITIAL` / `GAME_SPEED_MAX` → joga com a dificuldade.

---

## 2) Mexer no NEAT (`src/neat_config/neat-config.ini`)

Aqui é onde dá pra brincar com a "biologia" do algoritmo. Os campos mais didáticos:

> 💡 **Infos**: vários desses parâmetros (compat. threshold, elitism, taxas de mutação de pesos e topologia) podem ser sobrescritos via `.env` na **Seção 2 — Config avançada** (`NEAT_*`), sem precisar editar o `.ini`. Veja a tabela no [README](README.md#seção-2--config-avançada-neat). Use o `.ini` quando quiser mudar a topologia inicial / função de ativação / pesos iniciais (campos que ainda não têm override).

### Tamanho/forma da rede

```ini
num_inputs   = 6      # número de sentidos (precisa bater com sensors.py)
num_outputs  = 2      # PULAR e ABAIXAR
num_hidden   = 0      # neurônios escondidos no nascimento (NEAT começa minimal)
initial_connection = full_direct   # como conectar inputs→outputs no início
                                    # opções: unconnected | fs_neat_nohidden |
                                    # full_direct | full_nodirect | partial_direct 0.5
```

> 💡 **Quer começar com hidden neurons?** Aumente `num_hidden`. Quer rede totalmente desconectada começando do zero? `initial_connection = unconnected`.

### Pesos iniciais (a "personalidade" do nascimento)

```ini
weight_init_mean    = 0.0     # média dos pesos sorteados ao criar um neurônio
weight_init_stdev   = 1.0     # desvio padrão (quanto maior, mais "esquentado")
weight_min_value    = -30
weight_max_value    =  30
```

> 💡 Mudar `weight_init_stdev` de 1.0 pra 3.0 faz a geração 0 já ter dinos mais "ousados" — alguns vão pular muito, outros nada. Bom contraste pra mostrar diversidade.

### Mutação (motor da evolução)

```ini
weight_mutate_rate  = 0.8     # chance de qualquer peso ser perturbado a cada geração
weight_mutate_power = 0.5     # magnitude da perturbação
weight_replace_rate = 0.1     # chance de substituir o peso por um novo aleatório

conn_add_prob       = 0.5     # prob. de adicionar uma nova conexão
conn_delete_prob    = 0.5     # prob. de remover uma conexão
node_add_prob       = 0.2     # prob. de adicionar um novo neurônio (quebra uma conexão em duas)
node_delete_prob    = 0.2     # prob. de remover um neurônio
```

> 💡 **Pra ver a topologia crescer rápido:** sobe `node_add_prob` pra `0.5`. Em 5 gerações já aparecem hidden neurons na janela do cérebro.

### Função de ativação

```ini
activation_default      = tanh
activation_options      = tanh sigmoid relu
activation_mutate_rate  = 0.05    # chance de um neurônio trocar de função
```

> 💡 Pra forçar todo mundo a usar a mesma: deixe só uma em `activation_options` e zere `activation_mutate_rate`.

### Especiação (preserva diversidade)

```ini
[DefaultSpeciesSet]
compatibility_threshold = 3.0     # quanto menor, mais espécies (mais conservador)

[DefaultStagnation]
max_stagnation = 20               # gerações sem melhora antes de matar a espécie
species_elitism = 2               # protege as N melhores espécies da extinção
```

### Elitismo (quanto preservar dos campeões)

```ini
[DefaultReproduction]
elitism            = 2     # melhores N genomas passam intactos pra próxima geração
survival_threshold = 0.2   # 20% melhores de cada espécie podem reproduzir
```

📚 Documentação completa dos campos: <https://neat-python.readthedocs.io/en/latest/config_file.html>

---

## 3) Adicionar/remover sentidos da IA ([src/ai/sensors.py](src/ai/sensors.py))

Hoje a rede recebe 6 entradas. Pra adicionar uma sétima (ex.: distância até o **segundo** obstáculo):

1. Em `src/ai/sensors.py`, adicione o cálculo no `extract()` e o rótulo em `INPUT_LABELS`:

   ```python
   INPUT_LABELS = ["dist", "larg", "alt", "obs_y", "vel", "dino_y", "dist2"]

   def extract(dino, state):
       # … código existente …
       segundo = state.obstacles[1] if len(state.obstacles) > 1 else None
       dist2 = (segundo.x - dino.x) / config.WINDOW_WIDTH if segundo else 1.0
       return (dist, width, height, obs_y, speed, dino_y, dist2)
   ```

2. Em `src/neat_config/neat-config.ini`, atualize `num_inputs = 7`.
3. **Apague** `checkpoints/best_genome.pkl` (genoma antigo tem 6 entradas, não roda mais).

Pra remover uma entrada: o inverso — tira do `extract()`, remove do `INPUT_LABELS`, decrementa `num_inputs`, apaga checkpoint.

> 💡 **Dicas**: mostre primeiro a rede aprendendo só com `dist`, `larg`, `alt` (3 entradas). Depois adicione velocidade e veja como acelera o aprendizado. Aula visual sobre **engenharia de features**.

Pra mexer nas saídas é parecido: edite `OUTPUT_LABELS`, ajuste `num_outputs` e mude o decoder em [src/ai/trainer.py](src/ai/trainer.py) (`if out[0] > 0.5: d.jump()` etc.).

---

## 4) Mudar a função de fitness ([src/ai/trainer.py](src/ai/trainer.py))

A regra atual está no fim de `eval_genomes`:

```python
g.fitness = d.fitness + d.obstacles_passed * config.POINTS_PER_OBSTACLE
#           ^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^
#           tempo vivo   bônus por obstáculo
```

Variações pedagógicas:

- **Premiar só sobrevivência**: `g.fitness = d.fitness`.
- **Premiar só pular obstáculos**: `g.fitness = d.obstacles_passed * 100`.
- **Penalizar pular sem necessidade** (anti-pulador-compulsivo): conte pulos no `Dino` e subtraia.
- **Premiar distância**: `g.fitness = state.world.distance`.

Trocar a fitness é uma das demonstrações mais ricas: a mesma rede com fitness diferente desenvolve "personalidades" diferentes em poucas gerações.

---

## Workflow recomendado pra experimentar

```bash
make ai                    # treina do zero
# … alguns minutos …
# Editar neat-config.ini ou sensors.py
rm checkpoints/*.pkl       # se mudou inputs/outputs
make ai                    # treina de novo, compara
```

E acompanha tudo em [logs/dyno-race.log](logs/) — fica registrado o fitness por geração, dá pra plotar depois.
