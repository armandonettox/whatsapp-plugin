---
name: instalar-whatsapp
description: Instala e configura o plugin de WhatsApp do começo ao fim até funcionar - detecta o sistema e o agente, escolhe o caminho certo (Claude Code, outro agente por stdio, ou containers para OpenBot e agentes com terminal), instala o que falta com permissão, baixa a bridge pronta (ou compila), guia o pareamento por QR, registra o servidor MCP no agente, deixa o envio desligado por padrão e prova que funciona. Também atualiza o plugin para a última versão sem reinstalar. Use quando pedirem para instalar, configurar, consertar a instalação, atualizar ou conectar o WhatsApp a um agente.
---

# Instalar o plugin de WhatsApp

Esta skill leva da pasta vazia ao servidor funcionando. Siga os passos na ordem e **pare nos pontos marcados com PARE**: são coisas que só a pessoa pode fazer ou decidir.

O plugin dá ao agente acesso às conversas de WhatsApp da pessoa. Por isso, durante toda a instalação: **o envio de mensagens fica desligado** (`read-only`), a senha da bridge nunca é mostrada, e nenhuma mensagem é enviada nem como teste.

## Regras que valem o tempo todo

1. **Pergunte antes de instalar qualquer programa** (uv, Go, compilador, Podman). Diga o nome, para que serve e o comando. Só rode depois do "sim".
2. **Nunca imprima, repita nem cole no chat a senha da bridge.** Gere com Python escrevendo direto no arquivo ou segredo de destino (o comando não pode mostrar o valor) e confirme só que foi definida. Lembre que um agente que conhece a senha consegue usá-la: ela só protege a bridge de agentes que **não** a leem, e é por isso que ela vale no caminho C.
3. **Nunca envie mensagem de teste.** O teste é ler (`list_chats` com `limit` 1).
4. **Não altere nada fora da pasta do plugin e da configuração do agente**, a não ser que a pessoa peça. **Antes de editar a configuração do agente** (onde ficam os servidores MCP e as skills), diga o que vai mudar e peça o "sim". Em um servidor com outros serviços rodando, não reinicie nem edite o que já existe sem confirmação.
5. **Nunca use `git add .`, nunca envie a pasta `data/`** nem o arquivo `container/.env` para um repositório.
6. **Não invente configuração de agente.** Para registrar o servidor MCP e as skills em um agente, use só o que está em `docs/agentes.md`. O que lá estiver como "não confirmado", diga à pessoa e peça para conferir na documentação do agente.
7. **Se um passo falhar duas vezes do mesmo jeito, pare**, mostre o erro (sem dados pessoais) e pergunte. Não repita às cegas.

## Passo 0: onde estou e o que tenho

1. Descubra o **sistema** (Windows, Linux ou macOS) e o **agente** que está lendo esta skill (Claude Code, OpenBot, Codex, OpenCode, OpenClaw ou outro).
2. Ache a **pasta do plugin**. Se esta skill foi lida de dentro dela, é a pasta que tem `bridge/`, `server/` e `skills/`. Se não houver pasta, **PARE e pergunte** onde ela deve ficar e clone o repositório (`git clone https://github.com/armandonettox/whatsapp-plugin.git`). Se o clone falhar com erro de acesso, o repositório ainda é privado: peça à pessoa o acesso ou uma cópia da pasta.
3. Rode o diagnóstico, que só lê e não altera nada. A partir da pasta do plugin (use `python`, `python3` ou `py`, o que funcionar):

   ```
   python skills/instalar-whatsapp/scripts/verificar_instalacao.py
   ```

   Ele lista o que está pronto (`OK`), o que falta (`FALTA`), avisos e a primeira coisa a fazer. **Volte a rodá-lo depois de cada passo**: ele é a prova de que o passo funcionou.
4. Descubra **onde o agente roda**: no computador da pessoa, ou dentro de um container ou servidor que não alcança o computador dela (sinais: `podman`, `systemctl` e `docker` não existem, o diretório de trabalho fica em `/data/...`, não há `sudo`). Isso decide as opções do passo 1.

