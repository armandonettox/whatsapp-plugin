# Usar com o OpenBot

O OpenBot roda agentes que têm terminal e executam ações sem pedir confirmação a cada passo. Isso muda o desenho de segurança, e este guia explica como ligar o WhatsApp ao OpenBot sem dar ao agente acesso direto à sua conta.

Leia antes: [agentes.md](agentes.md) (o que cada agente confirma) e o [README](../README.pt-BR.md#modos-de-envio), seção "Modos de envio".

## Por que o desenho é diferente do Claude Code

No Claude Code, um hook confere cada envio. No OpenBot esse hook não existe. A proteção fica em duas camadas:

1. **O servidor MCP decide o que o agente pode fazer.** Em `read-only` (padrão) as ferramentas de envio nem aparecem. Em `two-step` o agente só guarda rascunhos e quem envia é você.
2. **A bridge fica fora do alcance do agente.** A API da bridge envia mensagens e só se protege por uma senha. Se o agente conseguir chamar a API, ele passa por cima do servidor. Por isso a bridge roda em um container próprio, numa rede que o agente não alcança, e a senha fica só nos containers dela e do servidor.

```
 agente (container do OpenBot)
        |
        |  rede "whatsapp-agente"  (só o agente e o servidor MCP)
        v
 servidor MCP  (container whatsapp-mcp, modo read-only ou two-step)
        |
        |  rede "whatsapp-back"    (só o servidor MCP e a bridge)
        v
 bridge        (container whatsapp-bridge, API com senha, sem porta publicada)
        |
        v
    WhatsApp
```

O agente alcança apenas o servidor MCP, em `http://whatsapp-mcp:8765/mcp`. Ele não enxerga a bridge, a senha, o banco nem a sessão do WhatsApp.

## Antes de começar

- **Seus dados ficam onde a bridge roda.** Quem controla o volume `whatsapp-data` controla a sua conta de WhatsApp. Só faça isso em um servidor seu, com disco e acesso protegidos, e com o seu próprio número.
- **O que o agente lê vai para o modelo que ele usa.** Não ligue a conversas que não possam passar por ele.
- O WhatsApp pode bloquear números que usam clientes não oficiais (veja o aviso no README).

## O que você precisa

- Podman (ou Docker) no computador que vai rodar a bridge.
- O OpenBot no mesmo computador, ou em um computador que alcance a rede `whatsapp-agente`.
- A pasta do plugin.

## Opção A: na VPS, com Podman e Quadlet

Os arquivos estão em `container/quadlet/`. Tudo roda sem root, no usuário que já roda o OpenBot.

**O caminho rápido: dois comandos.** No terminal do servidor, com o plugin clonado:

```
bash container/instalar-vps.sh            # constrói, cria a senha, instala os Quadlets e mostra o QR
bash container/instalar-vps.sh servidor   # sobe o servidor MCP e liga o OpenBot à rede dele
```

O primeiro comando constrói as imagens, cria a senha como segredo do Podman (sem mostrá-la), instala os arquivos e inicia a bridge, mostrando o QR: leia no celular e aperte Ctrl+C quando conectar. O segundo sobe o servidor e, **só depois de perguntar**, acrescenta `Network=whatsapp-agente.network` ao arquivo do OpenBot (com cópia em `.bak`) e o reinicia. Opções: `--audio` (transcrição de áudio), `--sem-openbot`, `--openbot-arquivo <caminho>` e `--sim` (não pergunta). `status` mostra o que está rodando. Os passos abaixo são o mesmo processo feito à mão.

**1. Construa as imagens**, a partir da pasta do plugin:

```
podman build -f container/bridge.Containerfile -t localhost/whatsapp-bridge:0.1.1 .
podman build -f container/mcp.Containerfile    -t localhost/whatsapp-mcp:0.1.1 .
```

Para transcrever áudios, acrescente `--build-arg INSTALL_AUDIO=1` na segunda (a imagem fica bem maior).

**2. Crie a senha da bridge como segredo do Podman** (nunca em arquivo no git):

```
python3 -c "import secrets; print(secrets.token_urlsafe(32))" | podman secret create whatsapp-bridge-token -
```

**3. Instale os arquivos Quadlet:**

```
mkdir -p ~/.config/containers/systemd
cp container/quadlet/whatsapp-* ~/.config/containers/systemd/
systemctl --user daemon-reload
```

**4. Conecte o WhatsApp (só na primeira vez).** Suba a bridge e leia o QR nos registros:

```
systemctl --user start whatsapp-bridge.service
podman logs -f whatsapp-bridge
```

No celular: **WhatsApp, Aparelhos conectados, Conectar um aparelho**, e leia o QR. Quando aparecer "Connected to WhatsApp", a sessão fica guardada no volume.

**5. Suba o servidor MCP:**

```
systemctl --user start whatsapp-mcp.service
```

**6. Ligue o OpenBot à rede do agente.** Faça uma cópia do arquivo do OpenBot antes de mexer (`cp ~/.config/containers/systemd/openbot.container ~/openbot.container.bak`). No `[Container]` dele, acrescente:

```
Network=whatsapp-agente.network
```

e recarregue e reinicie: `systemctl --user daemon-reload && systemctl --user restart openbot.service`. O container passa a usar essa rede (uma rede com saída para a internet), em vez da rede padrão. Confira que o OpenBot continua conectado ao servidor de conta depois do reinício.

**7. Cadastre o servidor MCP no OpenBot** como servidor por **URL**: `http://whatsapp-mcp:8765/mcp`. O cadastro vale para o computador inteiro: todos os agentes desse host recebem as ferramentas.

**8. Teste:** peça a um agente "liste meus últimos 5 chats do WhatsApp".

## Opção B: no notebook

**B1. Com containers (recomendado).** O arquivo `container/compose.yaml` sobe a bridge e o servidor. O servidor fica em `http://127.0.0.1:8765/mcp`, só no seu computador. Siga os passos do comentário no topo do arquivo: copie `container/.env.example` para `container/.env`, preencha a senha, construa, leia o QR com `run --rm -it bridge` e depois suba com `up -d`. No OpenBot, cadastre o servidor por URL em `http://127.0.0.1:8765/mcp`.

**B2. Sem containers.** O servidor roda direto no computador, por stdio (`uv --directory /caminho/para/whatsapp-plugin/server run main.py`), e a bridge roda como processo comum. É mais simples, mas um agente com terminal no mesmo computador consegue alcançar a bridge. Nesse caso:

- mantenha o `read-only`, e use o `two-step` só se aceitar o risco descrito no README;
- defina `WHATSAPP_BRIDGE_TOKEN` (a bridge e o servidor leem a mesma variável) para a API não ficar aberta;
- lembre que um agente com terminal que rode como o mesmo usuário pode ler essa variável.

## Confirmar rascunhos no `two-step`

Com os containers, o comando que o servidor mostra ao agente é `podman exec -it whatsapp-mcp python confirm.py send <id>` (com Docker, `docker exec -it ...`). Rode no terminal **seu**:

```
podman exec -it whatsapp-mcp python confirm.py list
podman exec -it whatsapp-mcp python confirm.py show <id>
podman exec -it whatsapp-mcp python confirm.py send <id>
```

O agente do OpenBot não tem o comando `podman` dentro do container dele, então não alcança esse caminho. Mesmo assim, mantenha o `read-only` quando não precisar de envio.

## Skills, comandos e rotinas no OpenBot

- **Skills.** Adicione as pastas de `skills/` em **Settings, Skills, Local skills**. O texto delas funciona sem os scripts: quando um script não existe ou não consegue ler os dados, elas mandam usar as ferramentas do MCP.
- **Os scripts de consulta não funcionam nesse desenho.** Eles leem o banco da bridge, que não está dentro do container do agente. Use `list_chats`, `list_messages` e as outras ferramentas do MCP. Os scripts de notas rodam com `python3` e `WHATSAPP_NOTES_DIR` apontando para uma pasta do agente, mas sem os nomes da agenda.
- **Comandos `/whatsapp:*`** são do Claude Code. No OpenBot, peça em linguagem natural.
- **Loop.** No OpenBot, a triagem periódica seria uma rotina do agente. Mantenha a regra: a rotina só prepara texto, nunca envia. Eu não confirmei se uma rotina agendada dispara com o app fechado.

## Limitações deste desenho

| Limitação | Motivo |
|---|---|
| `download_media` devolve um caminho que o agente não consegue abrir | o arquivo fica dentro do container do servidor, que o agente não monta |
| `transcribe_audio` funciona, mas só em imagem construída com `INSTALL_AUDIO=1` | o Whisper e o `ffmpeg` ficam na imagem |
| `send_file` e `send_audio_message` não alcançam arquivos do agente | o servidor só vê o próprio container; um volume compartilhado de saída seria necessário e não faz parte deste desenho |
| Modo `hook` não deve ser usado | depende do guarda do Claude Code |

## O que foi testado e o que não foi

**Testado:** a bridge exige a senha e recusa abrir fora do computador sem ela; o servidor envia a senha, fala HTTP e recusa nomes de host fora da lista; os arquivos de container têm as redes, as portas e os segredos corretos (testes automáticos); o `docker compose config` aceita o compose; os Quadlets passaram na simulação do gerador do Podman 4.9.

**Não testado:**

- construir as imagens (`podman build`) e subir os containers;
- o QR aparecendo legível nos registros do container;
- o OpenBot funcionando depois de trocar a rede dele;
- o cadastro do servidor por URL no OpenBot (a tela de cadastro não está documentada, então confirme que ela aceita uma URL);
- uma conversa real de ponta a ponta.

Se algum desses passos falhar, abra uma issue com o passo, a mensagem de erro e a saída de `podman logs`, sem trechos de conversas.

## Atualizar, copiar e remover

- **Atualizar:** reconstrua as imagens com a nova versão e reinicie as unidades (`systemctl --user restart whatsapp-bridge.service whatsapp-mcp.service`).
- **Cópia de segurança:** o volume tem a sessão do WhatsApp. Guarde-o como guardaria uma senha, e não o envie para nuvem nem para o git.
- **Remover:** `systemctl --user stop whatsapp-mcp.service whatsapp-bridge.service`, apague os arquivos Quadlet, desconecte o aparelho no celular (**Aparelhos conectados**) e só então remova o volume (`podman volume rm whatsapp-data`) e o segredo (`podman secret rm whatsapp-bridge-token`). Desfaça também a linha `Network=` do OpenBot.
