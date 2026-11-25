# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e versionamento [SemVer](https://semver.org/lang/pt-BR/).

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
