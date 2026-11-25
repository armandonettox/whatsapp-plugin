---
description: Prepara a resposta a um contato no jeito da pessoa e envia (ou guarda como rascunho) só depois da confirmação
argument-hint: "<nome ou número do contato>"
---

Prepare a resposta ao contato: `$ARGUMENTS`

Se nenhum contato foi informado, pergunte qual e, se houver rascunhos de uma rotina em loop na pasta de rascunhos (veja `caminhos.py` da skill `triagem-whatsapp`), ofereça começar por eles.

Siga esta ordem, usando as skills do plugin:

1. **Achar e entender o contato** (`triagem-whatsapp`): `buscar_contato.py` e `resumo_contato.py`. Se o histórico for curto, `aprofundar_historico.py`. Se houver mais de um contato com o nome, confirme qual é. Se só houver número, avise em vez de adivinhar.
2. **Ver a nota do contato** (`notas-por-contato`), se existir, para o tom e os compromissos abertos. Se for um contato recorrente e ainda não houver nota, crie.
3. **Áudio ou imagem pendente?** Baixe ou transcreva antes de redigir (`usar-whatsapp-mcp`).
4. **Redigir** (`escrever-como-humano`), no estilo daquele contato. Se a pessoa costuma mandar várias mensagens seguidas, divida com `mensagens-em-partes`.
5. **Mostrar para confirmação:** o destinatário e o texto exato (todas as partes, numeradas), e pedir uma confirmação clara. Pedido de mudança é uma nova rodada, não uma confirmação.
6. **Enviar conforme o modo do servidor** (`usar-whatsapp-mcp`): no `hook`, envie depois da confirmação; no `two-step`, guarde os rascunhos e entregue o comando único para a pessoa confirmar no terminal dela; no `read-only`, apenas entregue o texto e explique que o envio está desligado.
7. **Registrar** (`notas-por-contato`): a decisão tomada e qualquer promessa feita na mensagem.

Nunca envie sem confirmação clara, e nunca diga que enviou antes de ter enviado.
