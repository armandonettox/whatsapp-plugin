# whatsapp-plugin

Plugin do Claude Code que conecta o WhatsApp ao agente: servidor MCP em Python (`server/`), bridge em Go (`bridge/`), skills (`skills/`), comandos (`commands/`), hooks (`hooks/`) e documentação (`README.md` em inglês, `README.pt-BR.md`, `docs/`). Visão de uso e instalação no `README.md`.

## Contexto
- Stack: Python 3.11+ (FastMCP, httpx), Go 1.25+ (`whatsmeow`, SQLite via CGO), shell (hooks). Gerenciador do servidor: `uv`.
- Nomes de código em inglês, snake_case. Comentários em português, simples e naturais. Arquivos e pastas em minúsculo com hífen. Commits em português. Sem emojis em código, saídas ou documentos.
- Código de terceiros: o servidor e a bridge derivam do `whatsapp-mcp` de Luke Harries (MIT). A `whatsmeow` (MPL-2.0) é usada sem alterações.

## Mapa
- `server/`: `main.py` (ferramentas MCP e registro por modo de envio), `whatsapp.py` (leitura dos bancos e chamadas à bridge), `seguranca.py` (modos de envio e rascunhos), `confirm.py` (comando que a pessoa usa no terminal para confirmar), `audio.py` e `transcricao.py` (áudio, opcional).
- `bridge/`: `main.go` conecta ao WhatsApp, grava `data/store/*.db` e expõe a API em `127.0.0.1:8081` por padrão; `auth.go` guarda a senha da API e decide o endereço de escuta (com testes em `auth_test.go`).
- `container/`: Containerfiles da bridge e do servidor, `compose.yaml` para o computador e `quadlet/` para o Podman da VPS.
- `skills/`: seis skills (`instalar-whatsapp`, `usar-whatsapp-mcp`, `triagem-whatsapp`, `notas-por-contato`, `escrever-como-humano`, `mensagens-em-partes`), cada uma com `SKILL.md`, `references/` e, quando precisa, `scripts/`. O `_comum.py` existe nas skills `triagem-whatsapp` e `notas-por-contato` com o mesmo conteúdo (um teste confere), para cada skill funcionar sozinha.
- `commands/`: comandos do plugin (`status`, `pendentes`, `responder`, `resumo`, `loop`, `modo`, `atualizar`).
- `hooks/`: `hooks.json`, `whatsapp-bridge-ensure.sh` (liga a bridge) e `guard.sh` + `whatsapp-send-guard.py` (guarda de envio do Claude Code).
- `.claude-plugin/`: `plugin.json` e `marketplace.json`. `scripts/check-privacy.py`: verificador de privacidade. `tests/`: testes.

## Comandos
- Testes (guarda, vocabulário, verificador, modos de envio, scripts das skills, divisor de mensagens e estrutura): `python -m unittest discover -s tests -v`
- Verificador de privacidade: `python scripts/check-privacy.py` (tudo) ou `--staged` (só o que vai no commit). Ativar o hook uma vez por clone: `git config core.hooksPath .githooks`. Exceção justificada: valor exato em `.privacy-allow` ou `privacy:ignore` no fim da linha.
- Validar o plugin (precisa passar antes de commitar): `claude plugin validate . --profile directory` (o aviso de ícone é só do catálogo oficial).
- Testes da bridge: `cd bridge && go test ./...`
- Regenerar as imagens em inglês e os fluxos novos: `python scripts/gerar-diagramas.py docs` (as de português `arquitetura.svg`, `fluxo-envio.svg` e `fluxo-envio-animado.svg` são a fonte)
- Compilar a bridge: `cd bridge && go build -o main.exe .` (Windows) ou `go build -o whatsapp-bridge .`

## Regras

