---
name: usar-whatsapp-mcp
description: Ensina a usar o servidor MCP de WhatsApp com segurança e economia - quais ferramentas existem, como achar contatos, ler conversas, baixar mídia, transcrever áudio e enviar (ou guardar rascunho) conforme o modo de envio. Use sempre que o pedido envolver ler, buscar, resumir ou enviar mensagens de WhatsApp.
---

# Usar o MCP de WhatsApp

Esta skill diz como usar as ferramentas do servidor `whatsapp` sem erro e sem gastar contexto à toa. As outras skills do plugin (`triagem-whatsapp`, `notas-por-contato`, `escrever-como-humano`, `mensagens-em-partes`) dependem desta para tudo que passa pelo MCP.

O nome completo das ferramentas muda conforme o agente (por exemplo `mcp__whatsapp__list_chats` ou `mcp__plugin_whatsapp_whatsapp__list_chats`). Procure pelo final do nome: `list_chats`, `send_message` e assim por diante.

## 1. Antes de qualquer coisa: em que modo o servidor está

O servidor tem três modos de envio, escolhidos por quem instalou (variável `WHATSAPP_SEND_MODE`). Descubra o seu olhando as ferramentas disponíveis e a instrução do servidor:

| Você vê | Modo | O que fazer |
|---|---|---|
| Nenhuma ferramenta `send_*` | `read-only` | Você só lê. Para uma resposta, escreva o texto na conversa e diga à pessoa que o envio está desligado de propósito. Não procure outro jeito de enviar. |
| `send_*` e `check_pending_send` | `two-step` | `send_*` só guarda um rascunho. A pessoa envia no terminal dela. Nunca diga que enviou. |
| `send_*` sem `check_pending_send` | `hook` | `send_*` envia direto. Mostre o texto e o destinatário e espere uma confirmação clara da pessoa antes de cada envio. |

Detalhes e exemplos do fluxo de confirmação em `references/confirmacao-de-envio.md`.

## 2. Mapa das ferramentas

Tabela completa, com parâmetros e armadilhas, em `references/ferramentas.md`. Em resumo:

| Quero... | Use |
|---|---|
| Achar um contato por nome ou número | `search_contacts`, e a skill `triagem-whatsapp` (`buscar_contato.py`) quando disponível |
| Ver as conversas mais recentes | `list_chats` |
| Ler o histórico de uma conversa | `list_messages` com `chat_jid` e `limit` pequeno |
| Ver o que veio antes e depois de uma mensagem | `get_message_context` |
| Saber quando falaram pela última vez | `get_last_interaction` |
| Baixar foto, vídeo, documento ou áudio | `download_media` |
| Transcrever um áudio | `transcribe_audio` (precisa do extra de áudio e do ffmpeg) |
| Enviar ou guardar rascunho | `send_message`, `send_file`, `send_audio_message` (conforme o modo) |

## 3. Ler com economia

- Peça só o que precisa: `limit` de 20 a 40 mensagens costuma bastar. Páginas com `page` quando faltar.
- Se a skill `triagem-whatsapp` estiver instalada, prefira os scripts dela (`listar_pendentes.py`, `resumo_contato.py`): leem o banco local e não gastam chamadas do MCP.
- Mídia aparece no histórico como `[audio]` ou `[image]`. Só baixe ou transcreva quando o conteúdo importar para a resposta.
- Conversa individual e grupo são coisas diferentes. Grupos só entram se a pessoa pedir.

## 4. Identificadores: o mesmo contato pode ter dois

Um contato aparece como `<número>@s.whatsapp.net` ou como `<id>@lid`, e a conversa recente pode estar em só um deles. Antes de dizer que não há mensagens, consulte os dois. Ao enviar, use o identificador pelo qual a pessoa de fato fala com você. Veja `references/identificacao-de-contatos.md`.

## 5. Enviar

1. **Nunca envie sem confirmação clara da pessoa para aquele texto específico.** Pedido de edição ("troca o oi") e pergunta ("pode mandar?") não são confirmação.
2. Mostre o destinatário e o texto exato, entre aspas.
3. Se o destinatário só tem número ou `@lid` sem nome, avise em vez de adivinhar quem é.
4. Não afirme em nome da pessoa algo que ela pode não ter feito ("já encaminhei", "já paguei").
5. Resposta em várias mensagens: use a skill `mensagens-em-partes` e peça uma única confirmação para todas as partes.
6. `send_file` não aceita legenda. Se precisar de texto junto, envie o texto em outra mensagem.
7. `send_audio_message` converte para Opus com o ffmpeg. Sem ffmpeg, use `send_file`.
8. Depois de enviar, diga o que foi enviado. No modo `two-step`, diga só que o rascunho foi guardado e dê o comando.

## 6. Sem os scripts, só com o MCP

Em alguns agentes os scripts das outras skills não rodam (por exemplo, o agente está em um container que não enxerga os dados da bridge). Se um script não existir ou falhar por falta do banco, **não desista: use as ferramentas do MCP**.

- Pendências: `list_chats` com `limit` pequeno e `sort_by="last_active"`, e veja a última mensagem de cada conversa.
- Histórico de um contato: `list_messages` com `chat_jid` e `limit` de 20 a 40.
- Contato: `search_contacts`, e confira os dois identificadores (`@lid` e `@s.whatsapp.net`).

Duas coisas mudam nesse caso: o resultado dos scripts (que junta os identificadores e avisa de dados antigos) passa a ser feito por você, e um caminho de arquivo devolvido por `download_media` pode não ser legível pelo agente. Diga isso à pessoa em vez de tentar abrir o arquivo.

## 7. Quando algo falha

Antes de investigar do zero, veja `references/problemas-da-bridge.md`: bridge parada, download que falha, mensagens que não chegam, backlog depois de reiniciar e ferramentas que não aparecem.

## Por que estas regras existem

- **Funcionar sem os scripts:** o plugin roda em vários agentes e em containers. Uma skill que só funciona com os scripts deixa o agente sem saída quando eles não estão lá.

- **Modos de envio:** o agente age em nome da pessoa e uma mensagem enviada não se desfaz. O servidor decide o que é permitido para valer em qualquer agente, inclusive os que não têm o guarda de confirmação do Claude Code.
- **Ler com economia:** conversas longas enchem o contexto e deixam o agente pior. Ler pouco e ler certo vale mais do que ler tudo.
- **Dois identificadores:** buscar só por um deles faz parecer que não há conversa, e enviar pelo outro pode ir para uma conversa diferente.
