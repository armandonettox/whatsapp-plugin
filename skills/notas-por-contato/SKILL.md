---
name: notas-por-contato
description: Mantém uma nota curta por contato de WhatsApp com o jeito de escrever da pessoa, a relação, os compromissos abertos e o histórico das últimas decisões, para não reanalisar o tom do zero a cada conversa. Use ao responder um contato recorrente, ao registrar uma promessa feita ("te retorno") ou ao ver o que ficou prometido.
---

# Notas por contato

Cada pessoa se comunica de um jeito diferente, e reanalisar o histórico inteiro toda vez é lento e caro. Esta skill guarda um resumo curto por contato e uma lista do que foi prometido.

As notas ficam **no computador da pessoa**, na pasta `data/notas` do plugin (ou onde `WHATSAPP_NOTES_DIR` apontar). O `criar_nota.py` mostra o caminho de cada nota que cria. Essa pasta não vai para o git.

Rode os scripts a partir da pasta desta skill (`python scripts/<nome>.py`).

## Scripts

| Script | O que faz |
|---|---|
| `criar_nota.py <chat_jid> [--relacao "..."]` | Cria o esqueleto da nota (nome da agenda, os identificadores, data). Se a nota já existir, achada por qualquer um dos identificadores, não duplica. |
| `criar_nota.py <chat_jid> --decisao "..."` | Registra uma linha no histórico de decisões (mantém as últimas 10). |
| `criar_nota.py <chat_jid> --compromisso "..."` | Abre um compromisso ("verificar com o financeiro"). |
| `criar_nota.py <chat_jid> --concluir "trecho"` | Conclui o primeiro compromisso aberto que contém o trecho. |
| `compromissos.py` | Lista os compromissos abertos de todos os contatos. |

O formato da nota está em `references/formato-da-nota.md`, com um exemplo em `references/exemplo-de-nota.md`.

## Quando usar

1. **Primeira vez que você responde um contato recorrente:** rode `criar_nota.py`, estude o estilo (skill `escrever-como-humano`) e preencha "Estilo identificado" e "Observações" com a ferramenta de edição de arquivos.
2. **Antes de redigir uma resposta:** leia a nota. Se existir, use como base do tom. Só refaça a análise se a conversa atual destoar muito do que a nota descreve.
3. **Depois que a pessoa reage a uma sugestão** (confirmou, pediu mudança ou decidiu não responder): registre com `--decisao`. Se ela corrigiu o tom, atualize também "Estilo identificado", e não só o histórico.
4. **Quando a mensagem enviada contém uma promessa** ("te retorno", "vou verificar", "levo seu caso para..."): registre com `--compromisso`. Quando for cumprida, ou quando a outra pessoa responder e resolver, conclua com `--concluir`.
5. **Na triagem**, rode `compromissos.py` e lembre a pessoa do que ficou em aberto.

## O que nunca guardar

- Conteúdo sensível de terceiros: números de outras pessoas, dados de saúde, financeiros ou de documentos.
- Cópia literal de mensagens privadas. Guarde o **padrão** de estilo, não o conteúdo.
- Notas de contatos de uso único (entregador, número desconhecido). Só vale para quem se repete.

## Por que

- **Nota curta por contato:** o tom muda de pessoa para pessoa, e o histórico de decisões é o que faz as sugestões melhorarem com o tempo.
- **Compromissos abertos:** a triagem só enxerga o que os outros mandaram. O que a própria pessoa prometeu some se ninguém registrar.
- **Só os padrões, nunca o conteúdo:** a nota é um arquivo local sem proteção especial. Guardar o conteúdo das conversas de outras pessoas ali é um risco que não compensa.