1. **Nenhum dado pessoal no repositório.** `data/` (mensagens e sessão do WhatsApp), `*.db`, `*.log`, binários, as notas por contato (`data/notas`) e os rascunhos do loop (`data/rascunhos`) ficam fora do git; os exemplos do repositório usam nomes e números fictícios. O verificador de privacidade (`scripts/check-privacy.py`, ligado ao hook `.githooks/pre-commit` e ao CI) barra IP público, e-mail, telefone, ID de WhatsApp, CPF, CNPJ, token e caminho com nome de usuário; nomes de pessoas continuam exigindo olhar à mão. **Motivação:** quem lê `data/` controla a conta de WhatsApp do dono, e as notas e os logs guardam texto de conversa de outras pessoas, protegido por lei de proteção de dados. Em repositório público não há como desfazer uma publicação.

2. **A API da bridge escuta só em `127.0.0.1` e nunca ganha outra interface.** Depois de mudar o `bridge/main.go`, conferir que o endereço de escuta é `127.0.0.1` (no Windows, `Get-NetTCPConnection -State Listen -LocalPort 8081`). **Motivação:** a API não tem senha e o `/api/send` envia mensagem pelo número do dono. Escutando em outra interface, qualquer máquina da rede poderia enviar sem passar por nenhuma confirmação. Escutar só em `127.0.0.1` não basta quando o agente tem terminal no mesmo computador: ele alcança a porta e chama o envio direto. Por isso a bridge aceita uma senha (`WHATSAPP_BRIDGE_TOKEN`, enviada como `Authorization: Bearer`), e em instalação para agentes com terminal a senha vale como obrigatória e fica fora do alcance do agente (outro container, outro usuário). Mudou a bridge ou as chamadas do servidor: rodar `go test ./...` em `bridge/` e `tests/test_token_da_bridge.py`.

3. **O guarda de envio falha fechado e só libera confirmação curta e direta.** Dúvida, pergunta (inclusive com `?` no fim), edição ("sim, mas troca"), frase longa, histórico ilegível ou Python ausente bloqueiam. Mudou o guarda: rodar os testes e acrescentar um caso novo. **Motivação:** um guarda que libera quando não consegue verificar não protege nada, e uma mensagem enviada a um contato por uma confirmação mal entendida não tem volta.

4. **Todo teste de bloqueio tem um irmão que libera.** Em `tests/`, cada cenário que deve bloquear vem com um que deve liberar, e os testes passam caminhos do sistema (`tempfile`), nunca `/tmp` do Git Bash. **Motivação:** como o guarda falha fechado, um erro de ambiente (arquivo não encontrado) também bloqueia, e os testes de bloqueio passariam pelo motivo errado. Só o caso que libera prova que a lógica rodou.

5. **O guarda só protege o Claude Code, e isso fica dito em todo lugar que fala de envio.** Hooks são recurso do Claude Code: em OpenBot, OpenClaw, Codex, OpenCode e outros o guarda não existe. Na documentação e nas respostas, nunca sugerir que o envio é protegido por ele fora do Claude Code; fora dele, a proteção é o modo de envio do servidor (regra 13). **Motivação:** quem usa o MCP em outro agente e acredita estar protegido pelo guarda pode enviar mensagens sem confirmação nenhuma.

6. **Credenciais e conteúdo real de pessoas ou empresas não entram.** Exemplos, testes e notas do repositório usam dados fictícios. **Motivação:** o projeto é público; dado ou credencial real não pode ser retirado depois de publicado.

7. **Manter o crédito e a licença do projeto de origem.** `LICENSE` (MIT, com o copyright de Luke Harries e o do dono) e `NOTICE` acompanham qualquer cópia. Não remover nem reescrever esses arquivos, e atualizar o `NOTICE` se entrar outro código de terceiros. **Motivação:** a licença MIT exige manter o aviso de copyright, e a MPL-2.0 da `whatsmeow` pede crédito. Sem isso, a publicação viola as licenças.

8. **Variável nova de ambiente entra no README.** Todas começam com `WHATSAPP_` (exceto `WHISPER_MODELO`) e aparecem na tabela de variáveis dos dois READMEs (`README.md` e `README.pt-BR.md`), com o padrão e para que serve. **Motivação:** quem instala o plugin só descobre o que dá para configurar pelo README; variável escondida vira pedido de suporte.