## Passo 1: escolher o caminho e as opções, de uma vez

Faça **uma mensagem só** com todas as escolhas, cada uma com a sua recomendação e o motivo em uma linha, para a pessoa responder tudo de uma vez (por exemplo, "C, sem áudio, instala as skills"). Não vá perguntando uma a uma.

| Se o agente é... | Caminho | Por quê |
|---|---|---|
| **Claude Code** | **A**: plugin | O plugin traz o servidor, as skills, os comandos e o guarda de envio prontos |
| **OpenBot** | **C**: containers | Os agentes têm terminal e rodam sem confirmação; a bridge precisa ficar fora do alcance deles |
| **Codex, OpenCode, OpenClaw** ou outro com MCP | **B**: servidor por stdio, somente leitura | Mais simples; sem o guarda do Claude Code, o servidor fica em `read-only` |
| Qualquer agente com terminal, quando a pessoa quer a proteção máxima | **C**: containers | A bridge e a senha ficam onde o agente não chega |

As escolhas a perguntar juntas:

1. **Caminho** (a tabela acima dá a recomendação).
2. **Transcrição de áudio** (precisa de `ffmpeg` e baixa um modelo de uns 500 MB): recomendado **não**, a menos que a pessoa receba muito áudio.
3. **Instalar as skills no agente** (as seis de `skills/`): recomendado **sim**, quando o agente tem o conceito de skill.

**Se o agente tem terminal e você ia escolher o caminho B, PARE e pergunte antes**, em duas linhas: o B é mais simples e o agente instala tudo sozinho, mas um agente com terminal consegue alcançar a bridge e o envio só fica protegido pelo servidor em `read-only`; o C isola a bridge, mas exige containers. Deixe a pessoa escolher. Nos demais casos, diga qual caminho escolheu e por quê, e **PARE** se ela quiser outro. Detalhes do caminho C, inclusive na VPS, estão em `docs/openbot.md`.

**Se o agente roda dentro de um container sem acesso ao servidor** (caso comum do OpenBot em uma VPS), o caminho C não pode ser feito por ele: quem instala é a pessoa, no terminal do servidor, com **um comando só** (passo 3C). Diga isso na mesma mensagem, com a comparação: no B você faz tudo agora, sem isolamento; no C ela roda um comando e o agente ganha o isolamento.

## Passo 2: pré-requisitos

Pelo diagnóstico, instale só o que faltar (com permissão, regra 1).

**Caminhos A e B** precisam de **Python 3.11 ou superior** e do **uv**. O **ffmpeg** é só para áudio, se a pessoa escolheu áudio. **Go e compilador C não são necessários**: a bridge vem pronta (passo 4). Eles só entram se não houver bridge pronta para o sistema.

| Sistema | uv |
|---|---|
| Windows | `winget install astral-sh.uv` |
| macOS | `brew install uv` |
| Linux (Debian, Ubuntu) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

Sem permissão de administrador (`sudo`), o `uv` e o ffmpeg estático instalam na pasta do usuário. Depois de instalar algo, abra um terminal novo (o PATH muda) e rode o diagnóstico de novo.

**Caminho C** precisa de **Podman** ou **Docker**. Na VPS do OpenBot costuma haver Podman.

## Passo 3A: caminho A (Claude Code)

1. Obtenha a bridge (passo 4) e conecte o WhatsApp (passo 5).
2. Instale o plugin. Para testar sem instalar, `claude --plugin-dir <pasta do plugin>`. Para instalar de verdade, `/plugin marketplace add armandonettox/whatsapp-plugin` e `/plugin install whatsapp@whatsapp-plugin` (ou, para uma pasta local, `/plugin marketplace add <pasta>`).
3. O modo de envio no Claude Code é `hook`: cada envio passa pelo guarda de confirmação. Nada mais a configurar.
4. Reinicie o Claude Code e vá para o passo 6.

## Passo 3B: caminho B (outro agente, por stdio)

