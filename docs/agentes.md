# Usar em cada agente

O servidor MCP é um servidor comum por stdio (e também por HTTP) e funciona em qualquer agente que aceite MCP; o Claude Code é só um deles. O que muda de um agente para outro é onde se cadastra o servidor e como se limitam as ferramentas.

Este guia só afirma o que está na documentação oficial de cada agente. O que não deu para confirmar aparece marcado como **não confirmado**: confira na documentação do seu agente antes de depender disso.

## O que vale para todos

**Comando do servidor** (troque o caminho pelo da pasta onde você baixou o plugin):

```
uv --directory /caminho/para/whatsapp-plugin/server run main.py
```

**Com transcrição de áudio**, instale uma vez com `uv --directory /caminho/para/whatsapp-plugin/server sync --extra audio` e use `run --extra audio main.py` no comando acima. Sem o `--extra audio` no comando, o `uv run` volta o ambiente ao padrão e desinstala o Whisper na próxima partida.

**Modo de envio.** Sem configurar nada, o servidor fica em `read-only`: lê, busca e transcreve, e as ferramentas de envio nem aparecem. Para enviar com confirmação sua, passe a variável `WHATSAPP_SEND_MODE=two-step` ao servidor. O modo `hook` envia direto e só deve ser usado no Claude Code, que tem o guarda de confirmação. Detalhes no README, seção "Modos de envio".

**A bridge precisa estar rodando** no mesmo computador do servidor. O hook que a liga sozinho é do Claude Code; nos outros agentes, inicie a bridge à mão (README, seção "Instalação").

**Skills.** As seis skills em `skills/` seguem o formato padrão de skill (uma pasta com `SKILL.md`, com `name` igual ao da pasta e `description`). Cada uma funciona sozinha. Os scripts delas leem as pastas de dados pelas variáveis `WHATSAPP_STORE_DIR`, `WHATSAPP_NOTES_DIR` e `WHATSAPP_DRAFTS_DIR`, então ao copiar uma skill para outro lugar, defina essas variáveis apontando para a pasta `data/` do plugin.

**Cuidado com agentes que têm terminal.** O comando `confirm.py` é a segunda etapa do modo `two-step` e foi feito para ser digitado por uma pessoa: ele exige um terminal interativo e a palavra `enviar`. Um agente que consiga abrir um terminal próprio e simular o teclado poderia, em teoria, rodá-lo sozinho. Se o seu agente tem ferramenta de shell, mantenha `read-only` ou use as permissões do agente para impedir comandos que chamem `confirm.py`.

## OpenCode

Fontes: opencode.ai/docs (MCP servers, permissions, config).

**Onde configurar.** `opencode.jsonc` (ou `opencode.json`) na pasta do projeto, ou `~/.config/opencode/opencode.jsonc` para valer em todos os projetos. O caminho global no **Windows não foi confirmado**.

**Cadastrar o servidor** (formato atual da documentação, com `mcp.servers`):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "whatsapp": {
        "type": "local",
        "command": ["uv", "--directory", "/caminho/para/whatsapp-plugin/server", "run", "main.py"],
        "environment": {
          "WHATSAPP_SEND_MODE": "read-only"
        }
      }
    }
  }
}
```

Para desligar sem apagar, use `"disabled": true` (a documentação diz para não usar um campo `enabled`). Também existe `opencode mcp add`.

**Limitar ferramentas.** As permissões são uma lista de regras, e a última regra que casar vence. O nome da ação de uma ferramenta MCP é `<servidor>_<ferramenta>`:

```jsonc
{
  "permissions": [
    { "action": "whatsapp_*", "resource": "*", "effect": "allow" },
    { "action": "whatsapp_send_*", "resource": "*", "effect": "ask" }
  ]
}
```

Esse exemplo é uma aplicação das regras documentadas ao nome `whatsapp_*`, não um exemplo copiado da documentação. A documentação também diz que `deny` esconde a ferramenta do agente. **Não confirmado:** como a pergunta (`ask`) aparece na interface.

## Codex (CLI da OpenAI)

Fonte: documentação de MCP do Codex. **Atenção:** o trecho de configuração abaixo veio de um resumo da página, não do texto literal. Confira na documentação atual antes de usar.

**Onde configurar.** `~/.codex/config.toml`, ou `.codex/config.toml` em projetos confiáveis. O caminho no **Windows não foi confirmado**.

```toml
[mcp_servers.whatsapp]
command = "uv"
args = ["--directory", "/caminho/para/whatsapp-plugin/server", "run", "main.py"]

