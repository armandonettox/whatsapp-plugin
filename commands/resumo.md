---
description: Resume as mensagens novas de WhatsApp, ou o histórico de um contato
argument-hint: "[nome ou número do contato]"
---

Resuma o WhatsApp para a pessoa, usando a skill `triagem-whatsapp`. Não envie nada e não redija respostas, só informe.

Argumento recebido: `$ARGUMENTS`

- **Sem argumento:** rode `scripts/resumo_sessao.py` e `scripts/listar_pendentes.py` e diga, em poucas linhas, quantas mensagens novas chegaram, de quantas pessoas e quem espera resposta. Se a bridge tiver acabado de reiniciar, rode antes `scripts/aguardar_backlog.py`.
- **Com um contato:** use `scripts/buscar_contato.py` para achar a pessoa (confirme qual, se houver nomes parecidos) e `scripts/resumo_contato.py` para o histórico. Resuma o assunto, o que ficou em aberto de cada lado e o tom da conversa. Se a nota do contato existir (skill `notas-por-contato`), inclua os compromissos abertos.

Se aparecer `AVISO` de dados desatualizados, diga isso logo no começo: o resumo pode estar incompleto.