1. Obtenha a bridge (passo 4) e conecte o WhatsApp (passo 5).
2. Registre o servidor MCP no agente, **usando `docs/agentes.md`** (peça o "sim" antes de editar a configuração, regra 4). Para um agente que não está lá (Grok, DeepSeek e outros), a seção "Outros agentes" não traz receita: **diga isso à pessoa e peça que ela confira, na documentação do agente, onde cadastrar um servidor MCP local**, em vez de inventar. O comando do servidor é este (troque o caminho pela pasta do plugin):

   ```
   uv --directory <pasta do plugin>/server run main.py
   ```

   **Se a pessoa escolheu áudio**, instale uma vez com `uv --directory <pasta do plugin>/server sync --extra audio` e use `run --extra audio main.py` no comando acima. Sem o `--extra audio` no comando, o `uv run` volta o ambiente ao padrão e **desinstala o Whisper** na próxima partida.

3. **O mais simples é não definir `WHATSAPP_SEND_MODE`**: o padrão já é `read-only`, e assim não depende de o agente aceitar variáveis de ambiente na configuração. **Não use `hook`** fora do Claude Code.
4. **Senha da bridge: não use neste caminho.** Neste caminho a bridge roda no mesmo computador e no mesmo usuário do agente, então um agente com terminal lê a senha da configuração e a usa. A única proteção real é o servidor em `read-only`. Se a pessoa quer que o agente nunca alcance a bridge, o caminho certo é o **C** (containers). Diga isso a ela se o agente tiver terminal.
5. Instale as skills, se o agente tiver o conceito: copie as pastas de `skills/` (cada uma funciona sozinha). Para o OpenClaw, `openclaw skills install <pasta da skill> --as <nome>`; para o OpenBot, Settings, Skills, Local skills; para os outros, **não invente o caminho**: consulte `docs/agentes.md` ou a documentação do agente.
6. Reinicie o agente (ele só lê a lista de servidores MCP ao iniciar) e vá para o passo 6.

## Passo 3C: caminho C (containers)

Leia `docs/openbot.md` antes de começar. Resumo:

1. **No computador** (Docker ou Podman Compose): `container/compose.yaml`.
   - Gere a senha e grave direto em `container/.env`, sem mostrar:

     ```
     python -c "import secrets; print('WHATSAPP_BRIDGE_TOKEN=' + secrets.token_urlsafe(32))" > container/.env
     ```

     Depois acrescente a linha `WHATSAPP_SEND_MODE=read-only` e, em Linux e macOS, `chmod 600 container/.env`. Confirme que o arquivo não é versionado (`git check-ignore container/.env`).
   - Construa: `docker compose -f container/compose.yaml --env-file container/.env build`.
   - Conecte o WhatsApp: `docker compose -f container/compose.yaml --env-file container/.env run --rm -it bridge`. **PARE: é o passo 5**, a pessoa lê o QR. Feche com Ctrl+C quando conectar.
   - Suba: `docker compose -f container/compose.yaml --env-file container/.env up -d`.
   - O servidor fica em `http://127.0.0.1:8765/mcp`. Registre no agente por URL (consulte `docs/agentes.md`).
2. **Na VPS com Podman e Quadlet:** a pessoa roda **um comando** no terminal do servidor, no usuário que roda o OpenBot (se você tem acesso a esse terminal, rode por ela depois do "sim"; se não tem, entregue estes comandos):

   ```
   git clone https://github.com/armandonettox/whatsapp-plugin.git ~/whatsapp-plugin
   bash ~/whatsapp-plugin/container/instalar-vps.sh
   ```

   O script constrói as imagens, cria a senha como segredo do Podman (sem mostrar), instala os Quadlets e inicia a bridge, mostrando o QR. A pessoa lê o QR no celular e aperta Ctrl+C. Depois:

   ```
   bash ~/whatsapp-plugin/container/instalar-vps.sh servidor
   ```

   sobe o servidor MCP e, **só depois de perguntar e fazer cópia**, liga o OpenBot à rede do servidor (essa é a única parte que mexe em um serviço que já roda; ele reinicia por alguns segundos). Para transcrever áudio, acrescente `--audio` no primeiro comando. O passo final é cadastrar `http://whatsapp-mcp:8765/mcp` no OpenBot por URL (consulte `docs/agentes.md`). Os detalhes passo a passo, se a pessoa preferir fazer à mão, estão em `docs/openbot.md`.

