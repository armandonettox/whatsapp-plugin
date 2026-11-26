---
description: Atualiza o plugin de WhatsApp para a ultima release, sem reinstalar nada
---

Atualize o plugin de WhatsApp para a ultima versao publicada. Nao envie nenhuma mensagem e nao apague nada da pasta `data/`.

1. **Verifique primeiro, sem alterar nada.** Rode `scripts/atualizar_plugin.py` (da skill `instalar-whatsapp`, a partir da pasta do plugin). Ele mostra a versao instalada, a ultima release e as notas dela. Se ja estiver na ultima, diga isso e termine.
2. **Se o script disser que a pasta nao e um clone do git** (codigo de saida 2), o plugin foi instalado pelo catalogo do Claude Code: use `/plugin marketplace update whatsapp-plugin` e depois `/plugin update whatsapp@whatsapp-plugin`, e reinicie o Claude Code. Catalogo de terceiros nao atualiza sozinho, entao a pessoa precisa pedir.
3. **Se ha versao nova**, mostre em poucas linhas o que muda (as notas) e pergunte se pode atualizar. So depois rode `scripts/atualizar_plugin.py --aplicar`.
4. **Se o script recusar** por alteracoes locais (codigo 3) ou historico divergente (codigo 4), mostre o motivo e **nao force nada**: explique o que a pessoa pode fazer (guardar as alteracoes com `git stash`, ou clonar de novo e copiar a pasta `data/`).
5. **Bridge.** Se o script disser que a bridge mudou, ela precisa ser fechada antes de trocar. Pergunte de quem e o processo se nao for o deste plugin, peca para a pessoa fechar e rode de novo com `--bridge` (ou compile). Containers mudaram: pergunte e rode `bash container/instalar-vps.sh atualizar` no servidor.
6. **Termine** lembrando de reiniciar o agente (ele so le o servidor MCP e as skills ao iniciar), de iniciar a bridge se foi fechada, e rode `scripts/verificar_instalacao.py` para conferir. Diga tambem que o modo de envio e a sessao do WhatsApp nao foram mexidos.
