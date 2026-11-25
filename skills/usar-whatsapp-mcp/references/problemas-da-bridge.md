# Problemas comuns da bridge

Antes de investigar um erro de download, envio ou sincronização do zero, veja se é um destes casos.

## As ferramentas de envio não aparecem

Pode ser de propósito: no modo `read-only` (o padrão) o servidor nem registra `send_*`. Confira a variável `WHATSAPP_SEND_MODE` do servidor e a instrução que ele passa ao agente. Para permitir envio com confirmação da pessoa, use `two-step`.

## Nenhuma ferramenta do WhatsApp aparece

Os agentes leem a configuração dos servidores MCP quando iniciam. Se ela mudou com o agente aberto, reinicie o agente.

## Falha ao baixar mídia

1. Veja se a bridge está rodando e escutando na porta 8081 (`netstat` ou o gerenciador de processos).
2. Se estiver, chame a API para ver o erro real, porque o servidor MCP resume o erro:
   `curl -X POST http://localhost:8081/api/download -d '{"message_id":"...","chat_jid":"..."}'`
3. Erro 403 em mensagens antigas costuma ser mídia expirada ou histórico sincronizado sem o endereço completo do arquivo. Mídia expirada não tem como recuperar.

Use o `curl` só para consultar. **Não envie mensagens pelo `curl`:** o texto pode chegar com acentos corrompidos em alguns terminais, e o envio passaria por cima das confirmações do servidor.

## A mensagem não chega, com a bridge rodando

- A sincronização de histórico só busca mensagens **mais antigas** que um ponto de referência. Não existe forma de forçar a entrega de uma mensagem nova que o WhatsApp ainda não enviou: é uma limitação do protocolo.
- Se uma pessoa específica não aparece mas as outras sim, ela provavelmente está falando por outro identificador (`@lid` ou `@s.whatsapp.net`). Veja `identificacao-de-contatos.md` antes de suspeitar de defeito.

## A bridge ficou parada e só alguns chats estão atualizados

Depois de um tempo desligada, ao reconectar costumam chegar primeiro os grupos, e as conversas individuais ficam na última mensagem de antes da queda.

- O script `listar_pendentes.py` (skill `triagem-whatsapp`) avisa (`AVISO: ...`) quando a mensagem mais recente de qualquer conversa tem mais de 6 horas. Nesse caso, **não trate a lista como o estado atual**: avise a pessoa de que pode haver mensagens perdidas.
- Abrir o WhatsApp no celular ajuda o aparelho a sincronizar de novo.
- Só se nada resolver há desincronização de sessão, que exige parear o aparelho de novo (ler o QR outra vez). É o último recurso e nunca se faz sem perguntar.

## A bridge acabou de reiniciar

O backlog chega devagar, em ordem cronológica, e por alguns minutos o servidor e os scripts podem dizer que não há mensagens. Isso não é defeito. Rode `aguardar_backlog.py` (skill `triagem-whatsapp`) e só conclua "não há mensagem nova" depois que o banco estiver em dia. Para esperar, use um laço que confere o banco de tempos em tempos, não uma espera longa.

## Porta 8081 ocupada ou comportamento estranho

Confira se há duas instâncias da bridge rodando. Duas instâncias disputam a mesma sessão (aparece "stream replaced") e cada uma recebe um pedaço das mensagens. Encerre todas e inicie só uma.

## A bridge precisa rodar de dentro da pasta `bridge/`

Ela usa caminhos relativos (`../data/store`). Inicie sempre a partir da pasta `bridge/`; o hook de início do plugin já faz isso.

## Respostas enviadas aparecem como pendentes

A bridge atual grava no histórico local as mensagens que envia. Se algo já respondido continuar como pendente, confira se a bridge em execução é a compilada a partir deste plugin e reinicie-a.

## Acentos quebrados em scripts no Windows

Python com acento ou símbolo na saída pode falhar com `UnicodeEncodeError`. Os scripts do plugin já forçam UTF-8; em comandos avulsos, defina `PYTHONIOENCODING=utf-8`.