No caminho C o agente **não** alcança a bridge, o banco nem a senha. É esse o objetivo.

## Passo 4: obter a bridge (caminhos A e B)

**Primeiro tente a bridge pronta**, que dispensa Go e compilador (a release traz Windows, Linux e macOS, em amd64 e arm64):

```
python skills/instalar-whatsapp/scripts/baixar_bridge.py
```

O script confere o SHA-256 publicado antes de gravar o arquivo e usa os mesmos nomes que o `go build` (`bridge/main.exe` no Windows, `bridge/whatsapp-bridge` nos outros). Se disser `ja existe`, use `--forcar` só se a pessoa quiser trocar.

- Saída `sem bridge pronta para este sistema` ou erro de rede: compile (abaixo).
- Erro de verificação do SHA-256: **pare**, não use o arquivo, e avise a pessoa.

**Compilar** (só se não houver bridge pronta). Precisa de **Go 1.25 ou superior** e de um **compilador C** (a bridge usa SQLite via CGO). Pergunte antes de instalar (regra 1):

| Sistema | Go | Compilador C |
|---|---|---|
| Windows | `winget install GoLang.Go` | MSYS2 (`winget install MSYS2.MSYS2`), depois no terminal MSYS2 MinGW 64-bit `pacman -S mingw-w64-x86_64-gcc` e a pasta `mingw64/bin` no PATH |
| macOS | `brew install go` | `xcode-select --install` |
| Linux (Debian, Ubuntu) | pacote `golang` se for 1.25 ou superior, senão o instalador de go.dev/dl | `sudo apt install build-essential` |

Sem `sudo` em Linux, o Go instala em uma pasta do usuário e o `zig cc` serve de compilador C (basta um arquivo `cc` no PATH com `exec zig cc "$@"`). Depois, **só o comando do seu sistema**. No Windows:

```
cd bridge
go build -o main.exe .
```

No Linux e no macOS:

```
cd bridge
go build -o whatsapp-bridge .
```

- Erro falando de `gcc` ou `cgo`: falta o compilador C.
- Erro de versão do Go: atualize para 1.25 ou superior.

**Senha da bridge:** nos caminhos A e B ela não é usada (veja os avisos acima). Ela existe para o caminho C.

## Passo 5: conectar o WhatsApp (só a pessoa faz)

Só a pessoa consegue ler o QR no celular. **PARE** e conduza por uma destas duas formas.

**Se a pessoa tem um terminal** (no Claude Code, ela pode digitar `!` antes do comando para rodar na própria sessão), peça que ela rode:

```
cd <pasta do plugin>/bridge
./main.exe          # Windows: .\main.exe   |   outros: ./whatsapp-bridge
```

**Se a pessoa só conversa com você** (chat de agente, celular), inicie a bridge em segundo plano com a saída em `data/bridge.log` (no Linux e no macOS, `nohup ./whatsapp-bridge > ../data/bridge.log 2>&1 &`) e **anexe a imagem `data/store/qr.png`** na conversa. A bridge grava essa imagem e a renova sozinha a cada poucos segundos; se a pessoa disser que o QR expirou, espere dois segundos e anexe o arquivo de novo, sem reiniciar nada. O QR é uma chave de acesso à conta: mostre só a ela e não guarde a imagem (a bridge apaga o arquivo quando o pareamento termina).

