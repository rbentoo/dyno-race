<!-- markdownlint-disable MD060 -->
# CLAUDE.md

Instruções para o Claude Code neste repositório.

A fonte de verdade pras instruções de qualquer harness de IA é o [`AGENTS.md`](AGENTS.md). **Leia esse arquivo primeiro** — cobre stack, comandos, estrutura, convenções, dashboard, NEAT overrides e o fluxo de trabalho do autor.

## Reforços específicos pro Claude Code

- Responda sempre em **português brasileiro com acentuação correta** (já reforçado nas global instructions do usuário).
- Antes de ler qualquer arquivo `.env*`, peça permissão (regra global do usuário). Para escrever no `.env.example`, use o workaround documentado em [`AGENTS.md` → Privacidade](AGENTS.md#privacidade--arquivos-sensíveis).
- Use o agent **Explore** pra navegação de código quando precisar de mais de 3 buscas; pra lookups pontuais, `grep`/`Read` direto.
- Use **TodoWrite** quando a tarefa tiver 3+ passos não-triviais; pula em mudanças simples.
- Atualize o [`CHANGELOG.md`](CHANGELOG.md) na seção `[Unreleased]` quando concluir uma feature visível ao usuário (env nova, alvo de Make, mudança no dashboard).
- O autor usa o projeto pra **mentoria de IA com a equipe** — priorize legibilidade e visualização ao vivo sobre abstrações.
