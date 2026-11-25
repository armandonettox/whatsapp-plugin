---
description: Diagnóstico rápido do WhatsApp - modo de envio, ferramentas disponíveis, bridge e dados desatualizados
---

Faça um diagnóstico rápido do plugin de WhatsApp e responda em poucas linhas, sem enrolar. Não envie nenhuma mensagem.

1. **Modo de envio.** Olhe quais ferramentas do servidor `whatsapp` você tem: nenhuma `send_*` quer dizer `read-only`; `send_*` com `check_pending_send` quer dizer `two-step`; `send_*` sem `check_pending_send` quer dizer `hook`. Diga o modo em uma linha e o que ele permite (use a skill `usar-whatsapp-mcp`).
2. **O MCP responde?** Chame `list_chats` com `limit` 1. Se falhar, diga que o servidor ou a bridge não está respondendo e aponte `references/problemas-da-bridge.md` da skill `usar-whatsapp-mcp`.
3. **Dados em dia?** Use a skill `triagem-whatsapp`: rode `scripts/caminhos.py` (onde estão os dados) e `scripts/listar_pendentes.py`. Se aparecer `AVISO` de dados desatualizados, destaque isso: a bridge pode ter ficado parada.
4. **Rascunhos.** Se o modo for `two-step`, lembre que a pessoa vê os rascunhos esperando com `python confirm.py list`, na pasta `server/` do plugin, no terminal dela.

Termine com uma linha de resumo: tudo certo, ou o que precisa de atenção primeiro.