A pessoa lê em **WhatsApp, Aparelhos conectados, Conectar um aparelho**. Quando aparecer "Connected to WhatsApp" (ou o diagnóstico mostrar "WhatsApp pareado"), a sessão fica guardada em `data/store`. **Avise já:** só o Claude Code liga a bridge sozinho (pelo hook). Em qualquer outro agente, a bridge precisa ser iniciada à mão toda vez que o computador ou o container reiniciar, e sem ela o servidor não responde.

- O QR não aparece: a sessão já pode estar pareada (rode o diagnóstico) ou o terminal não suporta a imagem (use o `qr.png`).
- **Porta 8081 ocupada por outro processo** (o diagnóstico mostra o aviso): pode ser outra bridge da pessoa. **Não feche o processo por conta própria**: pergunte de quem é. Duas bridges disputam a mesma sessão e a mesma porta, então a pessoa precisa decidir qual fica.

## Passo 6: provar que funciona

Rode o diagnóstico e, depois do reinício do agente:

1. **O servidor aparece?** As ferramentas do WhatsApp devem estar na lista do agente. No modo `read-only` são 10 e **nenhuma** começa com `send_`. Se aparecer `send_message`, o modo não é o esperado: confira `WHATSAPP_SEND_MODE`.
2. **Lê uma conversa?** Chame `list_chats` com `limit` 1. Mostre à pessoa **só que funcionou**, sem repetir nomes nem mensagens, a não ser que ela peça.
3. **A bridge está protegida?** O diagnóstico não pode acusar "Bridge exposta na rede".
4. **O modo está certo?** `Modo de envio: read-only` (ou `hook` só no Claude Code).

## Passo 7: decidir o envio (a pessoa decide)

Explique em poucas linhas e **PARE** para a pessoa escolher:

- `read-only` (padrão): o agente só lê. É o que ficou instalado.
- `two-step`: o agente guarda rascunhos e a pessoa envia no terminal dela com `confirm.py`. Mude com `WHATSAPP_SEND_MODE=two-step` e reinicie o agente. Avise do limite: um agente com terminal poderia tentar rodar o `confirm.py` sozinho, então para agentes com terminal o caminho C é o mais seguro.
- `hook`: só no Claude Code.

Não mude o modo sem a resposta dela.

## Passo 8: entregar

Termine com um resumo curto, sem dados pessoais:

- o caminho usado e onde ficou cada coisa (pasta do plugin, pasta `data/`);
- o modo de envio e como mudar;
- como iniciar a bridge depois de reiniciar o computador;
- o que ela pode pedir agora ("quem me mandou mensagem e preciso responder?") e, no Claude Code, os comandos `/whatsapp:status` e `/whatsapp:pendentes`;
- como desinstalar (`docs/guia-de-uso.md`, seção "Remover");
- o que ficou pendente ou não confirmado.

## Atualizar (sem reinstalar)

Quando a pessoa pedir para **atualizar** o plugin, não refaça a instalação. A partir da pasta do plugin:

1. **Verifique, sem alterar nada:** `python skills/instalar-whatsapp/scripts/atualizar_plugin.py`. Ele mostra a versão instalada, a última release e as notas. Se já está na última, diga isso e termine.
2. **Se há versão nova**, mostre em poucas linhas o que muda e **pergunte se pode atualizar**. Só então: `python skills/instalar-whatsapp/scripts/atualizar_plugin.py --aplicar`. O script avança o código para a release (`merge --ff-only`), atualiza as dependências do servidor pelo arquivo de travas e mostra o que mudou. Ele **nunca** toca em `data/`, em `.env`, na senha nem no modo de envio.
3. **Se ele recusar** (alterações locais, código 3; histórico divergente, código 4), mostre o motivo e **não force**. A pessoa decide: guardar as alterações (`git stash`), ou clonar de novo e copiar a pasta `data/`.
4. **Bridge:** só é trocada se o código dela mudou. Se o script avisar, peça para a pessoa fechar a bridge (pergunte de quem é o processo se não for deste plugin) e rode de novo com `--bridge`, ou compile (passo 4).
5. **Containers:** se os arquivos de `container/` mudaram, no servidor rode `bash container/instalar-vps.sh atualizar` (ele pergunta antes, refaz as imagens e reinicia, sem mexer na sessão nem na senha). O endereço do servidor MCP não muda.
6. **Se a pasta não é um clone do git** (código 2): no Claude Code instalado pelo catálogo, `/plugin marketplace update whatsapp-plugin` e `/plugin update whatsapp@whatsapp-plugin`; em outros casos, baixar a release e trocar a pasta, mantendo `data/`.
7. **Depois:** reiniciar o agente (ele só lê o servidor MCP e as skills ao iniciar), iniciar a bridge se foi fechada e rodar o diagnóstico (passo 0).

