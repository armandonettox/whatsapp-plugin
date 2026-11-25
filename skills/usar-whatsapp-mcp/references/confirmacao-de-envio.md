# Confirmação de envio

Uma mensagem enviada não se desfaz e chega a uma terceira pessoa. Por isso, **nada sai sem a confirmação clara da pessoa para aquele texto específico**.

## O fluxo, por modo

| Modo | Como funciona |
|---|---|
| `read-only` | Não há envio. Entregue o texto à pessoa na conversa e explique que o envio está desligado. |
| `two-step` | O agente chama `send_*`, que só guarda um rascunho, e entrega à pessoa o comando que ela roda no próprio terminal. Quem confirma é ela, digitando `enviar`. |
| `hook` | O agente mostra o destinatário e o texto, a pessoa confirma na conversa e o agente chama `send_*`. No Claude Code, um guarda confere a confirmação e bloqueia o que não for claro. |

## Passos para qualquer modo

1. Mostre o destinatário e o texto exato, entre aspas.
2. Espere a resposta da pessoa.
3. Se ela pedir uma mudança, reescreva e volte ao passo 1.
4. Só então envie (modo `hook`) ou guarde o rascunho (modo `two-step`).
5. Diga o que aconteceu: enviado, ou rascunho guardado com o comando para confirmar.

Cada mensagem é uma ação separada. Em uma sequência de partes, mostre todas juntas, com o mesmo destinatário, e peça uma única confirmação para o conjunto.

## O que conta como confirmação (modo `hook`)

Uma frase curta, só de confirmação, para o texto mostrado. O guarda do plugin aceita, em português, inglês e espanhol, exemplos como:

- `sim`, `manda`, `pode mandar`, `pode seguir`, `envia`, `confirmo`, `beleza, manda`, `fechado`, `com certeza`
- `yes`, `send it`, `go ahead`, `sounds good`, `please send it`
- `si`, `dale`, `mandalo`, `de acuerdo`

Também vale um polegar para cima ou uma marca verde. Até 8 palavras, sem nenhuma palavra de dúvida ou de mudança.

## O que NÃO conta

- Pedido de edição: "troca o oi", "tira a última frase", "adiciona um beijo".
- Confirmação com ressalva: "sim, mas espera", "pode, só depois das 18h".
- Pergunta, mesmo que as palavras sejam de confirmação: "pode mandar?", "tá bom?". Uma pergunta é uma dúvida.
- Um assunto novo ("pergunta também se ele vem"): isso é conteúdo para uma nova mensagem, que precisa ser mostrada e confirmada.
- Silêncio, ou a aprovação de uma mensagem anterior da sequência.

Se o guarda bloquear uma resposta, mostre o texto de novo e pergunte: "é para enviar?". É melhor uma pergunta a mais do que uma mensagem enviada errada.

## No modo `two-step`

1. Chame `send_message` (ou `send_file`, `send_audio_message`) para cada mensagem. Você recebe um `pending_id` e o comando `how_to_send`.
2. Mostre à pessoa o texto, o destinatário e o comando. Com várias partes, entregue um só comando com todos os identificadores, na ordem: `python confirm.py send <id1> <id2> <id3>`.
3. A pessoa abre o terminal dela, confere o texto e digita `enviar`.
4. Se quiser saber o resultado, use `check_pending_send`. Nunca diga que enviou antes de `sent`.

O rascunho expira em 30 minutos e o servidor guarda no máximo 20 por vez.
