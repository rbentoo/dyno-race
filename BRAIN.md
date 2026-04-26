<!-- markdownlint-disable MD060 -->
# 🧠 Como ler a janela do cérebro

A segunda janela mostra **a rede neural do melhor dino vivo da geração atual**, atualizada em tempo real. É aqui que se vê a IA "pensando".

## Anatomia da rede

```text
ENTRADAS (esquerda) ──► OCULTOS (meio) ──► SAÍDAS (direita)
       6 sentidos           N neurônios          2 ações
                          (cresce com gerações)
```

### 🔵 Entradas (esquerda) — o que o dino "vê"

| Label | O que mede |
|---|---|
| `dist`   | Distância horizontal até o próximo obstáculo (0 = grudou nele, 1 = nada à vista) |
| `larg`   | Largura do obstáculo |
| `alt`    | Altura do obstáculo |
| `obs_y`  | Posição vertical do obstáculo (cacto = baixo, pássaro alto = alto) |
| `vel`    | Velocidade atual do mundo (0 → 1, normalizada pela máxima) |
| `dino_y` | Altura atual do próprio dino (no chão? no ar?) |

Tudo é normalizado em [0, 1] — redes neurais aprendem melhor com valores na mesma escala.

### 🟠 Saídas (direita) — o que o dino faz

- **PULAR**: ativa quando o valor passa de 0.5
- **ABAIXAR**: idem

Ficam **verdes** quando a ação dispara naquele frame, laranja quando estão dormindo. A ação atual aparece grande no topo da janela.

### 🟣 Ocultos (meio) — neurônios criados pela evolução

A rede começa **sem ocultos** (`num_hidden = 0`). Quando uma mutação adiciona um neurônio (`node_add_prob`), ele aparece no meio da tela. Eles permitem combinações não-lineares — sem ocultos, a rede só consegue aprender regras tipo "se distância < X, pula", com ocultos ela pode aprender padrões compostos tipo "se for pássaro alto e estou pulando, abaixa".

## 🎨 Linhas (conexões)

| Cor | Significado |
|---|---|
| **🔵 Azul** | peso **positivo** — o sinal de origem **excita** o neurônio destino. Quanto mais ativa a entrada, mais ativo fica o destino. |
| **🔴 Vermelho** | peso **negativo** — o sinal de origem **inibe** o neurônio destino. Quanto mais ativa a entrada, *menos* ativo fica o destino. |
| **Espessura** | magnitude do peso. Linha grossa = aquela conexão tem muita influência; linha fina = pouca. |

Exemplo: se `dist → PULAR` está com aresta **vermelha grossa**, a IA aprendeu "quanto mais longe o obstáculo, *menos* devo pular" — ou seja, ela só pula quando está perto. Conexão azul fina de `vel → PULAR` = "velocidade alta empurra um pouquinho pra pular antes". Esse é o tipo de leitura que dá pra fazer ao vivo.

## ✨ Brilho dos nós (ativação)

O halo em volta de cada neurônio mostra **quanto ele está ativo agora**:

- Halo apagado → ativação ≈ 0 (neurônio quieto)
- Halo intenso → ativação alta (positiva ou negativa)

Pra inputs, isso é literal — `dist=0.9` faz o nó `dist` brilhar muito. Pra outputs, brilho alto + cor verde = a IA está mandando o dino agir.

## 📈 O que muda entre gerações

Quando uma geração acaba e a próxima começa, repare em:

1. **Pesos diferentes** → linhas mudam de cor e espessura. A evolução está ajustando "o quanto cada sentido importa".
2. **Topologia diferente** → podem aparecer (ou sumir) neurônios ocultos. NEAT cria/remove conexões e nós via mutação.
3. **Comportamento diferente** → a IA decide pular em outros momentos. É o efeito visível dos pesos novos.

> 💡 Dica: deixe a geração 1 jogando alguns segundos, observe a rede caótica. Depois pule pra geração 20+ — vai ver poucas conexões grossas, escolhidas pela seleção natural. Esse "destilar" das conexões úteis é o coração do NEAT.

## ⚙️ Notas técnicas

- A janela mostra sempre **o melhor dino vivo no momento** — pode trocar de "foco" se outro dino ultrapassar o líder no fitness.
- Atualizada a ~20 FPS (não 60) pra ficar mais legível ao olho — mudanças sutis ficam visíveis.
- O painel inferior lista valores numéricos exatos das entradas e saídas pra quem quiser conferir.
- IDs negativos (`-1`, `-2`, …) são entradas; `0`, `1` são saídas; números positivos maiores são neurônios ocultos criados pela evolução.

📚 Quer mexer no que a rede vê / nos hiperparâmetros? → [INSTRUCTIONS.md](INSTRUCTIONS.md).
