---
description: Mostra o modo de envio do WhatsApp em uso e explica como mudar
---

Explique à pessoa, de forma curta, em que modo de envio o servidor de WhatsApp está e o que isso permite. Não mude nenhuma configuração e não envie nada.

1. Descubra o modo pelas ferramentas disponíveis e pela instrução do servidor: nenhuma `send_*` quer dizer `read-only`; `send_*` com `check_pending_send` quer dizer `two-step`; `send_*` sem `check_pending_send` quer dizer `hook`.
2. Diga o modo em uma linha e o que ele permite:
   - `read-only` (padrão): só lê. As ferramentas de envio nem aparecem.
   - `two-step`: o agente guarda rascunhos e a pessoa envia no terminal dela, com `python confirm.py send <id>`, na pasta `server/` do plugin.
   - `hook`: envio direto. Só deve ser usado onde existe o guarda de confirmação (o plugin no Claude Code liga esse modo sozinho).
3. Explique como mudar, em uma linha: pela variável `WHATSAPP_SEND_MODE` do servidor MCP (`read-only`, `two-step` ou `hook`), na configuração do agente, e que é preciso reiniciar o agente para a mudança valer. Se a pessoa usa outro agente que não o Claude Code, recomende `two-step` para poder enviar com confirmação.
4. Se a pessoa quiser o `two-step` e o agente dela tiver ferramenta de terminal, avise do limite descrito no README: um agente que consiga abrir um terminal próprio e simular o teclado poderia rodar o `confirm.py` sozinho, então vale restringir esse comando nas permissões do agente.

Termine perguntando se ela quer ajuda para mudar a configuração do agente dela.
