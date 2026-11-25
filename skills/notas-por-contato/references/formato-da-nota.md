# Formato da nota por contato

## Onde fica

Um arquivo `<slug>.md` por contato, na pasta de notas (`data/notas` do plugin, ou `WHATSAPP_NOTES_DIR`).

O slug é o nome do contato em minúsculas, sem acento e com hífen no lugar dos espaços. Exemplo: "Maria Silva" vira `maria-silva.md`. O texto entre parênteses no nome é ignorado.

## Estrutura

```markdown
---
contato: Nome como salvo no WhatsApp
jid: 5511999999999@s.whatsapp.net | 11111111111111@lid
atualizado: AAAA-MM-DD
---

## Estilo identificado
- sinais concretos: caixa, acentuação, abreviações, apelidos, emojis, formalidade, como divide em mensagens

## Relação
- quem é: amigo, colega de trabalho, família, prestador de serviço

## Observações
- padrões recorrentes: assuntos comuns, piadas internas, coisas a evitar

## Compromissos abertos
- [ ] AAAA-MM-DD: o que a pessoa prometeu fazer
- [x] AAAA-MM-DD: compromisso cumprido (concluído AAAA-MM-DD)

## Histórico de decisões
- AAAA-MM-DD: sugeri "X", a pessoa confirmou sem mudar
- AAAA-MM-DD: sugeri "X", a pessoa mudou para "Y" - o que isso ensina sobre o tom
- AAAA-MM-DD: sugeri responder, a pessoa decidiu não responder - motivo
```

O cabeçalho lista os dois identificadores do contato. É por eles que o script acha a nota, mesmo que o nome tenha mudado.

## Quando criar e atualizar

- **Criar** na primeira vez que você analisa um contato recorrente.
- **Atualizar "Estilo identificado"** quando a pessoa corrigir o tom sugerido: é sinal de que a nota está incompleta.
- **Registrar uma decisão** depois de cada reação da pessoa a uma sugestão. É o que faz a nota ficar mais precisa com o tempo.
- **Guardar só as últimas 10 decisões.** O padrão aprendido já deve estar em "Estilo identificado" e "Observações"; o histórico é só para o aprendizado recente.

## O que nunca vai aqui

- Dados sensíveis de terceiros (outros números, saúde, finanças, documentos).
- Cópias literais de mensagens privadas.
