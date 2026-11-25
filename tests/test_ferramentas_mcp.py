"""Chama cada ferramenta de leitura pelo protocolo MCP, como um agente faz.

O pacote mcp valida a saida da ferramenta contra o tipo declarado. Testar so as funcoes soltas
deixa passar uma ferramenta que devolve o tipo errado; aqui o servidor roda de verdade e um
cliente MCP em memoria chama cada ferramenta contra um banco sintetico.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tests"))

import fixtures  # noqa: E402

TEM_MCP = importlib.util.find_spec("mcp") is not None

# Roda dentro de um processo novo, para o servidor ler as variaveis de ambiente do teste.
CLIENTE = r'''
import asyncio, json, sys
sys.path.insert(0, sys.argv[1])
import main
from mcp.shared.memory import create_connected_server_and_client_session

async def chamar(sessao, nome, args):
    r = await sessao.call_tool(nome, args)
    texto = "".join(getattr(c, "text", "") for c in r.content)
    return {"erro": bool(r.isError), "texto": texto, "estruturado": r.structuredContent}

async def principal():
    saida = {}
    async with create_connected_server_and_client_session(main.mcp._mcp_server) as sessao:
        saida["ferramentas"] = sorted(t.name for t in (await sessao.list_tools()).tools)
        for nome, args in json.loads(sys.argv[2]):
            saida[nome + "|" + json.dumps(args, sort_keys=True)] = await chamar(sessao, nome, args)
    print(json.dumps(saida))

asyncio.run(principal())
'''


@unittest.skipUnless(TEM_MCP, "precisa do pacote mcp (rode no ambiente do lock)")
class FerramentasDeLeituraPeloMcp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = Path(cls.tmp.name) / "store"
        fixtures.criar_banco(cls.store)
        import sqlite3

        con = sqlite3.connect(cls.store / "messages.db")
        con.execute(
            "INSERT INTO messages (id, chat_jid, sender, content, timestamp, is_from_me, media_type, filename) "
            "VALUES ('doc1', ?, ?, '', ?, 0, 'document', 'contrato-exemplo.pdf')",
            (fixtures.JOAO_PN, fixtures.JOAO_PN.split("@")[0], fixtures._ts(1)),
        )
        con.commit()
        con.close()

        chamadas = [
            ("list_chats", {"limit": 5}),
            ("search_contacts", {"query": "Maria"}),
            ("list_messages", {"chat_jid": fixtures.JOAO_PN, "limit": 5}),
            ("get_chat", {"chat_jid": fixtures.JOAO_PN}),
            ("get_chat", {"chat_jid": "0000@s.whatsapp.net"}),
            ("get_direct_chat_by_contact", {"sender_phone_number": "5511999990002"}),
            ("get_contact_chats", {"jid": fixtures.JOAO_PN}),
            ("get_last_interaction", {"jid": fixtures.JOAO_PN}),
            ("get_message_context", {"message_id": "msg3", "before": 1, "after": 1}),
        ]
        env = {k: v for k, v in os.environ.items() if not k.startswith("WHATSAPP_")}
        env.update({"WHATSAPP_STORE_DIR": str(cls.store), "PYTHONIOENCODING": "utf-8",
                    "WHATSAPP_API_BASE_URL": "http://127.0.0.1:9/api"})
        r = subprocess.run(
            [sys.executable, "-c", CLIENTE, str(RAIZ / "server"), json.dumps(chamadas)],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=120,
        )
        if r.returncode != 0:
            raise AssertionError(f"o cliente MCP falhou:\n{r.stderr[-1500:]}")
        cls.saida = json.loads(r.stdout.strip().splitlines()[-1])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def resultado(self, nome, args):
        return self.saida[nome + "|" + json.dumps(args, sort_keys=True)]

    def test_nenhuma_ferramenta_de_envio_no_modo_padrao(self):
        self.assertFalse([n for n in self.saida["ferramentas"] if "send" in n])
        self.assertIn("list_chats", self.saida["ferramentas"])

    def test_nenhuma_ferramenta_devolve_erro(self):
        for chave, r in self.saida.items():
            if chave == "ferramentas":
                continue
            with self.subTest(chave=chave):
                self.assertFalse(r["erro"], r["texto"][:300])

    def test_lista_de_conversas_traz_campos_e_data_em_texto(self):
        r = self.resultado("list_chats", {"limit": 5})
        conversas = json.loads(r["texto"]) if r["estruturado"] is None else r["estruturado"]["result"]
        jids = {c["jid"] for c in conversas}
        self.assertIn(fixtures.JOAO_PN, jids)
        joao = next(c for c in conversas if c["jid"] == fixtures.JOAO_PN)
        self.assertIsInstance(joao["last_message_time"], str)
        self.assertIs(joao["is_group"], False)
        grupo = next(c for c in conversas if c["jid"] == fixtures.GRUPO)
        self.assertIs(grupo["is_group"], True)

    def test_busca_de_contato_acha_a_pessoa(self):
        r = self.resultado("search_contacts", {"query": "Maria"})
        self.assertIn("5511999990001", r["texto"])

    def test_mensagens_voltam_como_texto_e_mostram_o_nome_do_arquivo(self):
        r = self.resultado("list_messages", {"chat_jid": fixtures.JOAO_PN, "limit": 5})
        self.assertIn("fechado, te vejo la", r["texto"])
        self.assertIn("document: contrato-exemplo.pdf", r["texto"])

    def test_conversa_inexistente_nao_e_erro(self):
        r = self.resultado("get_chat", {"chat_jid": "0000@s.whatsapp.net"})
        self.assertFalse(r["erro"])

    def test_conversa_por_jid_e_por_telefone(self):
        for nome, args in [("get_chat", {"chat_jid": fixtures.JOAO_PN}),
                           ("get_direct_chat_by_contact", {"sender_phone_number": "5511999990002"})]:
            with self.subTest(nome=nome):
                self.assertIn(fixtures.JOAO_PN, self.resultado(nome, args)["texto"])

    def test_contexto_de_mensagem_traz_a_mensagem_e_as_vizinhas(self):
        r = self.resultado("get_message_context", {"message_id": "msg3", "before": 1, "after": 1})
        self.assertIn("reuniao amanha as 10h?", r["texto"])
        self.assertIn("fechado, te vejo la", r["texto"])

    def test_ultima_interacao_mostra_o_documento(self):
        r = self.resultado("get_last_interaction", {"jid": fixtures.JOAO_PN})
        self.assertIn("contrato-exemplo.pdf", r["texto"])

    def test_pasta_dos_bancos_vem_da_variavel_de_ambiente(self):
        # O banco sintetico esta fora de data/store: se a variavel fosse ignorada, nada voltaria.
        r = self.resultado("list_chats", {"limit": 5})
        self.assertIn(fixtures.JOAO_PN, r["texto"])


if __name__ == "__main__":
    unittest.main()