## Se algo der errado

| Sintoma | O que fazer |
|---|---|
| `uv`, `go` ou `gcc` "não é reconhecido" depois de instalar | abrir um terminal novo; conferir o PATH; rodar o diagnóstico |
| `go build` falha em `cgo` | falta o compilador C no PATH (ou use `baixar_bridge.py`, que dispensa o compilador) |
| O QR expirou antes de a pessoa ler | anexar `data/store/qr.png` de novo: o arquivo se renova sozinho |
| O áudio parou de transcrever depois de reiniciar o servidor | o comando do servidor está sem `--extra audio` (passo 3B) |
| O agente não mostra as ferramentas do WhatsApp | reiniciar o agente; conferir o caminho da pasta `server/` e se o `uv` está no PATH que o agente usa |
| `list_chats` falha ou dá erro de conexão | a bridge não está rodando: pedir à pessoa para iniciá-la (passo 5) |
| Lista vazia logo depois de parear | o histórico demora alguns minutos para chegar: esperar e tentar de novo |
| O diagnóstico acusa "Bridge exposta na rede" | fechar a bridge, iniciar a deste plugin (escuta só em `127.0.0.1`) ou definir a senha |
| As ferramentas `send_*` apareceram sem a pessoa pedir | `WHATSAPP_SEND_MODE` está em `hook` ou `two-step`; voltar para `read-only` e reiniciar |

Mais casos em `docs/solucao-de-problemas.md`.

## Por que

- **Diagnóstico depois de cada passo:** instalação por agente falha em silêncio (PATH que só vale em terminal novo, versão antiga de uma ferramenta). Rodar a mesma checagem toda vez troca "acho que deu certo" por uma prova.
- **PARE nos pontos que só a pessoa resolve:** o QR só ela lê, e escolher se o agente pode enviar mensagens em nome dela não é decisão de quem está instalando.
- **Envio desligado até a pessoa decidir:** uma mensagem enviada não se desfaz e chega a terceiros. O padrão seguro custa um passo a mais para quem quer enviar, e evita o pior caso para quem não leu nada.
- **Senha só no ambiente, nunca no chat:** o que aparece na conversa fica no histórico do agente e pode ser enviado ao modelo.
- **Não inventar configuração de agente:** cada agente guarda o servidor MCP e as skills de um jeito. Um caminho inventado parece funcionar e deixa a instalação quebrada sem aviso.
- **Atualizar sem reinstalar, com recusa em vez de força:** a pessoa já tem sessão, notas e configuração que valem mais que a versão nova. O script só avança por `--ff-only`, recusa quando há alteração local e nunca toca em `data/`; assim uma atualização não vira perda de dados.
- **Todas as perguntas de uma vez:** cada pergunta separada é uma volta de espera para a pessoa. Com a recomendação ao lado, ela responde em uma linha e a instalação segue sem parar.
- **Bridge pronta antes de compilar:** compilar exige Go e um compilador C, que é a parte mais lenta e a que mais falha. O binário publicado com SHA-256 troca isso por um download conferido, e a compilação fica como plano B.
- **QR como imagem:** em um chat, o desenho de caracteres do terminal sai distorcido e o código vence em segundos. A imagem renovada sozinha elimina o refazer.
- **Caminho C para agentes com terminal:** um agente que consegue alcançar a bridge ignora todos os modos de envio. Só o isolamento resolve.
