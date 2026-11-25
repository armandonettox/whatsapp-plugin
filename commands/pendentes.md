---
description: Lista as conversas de WhatsApp que esperam resposta, por ordem de urgência
argument-hint: "[loop]"
---

Faça a triagem das conversas de WhatsApp que esperam resposta, usando a skill `triagem-whatsapp`. Siga o passo a passo dela.

Argumento recebido: `$ARGUMENTS`

- **Sem argumento (você está com a pessoa presente):** apresente o resumo curto de uma linha por conversa (quem, o que disse, há quanto tempo, urgência e próximo passo) e pergunte qual ela quer responder. Não redija nenhuma resposta por conta própria.
- **Com o argumento `loop` (rotina automática, sem ninguém presente):** siga o "Modo loop" da skill `triagem-whatsapp` à risca. **Não envie nada, não guarde rascunho no MCP e não faça perguntas.** Só salve as sugestões na pasta de rascunhos, evitando duplicar o que já está preparado, e apague o rascunho de quem já foi respondido. Termine em silêncio, com no máximo uma linha dizendo quantos rascunhos novos ficaram prontos.

Em qualquer caso: só conversas individuais, e avise se os dados parecerem desatualizados.