9. **Visuais seguem a paleta do projeto e o texto vai em SVG, não no gerador de imagem.** Tema claro e escuro, Inter como fonte:

   | Papel | Claro | Escuro |
   |---|---|---|
   | Fundo | `#F6F8F7` | `#0F1B22` |
   | Texto | `#1B2A33` | `#E6EEF0` |
   | Fluxo e acento | `#2BB673` | `#3DD68C` |
   | Componentes | `#2F6F8F` | `#5FA8C9` |
   | Guarda e atenção | `#F2A93B` | `#F2A93B` |
   | Bloqueio | `#E5604D` | `#F07C6B` |

   Texto pequeno no tema claro usa versões mais escuras (`#1B7F52` para o verde, `#B8402E` para o coral). Diagramas em SVG com `prefers-color-scheme`, título e descrição para leitores de tela. Imagens geradas ficam sem texto e sem a marca do WhatsApp. **Motivação:** uma paleta única dá identidade ao projeto; o contraste do verde e do coral em texto pequeno no fundo claro é baixo; e geradores de imagem erram acento e palavra em português, enquanto SVG com texto real é nítido e acessível.

10. **O vocabulário do guarda só cresce com teste, e a lista de recusa é uma segunda barreira também testada.** Palavra ou frase nova de confirmação entra em `hooks/whatsapp-send-guard.py` junto com um caso em `tests/test_vocabulario.py`; palavra de recusa, edição ou adiamento nunca vai para as listas que liberam, e o teste de listas disjuntas barra isso. Depois de mexer, fazer o teste de mutação: esvaziar de propósito a lista de recusa, a de confirmadores e a checagem do `?`, e conferir que a bateria falha. O arquivo do guarda fica em ASCII, sem emoji: emojis são dados por código com `chr()`. **Motivação:** o guarda é a última barreira antes de uma mensagem sair em nome do dono, e cada palavra a mais é uma chance de liberar o que não devia. As palavras de recusa já bloqueiam por serem desconhecidas; só um teste que desligue essa primeira barreira prova que a lista de recusa funciona.

11. **Hook ou script que chama Python testa o interpretador antes de usar.** Percorrer `python3`, `python` e `py` e usar o primeiro que roda `-c "import sys"`; sem nenhum, bloquear. É o que fazem `hooks/guard.sh` e `.githooks/pre-commit`. **Motivação:** no Windows, `python3` costuma ser um atalho da Microsoft Store que termina com erro. Um hook que usa o primeiro nome encontrado pode bloquear tudo, e só testar os dois cenários (bloqueia e libera) mostra isso.

12. **IP, telefone e identificadores reais nunca entram em arquivo, exemplo nem log de CI.** Exemplos usam as faixas reservadas para documentação (`203.0.113.x`, `198.51.100.x`, `192.0.2.x`), números como `5511999999999` e IDs de exemplo. `127.0.0.1` só aparece quando é o loopback de verdade. A saída do verificador mascara o valor (`8.8.x.x`). **Motivação:** um IP não é credencial, mas identifica um servidor, e o log do CI é guardado e pode ser público. Depois que um IP entra no histórico do git, só reescrever o repositório o remove.

13. **O servidor é seguro por padrão: sem `WHATSAPP_SEND_MODE`, ele é somente leitura.** As ferramentas de envio só existem nos modos `two-step` (rascunho que a pessoa confirma no terminal com `server/confirm.py`) e `hook` (envio direto, só onde um hook confirma). Valor desconhecido cai em `read-only`. O `confirm.py send` exige terminal interativo e a palavra digitada, aceita várias partes só do mesmo destinatário e nunca ganha opção para pular a pergunta. Mudou `seguranca.py`, `confirm.py` ou o registro das ferramentas em `main.py`: rodar `tests/test_modo_de_envio.py` e fazer o teste de mutação (padrão trocado, read-only registrando envio, trava de terminal removida, pergunta aceitando tudo, two-step enviando direto, identificador sem formato, envio sem confirmação, sem limite e sem expiração). Os testes apontam a bridge para uma porta que recusa a conexão (`WHATSAPP_API_BASE_URL`), para que um envio acidental nunca chegue à bridge de verdade. **Motivação:** o guarda do Claude Code é um hook e não existe nos outros agentes. Quem instala o plugin em outro agente sem ler a documentação não pode acabar com um agente que envia mensagens sem confirmação. A proteção precisa estar no servidor, que é o ponto comum a qualquer agente.

