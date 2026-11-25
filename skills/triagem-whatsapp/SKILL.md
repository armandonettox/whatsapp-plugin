---
name: triagem-whatsapp
description: Faz a triagem das conversas de WhatsApp - lista o que está pendente de resposta, identifica contatos, resume o histórico, decide o que vale responder e prepara a resposta. Use quando pedirem para ver as mensagens, o que precisa de resposta, um resumo de um contato, ou quando a rotina rodar em loop sem ninguém presente.
---

# Triagem de WhatsApp

Esta skill descobre o que precisa de atenção e em que ordem, usando scripts que leem o banco local da bridge. Isso é mais rápido e gasta menos contexto do que paginar `list_chats` e `list_messages` pelo MCP. O MCP entra depois, para baixar mídia, transcrever e enviar (skill `usar-whatsapp-mcp`).

Rode os scripts a partir da pasta desta skill (`python scripts/<nome>.py`; use `python3` ou `py` conforme o sistema). Se a pasta de dados não for a padrão, veja onde estão com `python scripts/caminhos.py`.

## Scripts

| Script | O que faz |
|---|---|
| `listar_pendentes.py` | Lista as conversas **individuais** em que a última mensagem é da outra pessoa. Ignora grupos, newsletters e listas de transmissão. Junta os dois identificadores da mesma pessoa. |
| `buscar_contato.py <nome ou número>` | Acha o contato de uma vez: junta os identificadores, mostra quem falou por último e se existe nota. Mostra mais de um resultado se houver nomes parecidos. |
| `resumo_contato.py <chat_jid> [--limite N]` | Histórico compacto de um contato, direto do banco. |
| `aprofundar_historico.py <chat_jid>` | Pede ao celular, pela bridge, as mensagens antigas do contato e repete até o banco parar de crescer. Use quando o histórico estiver curto demais para entender o assunto. |
| `aguardar_backlog.py` | Espera o backlog terminar de chegar depois de reiniciar a bridge. |
| `resumo_sessao.py [--aguardar] [--json]` | Conta as mensagens recebidas desde a última vez que rodou. |
| `caminhos.py` | Mostra onde ficam os bancos, as notas e os rascunhos. |

## Passo a passo

0. **A bridge está rodando?** Ela pode cair no meio da sessão. Se acabou de reiniciar, rode `aguardar_backlog.py` antes de concluir que não há mensagens novas: o backlog chega por vários minutos.
1. Rode `listar_pendentes.py`. **Se imprimir `AVISO: ...` de dados desatualizados, nunca apresente a lista como o estado atual**: avise que a bridge pode ter perdido conversas enquanto esteve parada.
2. Se a skill `notas-por-contato` estiver instalada, rode `compromissos.py` e mencione em uma linha o que a pessoa prometeu fazer e ainda está aberto.
3. Para identificar um contato (a pessoa citou um nome, ou o pendente veio só com número ou `@lid`), use `buscar_contato.py`. Se vier só número sem nome, **avise em vez de inventar quem é**. Se houver mais de um resultado, confirme com a pessoa qual é.
4. Para entender o assunto, rode `resumo_contato.py <chat_jid> --limite 40`. Se o histórico for curto (menos de uns 40 mensagens, ou só de poucas semanas), rode antes `aprofundar_historico.py`: sem isso, conclusões como "ele nunca falou X" podem estar erradas.
5. Se a última mensagem for áudio ou imagem, baixe ou transcreva antes de avaliar (skill `usar-whatsapp-mcp`).
6. **Vale responder?** Aplique `references/quando-nao-responder.md`. Assunto importante sempre merece resposta, por mais antigo que seja. Só um fechamento trivial e tardio pode ser dispensado.
7. Apresente um resumo curto, uma linha por conversa: quem é, o que a pessoa disse (trecho), há quanto tempo, urgência (alta, média, baixa ou sem necessidade de resposta) e o próximo passo sugerido.
8. Para responder, siga para: `notas-por-contato` (histórico do tom e compromissos), `escrever-como-humano` (redigir), `mensagens-em-partes` (se for dividir) e `usar-whatsapp-mcp` (enviar ou guardar rascunho).

## Sem os scripts

Se os scripts não rodarem (agente em container sem acesso ao banco da bridge, ou sem Python), faça a mesma triagem pelo MCP, seguindo a skill `usar-whatsapp-mcp`: `list_chats` para as conversas recentes, `list_messages` para o histórico e `search_contacts` para identificar. Você perde a união automática dos dois identificadores e o aviso de dados antigos: confira os dois identificadores à mão e avise a pessoa se a última mensagem de todas as conversas for antiga.

## Modo loop (sem ninguém presente)

Quando a triagem roda automaticamente (por exemplo, com `/whatsapp:loop`), ninguém está ali para confirmar nada. Portanto:

- **Nunca envie, nunca guarde rascunho no MCP e nunca poste em grupo.** O loop só prepara.
- Para cada conversa que merece resposta, salve a sugestão em `<pasta de rascunhos>/<slug>.md` (veja `caminhos.py`; crie a pasta se não existir):

  ```
  # <Nome do contato> (<chat_jid>)

  Última mensagem pendente: "<texto, ou [áudio]/[imagem] transcrito>" - <data e hora>
  Contexto: <uma ou duas frases do que a pessoa precisa>
  Tom: <sinais do estilo, da nota do contato>
  Sugestão: <texto exato da resposta, ou as partes numeradas>
  ```

- **Antes de escrever, veja se o rascunho já existe.** Mesma mensagem pendente: não sobrescreva, já está preparado. Chegou mensagem nova depois do rascunho: atualize. A pessoa já respondeu aquela conversa: apague o rascunho.
- Rode em silêncio: o resultado são os arquivos. Quem abrir uma sessão vê tudo o que ficou preparado (`/whatsapp:responder`).

## Regras

1. Só conversas individuais, a não ser que a pessoa peça grupos.
2. Contato sem nome resolvido: avise, não adivinhe.
3. Dados possivelmente desatualizados: avise, não trate como estado atual.
4. Triagem lê e resume. Quem decide e confirma é a pessoa.

## Por que

- **Scripts locais:** ler o banco direto custa quase nada, e o MCP gasta chamadas e contexto para o mesmo resultado.
- **Aviso de dados antigos:** uma lista apresentada como atual, mas incompleta, faz a pessoa acreditar que está em dia quando não está.
- **Aprofundar o histórico:** sem o histórico antigo, o resumo e o tom saem de uma amostra pequena e erram.
- **Loop só prepara:** automação sem a pessoa presente não pode falar em nome dela.
