"""Testes do verificador de privacidade (scripts/check-privacy.py).

Os dados de exemplo sao montados em tempo de execucao, para este arquivo de teste tambem passar
no proprio verificador. Cada regra tem um caso que deve achar e outro que nao deve achar: so os
dois juntos provam que a regra funciona.
"""

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("verificador", RAIZ / "scripts" / "check-privacy.py")
verificador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verificador)

BARRA = chr(92)

# Dados que DEVEM ser achados: (regra esperada, valor)
SENSIVEIS = [
    ("ip_publico", ".".join(["8", "8", "4", "4"])),
    ("email", "pessoa" + "@" + "empresa-real.com.br"),
    ("telefone", "55" + "27" + "987654321"),
    ("id_whatsapp", "55" + "27" + "987654321" + "@s.whatsapp.net"),
    ("id_whatsapp", "120363" + "987654321098" + "@g.us"),
    ("cpf", "123." + "456." + "789-09"),
    ("cnpj", "12." + "345." + "678/0001-95"),
    ("token_ou_chave", "gh" + "p_" + "A" * 36),
    ("token_ou_chave", "sk" + "-" + "B" * 30),
    ("token_ou_chave", "AIza" + "C" * 35),
    ("token_ou_chave", "-----BEGIN " + "PRIVATE" + " KEY-----"),
    ("caminho_com_usuario", "C:" + BARRA + "Users" + BARRA + "joao" + BARRA + "projeto"),
    ("caminho_com_usuario", "/home/" + "maria" + "/projeto"),
]

# Dados que NAO devem ser achados
INOFENSIVOS = [
    "127.0.0.1",
    "192.168.1.10",
    "10.0.0.5",
    "172.16.0.9",
    "203.0.113.9",
    "198.51.100.7",
    "192.0.2.1",
    "0.0.0.0",
    "versao 1.2.3.4.5 do pacote",
    "1234+usuario@users.noreply.github.com",
    "contato@example.com",
    "5511999999999",
    "5511999999999@s.whatsapp.net",
    "1234567890@s.whatsapp.net",
    "WHERE jid LIKE '%@g.us'",
    "C:" + BARRA + "Users" + BARRA + "usuario" + BARRA + "projeto",
    "/home/user/projeto",
    "texto comum sem nenhum dado pessoal",
]


class TesteVerificadorDePrivacidade(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.raiz = Path(self.pasta.name)

    def escrever(self, nome, conteudo):
        caminho = self.raiz / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(conteudo if isinstance(conteudo, bytes) else conteudo.encode("utf-8"))
        return caminho

    def regras(self):
        return [r for _, _, r, _ in verificador.executar(self.raiz)]

    def test_acha_cada_tipo_de_dado_sensivel(self):
        for regra, valor in SENSIVEIS:
            with self.subTest(regra=regra, valor=valor[:6]):
                self.escrever("nota.md", "dado: " + valor + "\n")
                self.assertIn(regra, self.regras())

    def test_nao_acusa_dado_inofensivo(self):
        for valor in INOFENSIVOS:
            with self.subTest(valor=valor):
                self.escrever("nota.md", "texto: " + valor + "\n")
                self.assertEqual(self.regras(), [])

    def test_a_saida_nunca_mostra_o_valor_inteiro(self):
        for regra, valor in SENSIVEIS:
            with self.subTest(regra=regra, valor=valor[:6]):
                self.escrever("nota.md", valor + "\n")
                for _, _, _, mascarado in verificador.executar(self.raiz):
                    self.assertNotEqual(mascarado, valor)
                    self.assertLess(len(mascarado), len(valor) + 1)
                    self.assertNotIn(valor, mascarado)

    def test_ip_mostra_so_dois_blocos(self):
        self.escrever("nota.md", ".".join(["8", "8", "4", "4"]) + "\n")
        self.assertEqual(verificador.executar(self.raiz)[0][3], "8.8.x.x")

    def test_informa_arquivo_e_linha(self):
        self.escrever("docs/guia.md", "linha limpa\n" + SENSIVEIS[0][1] + "\n")
        arquivo, linha, regra, _ = verificador.executar(self.raiz)[0]
        self.assertEqual((Path(arquivo).name, linha, regra), ("guia.md", 2, "ip_publico"))

    def test_marcador_de_linha_libera_a_linha(self):
        self.escrever("nota.md", SENSIVEIS[0][1] + "  privacy:ignore\n")
        self.assertEqual(self.regras(), [])

    def test_arquivo_de_excecoes_libera_o_valor_exato(self):
        valor = SENSIVEIS[1][1]
        self.escrever("nota.md", valor + "\n")
        self.assertIn("email", self.regras())
        self.escrever(".privacy-allow", "# exemplo aprovado\n" + valor + "\n")
        self.assertEqual(self.regras(), [])

    def test_excecao_de_um_valor_nao_libera_outro(self):
        self.escrever(".privacy-allow", SENSIVEIS[1][1] + "\n")
        self.escrever("nota.md", SENSIVEIS[0][1] + "\n")
        self.assertIn("ip_publico", self.regras())

    def test_ignora_binarios_e_arquivos_de_trava(self):
        self.escrever("imagem.png", SENSIVEIS[0][1].encode("utf-8"))
        self.escrever("uv.lock", SENSIVEIS[0][1] + "\n")
        self.escrever("data/store.txt", SENSIVEIS[0][1] + "\n")
        self.assertEqual(self.regras(), [])

    def test_so_olha_o_que_esta_no_staging_quando_pedido(self):
        if shutil.which("git") is None:
            self.skipTest("git nao encontrado")
        subprocess.run(["git", "init", "-q"], cwd=self.raiz, check=True)
        self.escrever("fora.md", SENSIVEIS[0][1] + "\n")
        self.escrever("limpo.md", "nada aqui\n")
        subprocess.run(["git", "add", "limpo.md"], cwd=self.raiz, check=True)
        self.assertEqual(verificador.executar(self.raiz, so_staged=True), [])
        subprocess.run(["git", "add", "fora.md"], cwd=self.raiz, check=True)
        achados = verificador.executar(self.raiz, so_staged=True)
        self.assertEqual([r for _, _, r, _ in achados], ["ip_publico"])

    def test_o_proprio_repositorio_esta_limpo(self):
        achados = verificador.executar(RAIZ)
        self.assertEqual(achados, [], "dados sensiveis no repositorio: %s" % achados)


if __name__ == "__main__":
    unittest.main()
