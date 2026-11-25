---
name: mensagens-em-partes
description: Divide uma resposta de WhatsApp em várias mensagens curtas, do jeito que uma pessoa escreve (cumprimento sozinho, uma ideia por mensagem, pergunta por último), com um script que sugere onde cortar sem mudar nenhuma palavra, e orienta como enviar as partes com uma única confirmação. Use quando uma resposta tiver mais de uma ideia, for longa, ou quando o contato costumar receber mensagens picadas.
---

# Mensagens em partes

Pessoas raramente mandam um texto longo e arrumado no WhatsApp: mandam duas ou três mensagens curtas, em sequência. Um bloco único é o sinal mais comum de que a mensagem não foi escrita à mão. Esta skill diz quando e como dividir.

## Quando dividir

- A resposta tem mais de uma ideia.
- Há cumprimento mais assunto.
- Há um fato e uma pergunta ("Mudei a data. Pode ser sexta?").
- Passa de uns 160 caracteres.
- O histórico mostra que a pessoa costuma mandar várias mensagens seguidas para aquele contato.

## Quando não dividir

- Cabe em uma frase curta ("Fechado, te vejo lá.").
- A pessoa, com aquele contato, escreve em blocos: confira o histórico (skill `escrever-como-humano`).
- É uma informação que só faz sentido junta, como um endereço completo ou um código.

## Como dividir

1. **O cumprimento sai sozinho**, se for curto ("Bom dia!", "Oi, tudo bem?").
2. **Cada ideia vai em uma mensagem**, de uma a três frases curtas.
3. **A pergunta vai por último**, em mensagem própria, para ser a que a pessoa responde.
4. **De duas a quatro partes** é o normal. Mais de cinco já parece spam.
5. **Nunca corte** link, número decimal, hora (`15:30`) ou abreviação (`Dr.`) no meio.
6. **Nunca mude as palavras** ao dividir. Dividir é decidir onde cortar, não reescrever.

## O script

`scripts/dividir_mensagem.py` aplica essas regras e mostra a divisão. Rode a partir da pasta desta skill:

```
python scripts/dividir_mensagem.py "Bom dia! Preciso do relatório hoje. Consegue me mandar?"
```

```
[1/3] Bom dia!
[2/3] Preciso do relatório hoje.
[3/3] Consegue me mandar?
```

| Opção | Para que serve |
|---|---|
| `--max-chars N` | Tamanho máximo de cada parte (padrão 160). |
| `--max-partes N` | Número máximo de partes (padrão 5). Se passar, as menores são unidas e o script avisa. |
| `--json` | Saída em JSON, com as partes e as pausas sugeridas. |
| `-` no lugar do texto | Lê o texto da entrada padrão. |

A divisão é uma sugestão. Ajuste conforme o estilo da pessoa com aquele contato.

## Pausas

Entre as partes, deixe um intervalo parecido com o tempo de digitar: de 1 a 5 segundos, mais longo para partes maiores (o `--json` sugere os valores). Mensagens coladas, no mesmo instante, parecem automáticas.

## Como enviar as partes

A pessoa confirma o **conjunto** uma vez. Mostre todas as partes, numeradas, com o destinatário, e peça uma única confirmação.

| Modo do servidor | O que fazer |
|---|---|
| `hook` | Depois da confirmação, envie as partes na ordem, uma chamada de `send_message` por parte, com a pausa entre elas. Não altere nenhuma parte depois de confirmada. |
| `two-step` | Guarde cada parte, na ordem, com `send_message`. Entregue à pessoa **um só comando** com todos os identificadores: `python confirm.py send <id1> <id2> <id3>`. Ela confirma uma vez, no terminal. O comando recusa partes de destinatários diferentes. |
| `read-only` | Apenas mostre as partes. O envio está desligado. |

Se a pessoa pedir uma mudança em qualquer parte, volte a mostrar o conjunto inteiro e peça a confirmação de novo.

## Quando for texto longo demais

Se, mesmo dividido, passa de uns 500 caracteres, ou é um assunto delicado, sugira um áudio ou uma ligação em vez de uma enxurrada de mensagens.

## Por que

- **Dividir como a pessoa:** o ritmo das mensagens é parte do estilo, tanto quanto o vocabulário.
- **Pergunta por último:** é a mensagem que a outra pessoa responde; no meio, ela se perde.
- **Nunca mudar as palavras:** a pessoa confirmou aquele texto. Reescrever ao dividir enviaria algo que ela não viu.
- **Uma só confirmação para o conjunto:** uma confirmação por parte cansa e faz a pessoa confirmar sem ler.