[mcp_servers.whatsapp.env]
WHATSAPP_SEND_MODE = "read-only"
```

Também existe `codex mcp add <nome> --env VAR=valor -- <comando>`. Pelo resumo da página, é possível limitar as ferramentas (`enabled_tools` e `disabled_tools`) e definir o modo de aprovação (`default_tools_approval_mode`, com um ajuste por ferramenta em `[mcp_servers.<nome>.tools.<ferramenta>]`). **Não confirmado:** se essas chaves são literais da página e se o modo de aprovação é global ou por servidor.

## OpenClaw

Fonte: docs.openclaw.ai (configuração, MCP e skills dos nós, skills, sandbox).

**Skills.** Uma skill é uma pasta com `SKILL.md`. O OpenClaw lê de `<workspace>/skills`, `<workspace>/.agents/skills`, `~/.agents/skills` e da pasta gerenciada. Para instalar a partir de uma pasta local: `openclaw skills install ./caminho/da/skill --as nome` (a documentação diz que o `SKILL.md` precisa estar na raiz da origem).

**MCP.** A documentação que li descreve servidores MCP hospedados no **nó** (`nodeHost.mcp.servers` no `openclaw.json` da máquina do nó), com `command`, `args` e um filtro de ferramentas (`toolFilter` com `include`):

```json5
{
  nodeHost: {
    mcp: {
      servers: {
        whatsapp: {
          command: "uv",
          args: ["--directory", "/caminho/para/whatsapp-plugin/server", "run", "main.py"],
          toolFilter: { include: ["list_*", "search_*", "get_*", "download_media", "transcribe_audio"] }
        }
      }
    }
  }
}
```

Reinicie o nó depois de mudar a configuração. **Não confirmado:** como cadastrar um servidor stdio direto no gateway, e se existe uma chave `env` para o servidor (nenhum exemplo que li mostra). Se não houver `env`, defina `WHATSAPP_SEND_MODE` no ambiente do processo do nó. Sem a variável, o servidor já é `read-only`.

**Segurança.** O sandbox vem desligado por padrão (`agents.defaults.sandbox`), e a documentação diz que as ferramentas rodam no computador para a sessão principal enquanto o sandbox não for configurado. Existem `tools.allow` e `tools.deny`. **Não li** a página de política de ferramentas nem a de aprovação de comandos, então não afirmo as chaves exatas.

## OpenBot

Fonte: documentação do repositório do OpenBot. O desenho completo para usar o plugin com ele, com a bridge em containers, está em [openbot.md](openbot.md).

**MCP.** Os servidores MCP cadastrados pelo usuário valem para o **computador inteiro** (host), e não para um agente só: todos os agentes daquele host recebem as ferramentas. O painel de servidores MCP do app mascara os valores de cabeçalhos e de variáveis de ambiente. **Não confirmado:** onde fica o botão de adicionar, se os campos são `command`, `args` e `env`, e como os argumentos são separados. Use o app para cadastrar o comando e as variáveis e confira os nomes dos campos na tela.

**Skills.** Skills seguem o mesmo formato (pasta com `SKILL.md`). Adicione-as em **Settings, Skills, Local skills**; o OpenBot copia a skill para a pasta do agente (`.agents/skills` e `.claude/skills`). Atualizar a biblioteca não atualiza as cópias já instaladas.

**Segurança.** Os agentes do OpenBot rodam sem pedir confirmação a cada ação, e o servidor é do computador, não do agente. Por isso:

- deixe o servidor em `read-only` e ligue o envio só se você realmente precisar;
- se ligar `two-step`, lembre que o agente tem acesso à ferramenta de terminal e leia o aviso sobre o `confirm.py` acima;
- nunca use o modo `hook` no OpenBot: não existe o guarda de confirmação lá.

**Rotinas.** **Não confirmado** se uma rotina agendada dispara com o app fechado. A documentação diz que webhooks só funcionam com o computador online e que um servidor hospedado roda agentes em segundo plano, mas não afirma que uma rotina agendada dispara sozinha.

## Outros agentes (Grok, DeepSeek e demais)

Não li a documentação desses agentes, então não há instrução específica aqui. Qualquer agente que aceite um servidor MCP por stdio consegue usar o comando da seção "O que vale para todos". Procure no seu agente:

1. onde se cadastra um servidor MCP local (comando, argumentos e variáveis de ambiente);
2. como limitar ou pedir confirmação por ferramenta;
3. se o agente tem terminal próprio (nesse caso, siga o cuidado com o `confirm.py`).

Se o seu agente não tem MCP, não dá para usar este servidor. Os scripts das skills ainda funcionam sozinhos no terminal.
