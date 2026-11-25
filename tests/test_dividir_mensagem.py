"""Testes do divisor de mensagens (skills/mensagens-em-partes/scripts/dividir_mensagem.py).

A propriedade mais importante: juntar as partes reproduz o texto original, sem mudar nenhuma
palavra. O script so decide onde cortar.
"""

import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO = RAIZ / "skills" / "mensagens-em-partes" / "scripts" / "dividir_mensagem.py"
_spec = importlib.util.spec_from_file_location("divisor", CAMINHO)
divisor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(divisor)


def normal(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


TEXTOS = [
    "Bom dia! Preciso do relatorio hoje. Consegue me mandar?",
    "Oi, tudo bem? Passei aqui pra avisar que a reuniao mudou pra quinta. Consigo te ligar depois das 15:30 se for melhor.",
    "Falei com o Dr. Silva ontem. Ele topou. O valor ficou em 10.50 por unidade, mas ainda vou confirmar.",
    "Veja os detalhes em https://exemplo.com/pagina.html?id=3&x=1. Depois me avise se ficou claro.",
    "Eu queria te explicar uma coisa, mas antes preciso saber se voce tem tempo, porque o assunto e meio longo e envolve varias pessoas do time.",
    "Acho que o prazo vai apertar. Mudei a data. Pode ser sexta?",
    "primeira linha\nsegunda linha\n\nterceira linha depois de um espaco",
    "Opa! Vi sua mensagem agora. Dei uma olhada no arquivo, esta tudo certo. So falta o anexo do contrato, que ficou de vir ontem. Me manda quando puder? Valeu!",
]


class TesteDivisor(unittest.TestCase):
    def test_juntar_as_partes_reproduz_o_texto_sem_mudar_palavras(self):
        for texto in TEXTOS:
            for limite in (40, 80, 160, 400):
                with self.subTest(texto=texto[:30], limite=limite):
                    partes, _ = divisor.dividir(texto, max_chars=limite, max_partes=50)
                    self.assertEqual(normal(" ".join(partes)), normal(texto))

    def test_texto_curto_fica_em_uma_parte(self):
        partes, _ = divisor.dividir("Fechado, te vejo la.")
        self.assertEqual(partes, ["Fechado, te vejo la."])

    def test_cumprimento_curto_sai_sozinho(self):
        partes, _ = divisor.dividir("Bom dia! Preciso do relatorio hoje. Consegue me mandar?")
        self.assertEqual(partes, ["Bom dia!", "Preciso do relatorio hoje.", "Consegue me mandar?"])

    def test_cumprimento_sem_mais_nada_nao_e_dividido(self):
        self.assertEqual(divisor.dividir("Bom dia")[0], ["Bom dia"])

    def test_pergunta_final_sai_por_ultimo_em_uma_mensagem_propria(self):
        partes, _ = divisor.dividir("Acho que o prazo vai apertar. Mudei a data. Pode ser sexta?")
        self.assertEqual(partes, ["Acho que o prazo vai apertar. Mudei a data.", "Pode ser sexta?"])

    def test_link_decimal_hora_e_abreviacao_nao_sao_cortados(self):
        casos = {
            "https://exemplo.com/pagina.html?id=3&x=1": TEXTOS[3],
            "10.50": TEXTOS[2],
            "15:30": TEXTOS[1],
            "Dr. Silva": TEXTOS[2],
        }
        for trecho, texto in casos.items():
            with self.subTest(trecho=trecho):
                partes, _ = divisor.dividir(texto, max_chars=60, max_partes=50)
                self.assertTrue(any(trecho in parte for parte in partes), partes)

    def test_respeita_o_limite_de_caracteres_quando_da_para_cortar(self):
        for texto in TEXTOS:
            with self.subTest(texto=texto[:30]):
                partes, _ = divisor.dividir(texto, max_chars=70, max_partes=50)
                for parte in partes:
                    maior_palavra = max(len(p) for p in parte.split())
                    self.assertTrue(len(parte) <= 70 or maior_palavra > 40, parte)

    def test_frase_longa_e_cortada_em_virgulas_e_conectores(self):
        partes, _ = divisor.dividir(TEXTOS[4], max_chars=60, max_partes=50)
        self.assertGreater(len(partes), 1)
        self.assertTrue(all(len(p) <= 60 for p in partes), partes)

    def test_limite_de_partes_une_as_menores_e_avisa(self):
        texto = " ".join(f"Frase numero {i} com algum texto." for i in range(8))
        partes, avisos = divisor.dividir(texto, max_chars=36, max_partes=3)
        self.assertLessEqual(len(partes), 3)
        self.assertTrue(avisos)
        self.assertEqual(normal(" ".join(partes)), normal(texto))

    def test_texto_vazio(self):
        self.assertEqual(divisor.dividir("   ")[0], [])

    def test_pausas_sugeridas(self):
        partes = ["Oi!", "x" * 20, "y" * 400]
        pausas = divisor.pausas_sugeridas(partes)
        self.assertEqual(pausas[0], 0.0)
        self.assertEqual(len(pausas), len(partes))
        self.assertTrue(all(1.0 <= p <= 5.0 for p in pausas[1:]))
        self.assertEqual(pausas[2], 5.0)

    def test_linha_de_comando_json_e_entrada_padrao(self):
        r = subprocess.run(
            [sys.executable, str(CAMINHO), "-", "--json"], input="Bom dia! Preciso do relatorio hoje. Consegue me mandar?",
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        dados = json.loads(r.stdout)
        self.assertEqual(dados["partes"], ["Bom dia!", "Preciso do relatorio hoje.", "Consegue me mandar?"])
        self.assertEqual(len(dados["pausas_segundos"]), 3)

    def test_linha_de_comando_texto_vazio_sai_com_erro(self):
        r = subprocess.run([sys.executable, str(CAMINHO), "   "], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