14. **Cada skill funciona sozinha e tem o `name` igual ao da pasta.** Os arquivos que a skill cita (`references/`, `scripts/`) existem dentro dela; os scripts leem as pastas de dados por variável de ambiente, com um padrão dentro do plugin. Nada de caminho absoluto, nome de pessoa real ou dado real nas skills. `tests/test_estrutura_do_plugin.py` confere. **Motivação:** quem instala uma skill isolada (por exemplo, em outro agente) não tem o resto do plugin, e um arquivo citado que não existe faz o agente seguir instruções que não consegue cumprir.

15. **Textos públicos dizem como as coisas funcionam, não o histórico de como chegaram aqui.** README, skills, comandos, diagramas, comentários e testes não citam datas de problemas passados, pessoas, empresas, notas privadas nem relatos do que foi corrigido; descrevem a regra e o motivo técnico. O teste de estrutura procura esses rastros. **Motivação:** o texto é lido por quem instala e usa o plugin. O histórico interno não ajuda essa pessoa e mistura contexto privado com o que é público.

16. **Em container, o agente nunca está na mesma rede da bridge.** A bridge fica só na rede `back` (com o servidor MCP) e o agente só na rede `agente` (com o servidor MCP); nenhuma porta é publicada fora de `127.0.0.1`; a senha vem de segredo ou de variável obrigatória, nunca de valor em arquivo; tudo roda sem root, sem capacidades e sem privilégios extras; o modo `hook` não existe em container. `tests/test_containers.py` trava isso. Valor de variável com espaço no Quadlet vai entre aspas. Depois de mexer em `container/`, simular os Quadlets com `QUADLET_UNIT_DIRS=<pasta> /usr/lib/systemd/system-generators/podman-system-generator --user --dryrun` (não instala nada). **Motivação:** o agente tem terminal; se alcançar a API da bridge, ignora os modos de envio do servidor. O Quadlet corta valores com espaço e rejeita chaves que a versão do Podman não conhece (`NetworkAlias`, por exemplo), e só a simulação mostra isso.

17. **Toda variável de ambiente usada no código está na tabela do README.** `tests/test_estrutura_do_plugin.py` confere. **Motivação:** variável sem documentação vira pedido de suporte, e uma de segurança sem documentação não é ligada.

18. **O projeto é para qualquer agente com MCP; o Claude Code é um dos agentes, não o padrão.** Título, descrições, README, diagrama e guias apresentam o servidor MCP como o centro e o Claude Code como um caminho (o plugin, com comandos, hook e guarda). O que só existe no Claude Code (hook, guarda, comandos `/whatsapp:*`, modo `hook`, `claude --plugin-dir`) continua dizendo Claude Code, porque é um fato técnico. Texto novo não escreve "Claude Code" onde vale para todos. `tests/test_estrutura_do_plugin.py` confere. **Motivação:** um projeto apresentado como "para Claude Code" afasta quem usa outro agente, e o servidor, as skills e os containers funcionam em todos.

19. **O README principal é em inglês e há uma versão em português; os dois contam a mesma história.** Texto novo no README entra nos dois, com as mesmas seções, os mesmos blocos de código e as mesmas variáveis. Cada versão usa as imagens no próprio idioma (`docs/architecture.svg` e `docs/arquitetura.svg`, e assim por diante). As imagens em inglês e os fluxos novos são gerados por `scripts/gerar-diagramas.py`; não se edita um SVG gerado à mão. Os guias em `docs/` estão em português e o README em inglês avisa isso. `tests/test_imagens.py` e `tests/test_estrutura_do_plugin.py` conferem. **Motivação:** o projeto é para qualquer agente e qualquer pessoa, e o inglês é o idioma comum de quem escolhe uma ferramenta assim; o português continua sendo o idioma de quem mantém. Duas versões editadas à mão divergem em semanas, e uma imagem com texto no idioma errado confunde mais do que ajuda.
