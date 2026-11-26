# Guia de uso

Passo a passo para instalar, conectar e usar o WhatsApp com um agente de IA. Para a visão geral e os avisos de segurança, comece pelo [README](../README.pt-BR.md).

## 1. Antes de começar

Você precisa de:

| Item | Observação |
|---|---|
| Um agente com suporte a MCP | Claude Code, OpenBot, Codex, OpenCode, OpenClaw ou outro, veja [agentes.md](agentes.md) |
| [`uv`](https://docs.astral.sh/uv/) | roda o servidor MCP |
| [Go](https://go.dev/dl/) 1.25 ou superior e compilador C | só se for compilar a bridge (SQLite via CGO). No Windows, instale o MSYS2/MinGW e deixe o `gcc` no PATH. Com a bridge pronta da release, dispensa os dois |
| Um celular com WhatsApp | para ler o QR de conexão |
| `ffmpeg` (opcional) | só para transcrever áudios e enviar mensagens de voz |

Confira no terminal:

```
uv --version
go version
gcc --version
```

**Aviso.** A bridge usa um cliente não oficial do WhatsApp. O uso pode ir contra os termos do WhatsApp e o número pode ser bloqueado. Use com o seu próprio número.

## 2. Instalar

**Atalho:** peça a um agente para instalar por você, com o prompt da seção "Instalar com a ajuda de um agente" do [README](../README.pt-BR.md). Abaixo está o passo a passo manual.

```
git clone https://github.com/armandonettox/whatsapp-plugin.git
cd whatsapp-plugin
```

Ative o verificador de privacidade antes de qualquer commit seu (só é preciso se você pretende contribuir):

```
git config core.hooksPath .githooks
```

## 3. Obter a bridge

O caminho rápido é baixar a bridge pronta da release (confere o SHA-256 antes de gravar):

```
python skills/instalar-whatsapp/scripts/baixar_bridge.py
```

Se o script disser que não há bridge para o seu sistema, ou se faltar rede, compile:

```
cd bridge
go build -o main.exe .            # Windows
go build -o whatsapp-bridge .     # Linux e macOS
```

Se aparecer um erro falando de `gcc` ou `cgo`, o compilador C não está instalado ou não está no PATH. Veja [solução de problemas](solucao-de-problemas.md).

## 4. Conectar o WhatsApp (só na primeira vez)

Rode a bridge **em um terminal**, para ver o QR:

```
./main.exe                        # ou ./whatsapp-bridge
```

No celular: **WhatsApp, Aparelhos conectados, Conectar um aparelho**, e leia o QR do terminal. Quando aparecer "Connected to WhatsApp", a bridge começa a baixar o histórico. Pode deixá-la rodando ou fechar com Ctrl+C: nas próximas vezes o hook do Claude Code a liga sozinho, e nos outros agentes você a inicia à mão.

Sem terminal à mão (por exemplo, conversando com um agente pelo chat ou pelo celular)? Enquanto espera o pareamento, a bridge grava o mesmo QR como imagem em `data/store/qr.png` e a renova sozinha a cada poucos segundos. Abra ou peça ao agente para anexar esse arquivo; se expirar, abra de novo. O arquivo é apagado quando o pareamento termina. Trate-o como uma senha: quem lê o QR a tempo conecta a sua conta.

A sessão fica guardada em `data/store`. Se o aparelho for desconectado pelo celular, a bridge pede um novo QR.

## 5. Instalar no seu agente

**Claude Code**, direto da pasta (para testar):

```
claude --plugin-dir /caminho/para/whatsapp-plugin
```

Ou pelo catálogo do repositório:

```
/plugin marketplace add armandonettox/whatsapp-plugin
/plugin install whatsapp@whatsapp-plugin
```

**Outros agentes:** veja [agentes.md](agentes.md).

## 6. Conferir

Peça ao agente: "liste meus últimos 5 chats do WhatsApp". No Claude Code, use também o comando `/whatsapp:status`, que mostra o modo de envio, se o servidor responde e se os dados estão em dia.

## 7. Escolher o modo de envio

| Modo | O que o agente pode fazer | Como ligar |
|---|---|---|
| `read-only` (padrão) | só ler, buscar, baixar mídia e transcrever | não precisa fazer nada |
| `two-step` | guardar rascunhos; **você** envia no terminal | `WHATSAPP_SEND_MODE=two-step` |
| `hook` | enviar direto, com o guarda de confirmação | já vem ligado no plugin do Claude Code |

Para mudar o modo no Claude Code, defina `WHATSAPP_SEND_MODE` no ambiente em que o agente roda, ou ajuste o `.mcp.json` do plugin, e reinicie o agente. O comando `/whatsapp:modo` mostra o modo atual e explica como mudar.

### Confirmando rascunhos no `two-step`

Quando o agente guarda um rascunho, ele mostra o texto, o destinatário e um comando. Em **um terminal seu**, na pasta `server/`:

```
python confirm.py list                  # rascunhos esperando
python confirm.py show a1b2c3d4         # texto inteiro e destinatário
python confirm.py send a1b2c3d4         # pergunta e só envia se você digitar "enviar"
python confirm.py send a1b2c3d4 e5f6a7b8 c9d0e1f2   # várias partes, uma confirmação
python confirm.py discard a1b2c3d4      # descarta
python confirm.py discard --all
```

Os rascunhos expiram em 30 minutos (`WHATSAPP_PENDING_TTL_MINUTES`) e há no máximo 20 por vez. As partes de um mesmo envio precisam ser do mesmo destinatário.

## 8. Usar no dia a dia

### Comandos (Claude Code)

Nos outros agentes, os comandos não existem: peça a mesma coisa em linguagem natural (por exemplo, "quem me mandou mensagem e preciso responder?").

| Comando | O que faz |
|---|---|
| `/whatsapp:status` | diagnóstico rápido: modo, servidor, dados em dia |
| `/whatsapp:pendentes` | lista as conversas que esperam resposta, por urgência |
| `/whatsapp:responder <contato>` | prepara a resposta no seu jeito e envia (ou guarda) só depois da sua confirmação |
| `/whatsapp:resumo [contato]` | resume as mensagens novas, ou o histórico de um contato |
| `/whatsapp:loop [intervalo]` | liga a triagem periódica, que só prepara rascunhos |
| `/whatsapp:modo` | mostra o modo de envio e como mudar |
| `/whatsapp:atualizar` | atualiza o plugin para a última release, sem reinstalar |

### Pedidos em linguagem natural

Funciona pedir, por exemplo:

- "quem me mandou mensagem e preciso responder?"
- "resume a conversa com a Maria"
- "responde ao João dizendo que confirmo a reunião de quinta"
- "transcreve o áudio que o Pedro mandou"

O agente nunca envia sem a sua confirmação clara para aquele texto.

### As skills

| Skill | Para que serve |
|---|---|
| `instalar-whatsapp` | instalar e configurar o plugin até funcionar, com um diagnóstico que só lê |
| `usar-whatsapp-mcp` | como usar as ferramentas do MCP com segurança e economia |
| `triagem-whatsapp` | descobrir o que espera resposta e o que vale responder |
| `notas-por-contato` | lembrar o jeito de falar de cada contato e o que você prometeu |
| `escrever-como-humano` | escrever respostas que soam como você, sem cara de texto gerado |
| `mensagens-em-partes` | dividir uma resposta em várias mensagens curtas |

### O loop

`/whatsapp:loop 30m` liga uma rotina que, a cada 30 minutos, faz a triagem e salva sugestões em `data/rascunhos`. **O loop nunca envia nada**, porque não há ninguém ali para confirmar. Depois, `/whatsapp:responder <contato>` retoma a partir do rascunho. No Claude Code, o loop usa a skill `loop`; em outros agentes, use o agendador deles para rodar `/whatsapp:pendentes loop`.

### Notas por contato

Para um contato recorrente, o agente cria uma nota com o jeito de escrever, a relação e os compromissos abertos. As notas ficam em `data/notas`, no seu computador, e não vão para o git. Veja o formato em [`skills/notas-por-contato/references/formato-da-nota.md`](../skills/notas-por-contato/references/formato-da-nota.md).

### Transcrição de áudio

```
cd server
uv sync --extra audio
```

Precisa do `ffmpeg` no PATH. O idioma padrão é o português (`WHATSAPP_AUDIO_LANGUAGE`) e o modelo padrão é o `small` (`WHISPER_MODELO`). A primeira transcrição baixa o modelo.

## 9. Onde ficam seus dados

| Pasta | Conteúdo | Variável para mudar |
|---|---|---|
| `data/store` | bancos da bridge e a sessão do WhatsApp | `WHATSAPP_STORE_DIR` |
| `data/notas` | notas por contato | `WHATSAPP_NOTES_DIR` |
| `data/rascunhos` | rascunhos do loop | `WHATSAPP_DRAFTS_DIR` |
| `data/pending` | rascunhos do modo `two-step` | `WHATSAPP_PENDING_DIR` |

Toda a pasta `data/` fica fora do git. **Quem lê `data/store` controla a sua conta de WhatsApp**: não copie, não envie e não inclua em backup compartilhado. Para ver os caminhos em uso, rode `python skills/triagem-whatsapp/scripts/caminhos.py`.

## 10. Atualizar

Pelo agente: `/whatsapp:atualizar` no Claude Code, ou peça "atualize o plugin de WhatsApp" a qualquer agente (ele segue a skill `instalar-whatsapp`). Ou direto no terminal, a partir da pasta do plugin:

```
python skills/instalar-whatsapp/scripts/atualizar_plugin.py            # só verifica
python skills/instalar-whatsapp/scripts/atualizar_plugin.py --aplicar  # atualiza
```

O script avança o código para a última release sem misturar históricos, atualiza as dependências do servidor e mostra o que mudou. **Não toca** em `data/` (sessão, mensagens, notas), no `.env`, na senha nem no modo de envio. Se você alterou arquivos do plugin, ele recusa e diz quais (guarde-os com `git stash`). Se o código da bridge mudou, ele avisa: feche a bridge e rode de novo com `--bridge` para baixar a nova (ou compile). Em containers, no servidor: `bash container/instalar-vps.sh atualizar`.

Depois, reinicie o agente para ele carregar o servidor e as skills novos. No Claude Code instalado pelo catálogo (sem pasta git), use `/plugin marketplace update whatsapp-plugin` e `/plugin update whatsapp@whatsapp-plugin`; catálogo de terceiros não atualiza sozinho.

> A primeira atualização a partir da versão 0.1.1 ou anterior é manual, porque essas versões ainda não têm o script: `git pull` na pasta do plugin (ou `git fetch --tags && git merge --ff-only v0.1.2`), e daí em diante o comando de atualização funciona.

## 11. Remover

1. Feche a bridge.
2. No celular, em **Aparelhos conectados**, desconecte o aparelho.
3. Apague a pasta do plugin. Se quiser manter só as notas, copie antes a pasta `data/notas`.
4. Remova o plugin do agente (no Claude Code, pelo menu `/plugin`).

## 12. Variáveis de ambiente

A tabela completa está no [README](../README.pt-BR.md#uso). As principais: `WHATSAPP_SEND_MODE`, `WHATSAPP_API_BASE_URL`, `WHATSAPP_STORE_DIR`, `WHATSAPP_NOTES_DIR`, `WHATSAPP_DRAFTS_DIR`, `WHATSAPP_PENDING_DIR`, `WHATSAPP_PENDING_TTL_MINUTES`, `WHATSAPP_AUDIO_LANGUAGE` e `WHISPER_MODELO`.
