# Solução de problemas

Procure pelo sintoma. Para um diagnóstico rápido, rode `python skills/instalar-whatsapp/scripts/verificar_instalacao.py` (funciona em qualquer agente, só lê) ou, no Claude Code, use `/whatsapp:status`.

## Instalação

### `go build` falha falando de `gcc` ou `cgo`

A bridge usa SQLite via CGO e precisa de um compilador C. No Windows, instale o MSYS2, abra o terminal "MSYS2 MinGW 64-bit", rode `pacman -S mingw-w64-x86_64-gcc` e coloque a pasta `mingw64/bin` no PATH. Confirme com `gcc --version` e compile de novo.

### `go build` diz que a versão do Go é antiga

O módulo pede Go 1.25 ou superior. Atualize o Go e rode `go version` para conferir.

### O comando `python3` não funciona no Windows

No Windows, `python3` pode ser só um atalho da Microsoft Store. Use `python` ou `py`. Os scripts e hooks do plugin já testam os três nomes e usam o primeiro que funciona.

### Acentos quebrados na saída de um script (`UnicodeEncodeError`)

Defina `PYTHONIOENCODING=utf-8` no terminal. Os scripts do plugin já forçam UTF-8, mas comandos avulsos podem falhar.

## Conexão

### O QR não aparece

Rode a bridge em um terminal comum, não em segundo plano, e espere alguns segundos. Se a sessão já estava conectada, o QR não aparece: isso é normal.

### A bridge pede o QR de novo

O aparelho foi desconectado (pelo celular, ou por muito tempo sem uso). Rode a bridge em um terminal e leia o QR de novo. O histórico já baixado continua em `data/store`.

### Duas bridges rodando

Duas instâncias disputam a mesma sessão (aparece "stream replaced") e cada uma recebe só parte das mensagens. Feche todas e inicie uma só. A porta usada é a 8081.

### A porta 8081 está ocupada

Outro programa usa a porta. Feche a outra bridge ou o programa que a ocupa. A bridge só escuta em `127.0.0.1`: se outra máquina precisa alcançá-la, **não mude isso**, porque a API não tem senha. Use o modo de envio do servidor.

## O agente

### As ferramentas de envio não aparecem

É o comportamento padrão: o modo `read-only` não registra ferramentas de envio. Use `/whatsapp:modo` para ver o modo e `WHATSAPP_SEND_MODE=two-step` para enviar com confirmação.

### Nenhuma ferramenta do WhatsApp aparece

Os agentes leem a configuração dos servidores MCP quando iniciam. Reinicie o agente. Confira também se o `uv` está no PATH do agente e se o caminho da pasta `server/` na configuração está certo.

### O agente diz que o servidor não responde

A bridge está parada. Inicie-a em um terminal (passo 4 do [guia de uso](guia-de-uso.md)). No Claude Code, o hook de início da sessão a liga sozinho; se isso falhar, confira se existe o binário compilado em `bridge/`.

### Os envios foram bloqueados

No modo `hook` (Claude Code), o guarda só libera uma confirmação curta e direta ("sim", "manda", "pode enviar"). Pedidos de mudança, perguntas ("pode mandar?") e frases longas bloqueiam de propósito. Quando bloquear, o agente mostra o texto de novo e pede a confirmação. Se o guarda não conseguir ler o histórico da conversa ou não achar o Python, ele também bloqueia.

### `confirm.py` diz que só roda em terminal interativo

É de propósito: o comando foi feito para ser digitado por uma pessoa. Abra um terminal seu (não o do agente) e rode o comando de lá.

### O rascunho expirou

Os rascunhos do modo `two-step` valem 30 minutos. Peça ao agente para guardar de novo. Para mudar o prazo, use `WHATSAPP_PENDING_TTL_MINUTES`.

## Mensagens e mídia

### Mensagens recentes não aparecem

Se a bridge ficou parada, ao reconectar chegam primeiro os grupos, e as conversas individuais podem ficar na última mensagem de antes da queda. O `listar_pendentes.py` avisa quando a mensagem mais recente de qualquer conversa tem mais de 6 horas. Abrir o WhatsApp no celular ajuda o aparelho a sincronizar. Se acabou de reiniciar a bridge, espere o backlog terminar de chegar (`aguardar_backlog.py`).

### Um contato "não tem conversa", mas tem

O mesmo contato pode ter dois identificadores (`@s.whatsapp.net` e `@lid`) e a conversa estar só em um deles. Os scripts da skill `triagem-whatsapp` juntam os dois. Veja [`identificacao-de-contatos.md`](../skills/usar-whatsapp-mcp/references/identificacao-de-contatos.md).

### O download de mídia falha

Confira se a bridge está rodando. Mídia antiga pode ter expirado, e nesse caso não há como recuperar. Veja [`problemas-da-bridge.md`](../skills/usar-whatsapp-mcp/references/problemas-da-bridge.md).

### A transcrição de áudio não funciona

Instale o extra de áudio (`cd server && uv sync --extra audio`) e o `ffmpeg`, e confirme com `ffmpeg -version`. A primeira transcrição baixa o modelo e pode demorar.

### Mensagens enviadas aparecem como pendentes

Confira se a bridge em uso foi compilada a partir deste plugin e reinicie-a. A versão atual grava no histórico local o que envia.

## Privacidade e git

### O commit foi barrado pelo verificador de privacidade

O verificador achou um IP público, e-mail, telefone, identificador de WhatsApp, CPF, CNPJ, token ou um caminho com nome de usuário em arquivos do commit. Ele mostra o arquivo, a linha e o tipo, com o valor mascarado. Remova o dado. Se for um exemplo fictício, coloque o valor exato em `.privacy-allow` ou escreva `privacy:ignore` no fim da linha.

### O hook de pré-commit não roda

Ative uma vez por clone: `git config core.hooksPath .githooks`. Em Linux e macOS, o arquivo `.githooks/pre-commit` precisa de permissão de execução (`chmod +x`).

## Ainda sem resposta?

Abra uma issue no repositório com: o sistema operacional, o agente e a versão, o modo de envio, o resultado do diagnóstico (`verificar_instalacao.py` ou `/whatsapp:status`) e a mensagem de erro. **Não cole conteúdo de conversas, números de telefone nem a pasta `data/`.**
