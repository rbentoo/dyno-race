<!-- markdownlint-disable MD060 -->
# Onde colocar os assets visuais

Tudo que o jogo desenha — dinossauro, cactos, pássaro, ícone — pode ser **substituído por PNGs** em [assets/](assets/). Se o arquivo não existir, o jogo cai num desenho procedural (retângulo colorido) sem quebrar nada.

> Os PNGs devem ter **fundo transparente** (PNG-32 / RGBA).

## Estrutura geral

```text
assets/
├── icon.png             # ícone da janela (opcional)
├── dino/                # animações do dino (sprite sheet de frames)
│   ├── Run (1).png
│   ├── Run (2).png ...
│   ├── Jump (1).png ...
│   ├── Walk (1).png ...
│   └── Dead (1).png ...
├── cactus_small.png     # cactos: PNG estático (1 frame)
├── cactus_med.png
├── cactus_big.png
└── bird/                # pássaro: animação batendo asa
    ├── bird (1).png
    └── bird (2).png
```

## 🦖 Dino — animações por frame

Cada animação é uma sequência numerada no padrão `Nome (N).png`. O loader carrega `(1)`, `(2)`, `(3)`… até não achar mais.

| Pasta/Prefixo | Quando toca | Quantos frames? |
|---|---|---|
| `assets/dino/Run (N).png`  | correndo no chão | qualquer número (loop) |
| `assets/dino/Jump (N).png` | no ar | qualquer número (loop) |
| `assets/dino/Walk (N).png` | abaixado (substitui o "duck") | qualquer número (loop) |
| `assets/dino/Dead (N).png` | depois da colisão | qualquer número (trava no último) |
| `assets/dino/Idle (N).png` | parado (não usado hoje, reservado) | qualquer número (loop) |

**Tamanho recomendado**: 80×80 (correndo/pulando) ou 80×60 (abaixado). O loader escala automaticamente, mas o aspect ratio do PNG fica preservado se você exportar nessas proporções.

**Velocidade da animação**: ajustável em [src/game/dino.py](src/game/dino.py) na constante `ANIM_TICK` — número de frames de jogo (60fps) entre trocas de frame da animação. Menor = mais rápido.

### Cor por dino na população

No modo IA, cada dino recebe uma cor única (HSV via razão áurea). O loader gera variantes coloridas do sprite via:

1. `pygame.transform.grayscale()` — converte o PNG em tons de cinza preservando a iluminação.
2. `BLEND_RGB_ADD` clareia o resultado.
3. `BLEND_RGBA_MULT` multiplica pela cor do dino.

**Recomendação**: exporte o sprite numa cor neutra (verde, marrom, cinza claro). Sprites muito escuros ficam abafados depois do tint.

## 🌵 Cactos

PNGs estáticos (1 frame só), nomes fixos:

| Arquivo | Tamanho recomendado | Hitbox de colisão |
|---|---|---|
| `assets/cactus_small.png` | 18×35 | 18×35 |
| `assets/cactus_med.png`   | 25×45 | 25×45 |
| `assets/cactus_big.png`   | 30×55 | 30×55 |

## 🐦 Pássaro — animação + cor aleatória

Mesma convenção do dino: frames numerados em `assets/bird/bird (N).png`.

| Pasta/Prefixo | Quantos frames? | Tamanho recomendado |
|---|---|---|
| `assets/bird/bird (N).png` | 2+ (loop, bate asa) | 64×40 |

Cada pássaro que aparece recebe uma **cor saturada aleatória** (HSV), aplicada via o mesmo grayscale + multiply do dino. Por isso o sprite original deve ser **claro/neutro** pra cor ficar viva.

A velocidade da batida de asa é controlada por `BIRD_ANIM_TICK` em [src/game/obstacles.py](src/game/obstacles.py) (frames de jogo entre uma troca de frame e outra — menor = bate asa mais rápido).

> Hitbox de colisão segue 40×25 — o sprite é desenhado um pouco maior só pelo visual, então a dificuldade do jogo não muda.

## 🏆 Troféu (HUD)

`assets/trophy.png` — ícone exibido ao lado do contador de troféus no HUD do modo humano. Tamanho recomendado: **32×32** (será escalado pra 18×18 no painel).

Sem o arquivo, o jogo desenha um troféu procedural ([src/game/hud.py](src/game/hud.py)).

## 🎨 Ícone da janela

`assets/icon.png` — se existir, vira o ícone da janela do jogo. Tamanhos comuns: **32×32**, **64×64** ou **128×128**.

Sem o arquivo, o jogo desenha um mini-dino procedural ([src/game/icon.py](src/game/icon.py)).

> No **macOS**, o ícone da barra de título troca, mas o do **Dock** continua o do Python — limitação de quem roda via `python -m` em vez de empacotar como `.app`.

## Onde encontrar arte gratuita

- [opengameart.org](https://opengameart.org/) — CC0 / CC-BY
- [itch.io/game-assets/free](https://itch.io/game-assets/free) — vários packs
- [craftpix.net/freebies](https://craftpix.net/freebies/) — sprite sheets prontos
- Sprites do dino do Chrome são domínio público e dá pra extrair direto do `chrome://dino`

## Cache

Tudo é carregado **uma vez** e mantido em memória ([src/game/assets.py](src/game/assets.py)):

- `_cache` — sprites estáticos
- `_anim_cache` — animações por (pasta, prefixo, tamanho) e variantes coloridas
- `_tint_cache` — versões tintadas de sprites estáticos

Trocar um PNG **exige reiniciar o jogo** pra invalidar o cache.
