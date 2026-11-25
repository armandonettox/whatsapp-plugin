# Ferramentas do MCP de WhatsApp: guia rápido

O nome completo muda conforme o agente. Procure pelo final do nome.

## Buscar e listar

| Ferramenta | Parâmetros (padrão) | Para que serve |
|---|---|---|
| `search_contacts` | `query` | Acha contatos por nome ou número, em parte do texto. Consulta só as conversas que o servidor já viu; um contato salvo no celular pode não aparecer. |
| `list_chats` | `query`, `limit=20`, `page=0`, `include_last_message=True`, `sort_by="last_active"` | Lista conversas. `query` filtra por nome ou identificador. |
| `get_chat` | `chat_jid`, `include_last_message=True` | Dados de uma conversa: nome e última mensagem. |
| `get_direct_chat_by_contact` | `sender_phone_number` | Acha a conversa direta com um número. |
| `get_contact_chats` | `jid`, `limit=20`, `page=0` | Todas as conversas em que um contato aparece, inclusive grupos. |
| `get_last_interaction` | `jid` | Última mensagem trocada com o contato. |

## Ler mensagens

| Ferramenta | Parâmetros (padrão) | Para que serve |
|---|---|---|
| `list_messages` | `after`, `before`, `sender_phone_number`, `chat_jid`, `query`, `limit=20`, `page=0`, `include_context=True`, `context_before=1`, `context_after=1` | Lê mensagens com filtros. `after` e `before` aceitam data em ISO-8601. `query` busca no texto. |
| `get_message_context` | `message_id`, `before=5`, `after=5` | Mostra as mensagens ao redor de uma mensagem específica. |

## Mídia

| Ferramenta | Parâmetros | Para que serve |
|---|---|---|
| `download_media` | `message_id`, `chat_jid` | Baixa foto, vídeo, documento ou áudio para o disco e devolve o caminho. |
| `transcribe_audio` | `message_id`, `chat_jid` | Transcreve um áudio com o Whisper local, sem enviar nada a um serviço externo. Precisa do extra de áudio (`uv sync --extra audio`) e do ffmpeg. O idioma vem de `WHATSAPP_AUDIO_LANGUAGE` e o modelo de `WHISPER_MODELO`. |

## Enviar (depende do modo de envio)

| Ferramenta | Parâmetros | Observações |
|---|---|---|
| `send_message` | `recipient`, `message` | Texto. |
| `send_file` | `recipient`, `media_path` | Foto, vídeo ou documento. **Não aceita legenda.** O caminho precisa ser absoluto e o arquivo existir. |
| `send_audio_message` | `recipient`, `media_path` | Mensagem de voz. Converte para Opus (.ogg) com o ffmpeg; sem ffmpeg, use `send_file`. |
| `check_pending_send` | `pending_id` | Só no modo `two-step`: diz se o rascunho foi `pending`, `sent`, `discarded`, `expired` ou `unknown`. Nunca mostra o conteúdo. |

`recipient` aceita um número com código do país e sem `+` (`5511999999999`) ou um identificador completo (`...@s.whatsapp.net`, `...@lid`, `...@g.us` para grupo). Contatos que só existem como `@lid` exigem o identificador completo.

## Armadilhas comuns

- `chat_jid` precisa ser exatamente o identificador do histórico. O mesmo contato tem dois (`@lid` e `@s.whatsapp.net`) e eles são conversas diferentes para o servidor.
- `list_messages` sem `chat_jid` mistura conversas. Use sempre `chat_jid` quando já souber qual é.
- `download_media` e `transcribe_audio` podem falhar se a bridge estiver parada ou a mídia tiver expirado. Veja `problemas-da-bridge.md`.
- Mensagens muito antigas podem não estar no banco: a bridge só guarda o que chegou enquanto estava ligada, mais o que o celular enviou na sincronização.
