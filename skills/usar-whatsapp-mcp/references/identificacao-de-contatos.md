# Identificar contatos: `@lid` e número normal

O WhatsApp usa dois formatos de identificador para a mesma pessoa:

- `<número>@s.whatsapp.net`: o formato clássico, baseado no telefone.
- `<id>@lid`: um identificador novo, que o WhatsApp usa cada vez mais por privacidade. Não dá para descobrir o telefone só olhando para ele.

**A mesma pessoa pode aparecer com os dois em momentos diferentes**, e as mensagens podem estar "escondidas" sob o identificador que você não está olhando. Para o servidor, são duas conversas.

## Descobrir quem é um `@lid` sem nome

Siga a ordem, parando quando achar:

1. **Scripts da skill `triagem-whatsapp`** (`listar_pendentes.py`, `buscar_contato.py`, `resumo_contato.py`): já juntam os dois identificadores e usam o nome da agenda sincronizada do celular. Resolvem a maioria dos casos.
2. **`search_contacts`** com o número ou parte do nome. Ele só consulta as conversas já vistas pelo servidor, então um resultado vazio não prova que o contato é desconhecido.
3. **O conteúdo da mensagem.** Muitas vezes a pessoa se apresenta ("oi, aqui é a Maria").
4. **O mapa de identificadores** no banco de sessão da bridge:

   ```sql
   SELECT * FROM whatsmeow_lid_map WHERE lid = '<número do lid>' OR pn = '<número conhecido>';
   ```

   A tabela liga `lid` ao telefone (`pn`) quando o WhatsApp já fez essa associação.
5. Se nada resolver, **avise a pessoa em vez de adivinhar**. Mandar mensagem para a pessoa errada não se desfaz.

## Ao enviar

Use o identificador pelo qual aquele contato fala com você de fato (o do histórico recente). Não assuma que enviar para `@s.whatsapp.net` vai cair na conversa que está em `@lid`, nem o contrário.

## Pessoas diferentes com nomes parecidos

Se a busca devolver mais de um contato (por exemplo, pai e filho com o mesmo primeiro nome), confirme com a pessoa qual é antes de seguir.
