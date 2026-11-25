# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [0.1.1]

### Corrigido
- Servidor MCP: as ferramentas de leitura (`list_chats`, `search_contacts`, `get_chat`, `get_direct_chat_by_contact`, `get_contact_chats`, `get_message_context`, `get_last_interaction`, `list_messages`) devolviam objetos do Python onde o contrato declara dicionário, lista ou texto, e falhavam em versões do pacote `mcp` que validam a saída. Agora devolvem JSON. Um teste novo chama cada ferramenta pelo protocolo MCP, como um agente faz.
- `WHATSAPP_STORE_DIR` agora vale também para o servidor e para a bridge (antes só os scripts das skills a liam).
- Mensagens de arquivo mostram o nome (`[document: contrato.pdf]`) nas ferramentas e nos scripts da triagem.
- Os scripts das skills acham o `data/` pela pasta de trabalho quando a skill foi copiada para a biblioteca de um agente.
- O diagnóstico reconhece o pacote `mcp` instalado no ambiente do `uv` (`server/.venv`) em vez de dizer que ele está ausente.

### Novo
- Bridge pronta nas releases (Windows, Linux e macOS, amd64 e arm64), com `SHA256SUMS`, gerada por um fluxo de release. O script `baixar_bridge.py` baixa o binário certo e confere a soma: Go e compilador C deixam de ser necessários para a maioria das pessoas.
- A bridge grava o QR de pareamento como imagem (`data/store/qr.png`), renovada sozinha e apagada ao parear, para quem instala por um chat.
- `container/instalar-vps.sh`: instala o plugin em um servidor com Podman com dois comandos (imagens, senha como segredo sem mostrá-la, Quadlets, QR; depois servidor MCP e rede do OpenBot, com pergunta e cópia).
- A skill `instalar-whatsapp` faz todas as perguntas em uma mensagem só, trata o agente que roda dentro de um container sem acesso ao servidor e documenta o `--extra audio` no comando do servidor.

## [0.1.0]

Primeira versão pública.

### Servidor MCP
- Treze ferramentas: buscar contatos, listar conversas, ler mensagens e contexto, baixar mídia, transcrever áudio (opcional, Whisper local) e enviar texto, arquivo ou áudio.
- **Modos de envio** pela variável `WHATSAPP_SEND_MODE`: `read-only` (padrão, sem ferramentas de envio), `two-step` (o agente guarda rascunhos e a pessoa confirma no terminal com `confirm.py`) e `hook` (envio direto, com o guarda do Claude Code).
- Envio em várias partes com uma única confirmação, apenas para o mesmo destinatário.
- Rascunhos com validade (30 minutos) e limite de 20 por vez.

### Bridge
- Escuta a API só em `127.0.0.1` por padrão; fora do loopback (`WHATSAPP_BRIDGE_ADDR`) só abre com senha.
- Senha opcional da API (`WHATSAPP_BRIDGE_TOKEN`, `Authorization: Bearer`), enviada pelo servidor e pelos scripts.
- Envio de documentos com o tipo correto e nome do arquivo.

### Containers
- Imagens da bridge e do servidor MCP (`container/`), arquivo Compose para o computador e Quadlets para o Podman, com a bridge numa rede que o agente não alcança.
- Servidor MCP também por HTTP (`WHATSAPP_MCP_TRANSPORT=streamable-http`), com lista de hosts permitidos obrigatória fora do loopback.

### Skills
- `instalar-whatsapp`, que instala e configura o plugin até funcionar (com um script de diagnóstico que só lê), e `usar-whatsapp-mcp`, `triagem-whatsapp`, `notas-por-contato`, `escrever-como-humano` e `mensagens-em-partes`, cada uma com guias e, quando precisa, scripts de consulta somente leitura.

### Comandos
- `/whatsapp:status`, `/whatsapp:pendentes`, `/whatsapp:responder`, `/whatsapp:resumo`, `/whatsapp:loop` e `/whatsapp:modo`.

### Segurança e privacidade
- Guarda de envio do Claude Code que falha fechado e reconhece confirmações em português, inglês e espanhol.
- Verificador de privacidade (`scripts/check-privacy.py`) com hook de pré-commit e CI: barra IP público, e-mail, telefone, ID de WhatsApp, CPF, CNPJ, token e caminho com nome de usuário.
- Notas por contato, rascunhos e bancos ficam em `data/`, fora do git.

### Documentação
- README em inglês (principal) e em português, guia de uso, solução de problemas, guia por agente (OpenCode, Codex, OpenClaw e OpenBot) e guia do OpenBot com containers.
- Imagens nos dois idiomas, com três fluxos novos (modos de envio, isolamento com containers e instalação por agente), geradas por `scripts/gerar-diagramas.py`.

### Créditos
- Baseado no `whatsapp-mcp` de Luke Harries (MIT). A bridge usa a `whatsmeow` (MPL-2.0).
