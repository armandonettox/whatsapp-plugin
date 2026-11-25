---
description: Ativa a triagem periódica do WhatsApp (loop). Ela só prepara respostas, nunca envia
argument-hint: "[intervalo, ex: 30m]"
---

Ative a triagem periódica do WhatsApp.

Intervalo pedido: `$ARGUMENTS` (se vazio, use 30m).

1. **Explique em uma frase o que o loop faz, antes de ligar:** a cada intervalo, ele roda a triagem das conversas pendentes e salva sugestões de resposta como rascunhos na pasta de rascunhos. **Ele nunca envia, nunca guarda rascunho no MCP e nunca posta em grupo**, porque ninguém está presente para confirmar. A pessoa revisa os rascunhos depois, com `/whatsapp:responder`.
2. **Ligue o loop** usando a função de execução periódica do agente. No Claude Code, é a skill `loop`: invoque-a com o intervalo e o comando `/whatsapp:pendentes loop`.
3. **Se o agente não tiver a função de loop,** diga isso com clareza e ofereça as alternativas: agendar `/whatsapp:pendentes loop` pelo recurso de tarefas agendadas do próprio agente, ou rodar `/whatsapp:pendentes` à mão quando quiser.
4. **Confirme o que ficou ativo:** o intervalo, o comando que roda a cada vez e como parar (no Claude Code, cancelando a tarefa do loop).

O loop precisa da bridge rodando. Se ela estiver parada, a triagem avisa que os dados podem estar desatualizados em vez de listar como se estivesse tudo em dia.
