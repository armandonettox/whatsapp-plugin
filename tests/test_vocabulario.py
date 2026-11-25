"""Testes do vocabulario do guarda de envio (frases que liberam e frases que bloqueiam).

Carrega o guarda direto, sem abrir um processo por frase, para poder testar centenas de casos.
Rodar: python -m unittest discover -s tests -v

Regra do projeto: toda lista que deve bloquear tem uma lista irma que deve liberar. Como o guarda
falha fechado, so as frases que liberam provam que a leitura funcionou de verdade.
"""

import importlib.util
import unittest
import unittest.mock
from pathlib import Path

CAMINHO = Path(__file__).resolve().parents[1] / "hooks" / "whatsapp-send-guard.py"
_spec = importlib.util.spec_from_file_location("guarda_de_envio", CAMINHO)
guarda = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guarda)

# Emojis por codigo, para o arquivo de teste tambem nao ter emoji literal
POLEGAR_CIMA = chr(0x1F44D)
POLEGAR_BAIXO = chr(0x1F44E)
OK_MAO = chr(0x1F44C)
MARCA_VERDE = chr(0x2705)
CRUZ_VERMELHA = chr(0x274C)
FOGUETE = chr(0x1F680)
PENSANDO = chr(0x1F914)
RISADA = chr(0x1F602)
FESTA = chr(0x1F389)
TOM_DE_PELE = chr(0x1F3FD)
SELETOR = chr(0xFE0F)

LIBERA_PORTUGUES = [
    "sim", "Sim.", "SIM", "manda", "MANDA", "pode enviar", "Pode enviar!", "confirma", "ok", "pode mandar",
    "pode", "pode seguir", "envia", "envia logo", "manda ver", "bora", "fechado", "isso, manda",
    "Pode mandar sim!", "beleza, manda", "claro, pode enviar", "manda ai", "Manda aí!", "perfeito",
    "uhum", "aham", "positivo", "afirmativo", "autorizo", "autorizado", "aprovado", "com certeza",
    "com certeza pode mandar", "sem problema", "sem problemas", "sem dúvida pode mandar", "pode crer",
    "manda bala", "pode ir", "de acordo", "estou de acordo", "ta bom", "está bom", "ta bom, pode mandar",
    "tudo certo", "tudo certo, pode mandar", "tudo bem, pode mandar", "isso mesmo", "isso mesmo, manda",
    "isso aí, manda", "exatamente isso", "claro que sim", "claro que pode", "pode sim", "quero sim",
    "vai lá", "vamos nessa", "vamos la", "bora la", "faz isso", "faça isso", "pode fazer isso", "jóia",
    "show", "top", "massa", "blz", "blz, manda", "beleza, pode mandar", "ótimo", "Ótimo, pode mandar",
    "excelente", "exato", "correto", "concordo", "bacana, pode mandar", "valeu, manda",
    "obrigado, pode mandar", "manda por favor", "pode mandar por favor", "por favor, manda", "manda pfv",
    "pode enviar a mensagem", "manda a mensagem", "envia o texto", "manda a resposta", "manda essa",
    "pode mandar essa", "manda esse", "pode mandar essa mensagem", "pode soltar", "solta", "dispara",
    "pode disparar", "libera", "liberado", "fechou", "fechado, pode mandar", "combinado", "certo",
    "certo, pode mandar", "claro", "claro, manda", "confirmado", "confirmo", "ok, manda", "ok, pode mandar",
    "okay", "oki", "tranquilo, manda", "pode ir sim", "partiu", "vamos", "manda ver sim",
    "Está ótimo, pode mandar", "Sim, pode enviar!!!", "sim sim sim", "sim, manda logo agora mesmo",
    "certeza", "pode mandar, doutor",
]

LIBERA_INGLES = [
    "yes", "Yes.", "YES", "yeah", "yep", "yup", "sure", "ok", "okay", "send", "go", "confirm", "confirmed",
    "approved", "proceed", "absolutely", "definitely", "certainly", "correct", "agreed", "affirmative",
    "lgtm", "fine", "good", "great", "perfect", "cool", "nice", "alright", "yes send it",
    "yes please send it", "send it", "do it", "go ahead", "go ahead and send it", "sounds good",
    "looks good", "looks good to me", "that is right", "that's right", "thats correct", "of course",
    "for sure", "yes go ahead", "yes please", "please send", "please send it now", "ok send it",
    "yep send it", "sure go ahead", "approved send it", "confirmed send", "fire away", "ship it",
    "yes, please do", "ok, go ahead",
]

LIBERA_ESPANHOL = [
    "si", "Sí", "dale", "vale", "listo", "adelante", "envialo", "mandalo", "si mandalo", "si envialo",
    "de acuerdo", "por supuesto", "claro que si", "hazlo", "sin problema", "perfecto", "genial", "aprobado",
    "correcto", "todo bien", "esta bien", "esta bien mandalo", "dale mandalo ya", "vale, envialo",
]

LIBERA_EMOJI = [
    POLEGAR_CIMA, POLEGAR_CIMA * 2, OK_MAO, MARCA_VERDE, FOGUETE, "sim " + POLEGAR_CIMA, "ok " + POLEGAR_CIMA * 2,
    "bora " + FOGUETE, POLEGAR_CIMA + TOM_DE_PELE, POLEGAR_CIMA + SELETOR, MARCA_VERDE + SELETOR,
    "manda " + OK_MAO,
]

BLOQUEIA_PERGUNTAS = [
    "pode mandar agora?", "pode mandar?", "sim?", "manda?", "pode enviar?", "Pode mandar sim?",
    "pode ser outro dia?", "e se eu pedir pra falar de outra coisa tambem?", "ok?", "tudo bem?",
    "yes?", "send it?", "sure?", "si?", "¿puedo enviar?", "sim？", "o que voce acha?",
    "¿si?", "claro?", "certo?",
]

BLOQUEIA_RECUSA_OU_EDICAO = [
    "nao", "NÃO", "não manda", "nunca", "espera", "espera um pouco", "calma", "muda o texto",
    "troca o oi", "tira a ultima frase", "adiciona um beijo", "cancela", "para", "pare", "talvez",
    "so a primeira", "apenas a primeira", "se for o caso", "ainda nao", "antes me mostra de novo",
    "depois", "sim mas muda", "sim, mas espera", "pode mandar mas tira o oi", "sem enviar",
    "sem mandar nada", "sim mas muda o texto", "manda so a primeira", "muda o ultimo paragrafo",
    "pode seguir mas muda o texto", "pode mandar so a primeira", "manda pra outra pessoa",
    "envia depois", "nao envia", "pode seguir com a parte 2 do plano agora", "sim, mas troca o oi",
    "claro que nao", "com certeza nao", "com certeza, espera", "sem problema mas muda o texto",
    "tudo bem, mas espera", "pode ir mas depois", "pode ir depois", "ok mas espera", "ok, mas muda",
    "negativo", "jamais", "nem pensar", "outra mensagem", "manda outra", "diferente",
    "no", "not now", "dont send", "don't send it", "wait", "stop", "cancel", "change it",
    "edit the text", "yes but change it", "only the first", "maybe", "later", "never", "nope", "no way",
    "send it later", "send it tomorrow", "do not send", "hold on", "ok but wait", "yes, but wait",
    "pero no", "solo la primera", "no lo mandes", "despues", "cambia el texto", "sin enviar",
    "si pero espera", "dale pero cambia",
]

BLOQUEIA_RUIDO = [
    "", "   ", "...", "123", "mensagem", "texto", "por favor", "obrigado", "valeu", "uma vez", "a",
    "frase", "<frase>", "pode mandar para a maria", "manda pra ele", "envia pro joao",
    "sim " + "sim " * 8,
    "ok bora mandar essa mensagem agora mesmo por favor entao",
]

BLOQUEIA_EMOJI = [
    POLEGAR_BAIXO, CRUZ_VERMELHA, PENSANDO, "sim " + POLEGAR_BAIXO, "ok " + CRUZ_VERMELHA, "sim " + RISADA,
    "manda " + FESTA, POLEGAR_CIMA + POLEGAR_BAIXO, "nao " + POLEGAR_CIMA, "sim " + PENSANDO,
    "espera " + POLEGAR_CIMA,
]


# Palavras que, em qualquer idioma, tiram a certeza de uma confirmacao (recusa, edicao, adiamento)
PALAVRAS_QUE_NUNCA_LIBERAM = [
    "nao", "nunca", "mas", "espera", "espere", "calma", "antes", "depois", "muda", "mude", "troca",
    "tira", "tire", "adiciona", "coloca", "ainda", "cancela", "cancelar", "para", "pare", "talvez",
    "so", "apenas", "se", "porem", "sem", "negativo", "jamais", "nem", "altera", "corrige", "edita",
    "no", "not", "dont", "wait", "stop", "hold", "cancel", "change", "edit", "but", "however", "only",
    "if", "later", "never", "nope", "maybe", "pero", "solo", "sin", "despues", "cambia", "quita",
]


class TesteVocabularioDoGuarda(unittest.TestCase):
    def conferir(self, frases, esperado):
        for frase in frases:
            with self.subTest(frase=frase):
                self.assertEqual(guarda.eh_confirmacao(frase), esperado)

    def test_libera_portugues(self):
        self.conferir(LIBERA_PORTUGUES, True)

    def test_libera_ingles(self):
        self.conferir(LIBERA_INGLES, True)

    def test_libera_espanhol(self):
        self.conferir(LIBERA_ESPANHOL, True)

    def test_libera_emoji_que_confirma(self):
        self.conferir(LIBERA_EMOJI, True)

    def test_bloqueia_pergunta_em_qualquer_idioma(self):
        self.conferir(BLOQUEIA_PERGUNTAS, False)

    def test_bloqueia_recusa_edicao_e_adiamento(self):
        self.conferir(BLOQUEIA_RECUSA_OU_EDICAO, False)

    def test_bloqueia_ruido_e_texto_sem_confirmacao(self):
        self.conferir(BLOQUEIA_RUIDO, False)

    def test_bloqueia_emoji_de_recusa_ou_desconhecido(self):
        self.conferir(BLOQUEIA_EMOJI, False)

    def test_fronteira_de_palavras(self):
        self.assertTrue(guarda.eh_confirmacao(" ".join(["sim"] * guarda.MAX_PALAVRAS)))
        self.assertFalse(guarda.eh_confirmacao(" ".join(["sim"] * (guarda.MAX_PALAVRAS + 1))))

    def test_frase_fixa_junto_de_recusa_bloqueia(self):
        for frase in ("sem problema mas espera", "com certeza nao", "go ahead but wait", "de acuerdo pero no"):
            with self.subTest(frase=frase):
                self.assertFalse(guarda.eh_confirmacao(frase))

    def test_marcador_interno_nao_pode_ser_digitado(self):
        # "<frase>" e o marcador interno de frase fixa; digita-lo nao pode contar como confirmacao
        self.assertFalse(guarda.eh_confirmacao("<frase>"))
        self.assertFalse(guarda.eh_confirmacao("<frase> <frase>"))

    def test_todo_confirmador_sozinho_ou_em_dupla_passa_e_nenhuma_recusa_passa(self):
        for palavra in sorted(guarda.CONFIRMADORES - {"<frase>"}):
            with self.subTest(palavra=palavra):
                self.assertTrue(guarda.eh_confirmacao(palavra))
        for palavra in sorted(guarda.RECUSA_OU_EDICAO):
            with self.subTest(recusa=palavra):
                self.assertFalse(guarda.eh_confirmacao(palavra))
                self.assertFalse(guarda.eh_confirmacao("sim " + palavra))

    def test_palavras_que_nunca_podem_liberar_estao_na_lista_de_recusa(self):
        # Lista fixa, escrita aqui: se alguem tirar uma delas do guarda, este teste acusa
        for palavra in PALAVRAS_QUE_NUNCA_LIBERAM:
            with self.subTest(palavra=palavra):
                self.assertIn(palavra, guarda.RECUSA_OU_EDICAO)

    def test_lista_de_recusa_segura_mesmo_se_alguem_trata_a_palavra_como_enchimento(self):
        # A lista de recusa e a segunda barreira: essas palavras ja bloqueiam por serem
        # desconhecidas. Simula o erro de alguem pondo todas como enchimento e exige que a lista
        # de recusa ainda bloqueie. As palavras vem de uma lista fixa do teste (nao da lista do
        # guarda), senao esvaziar a lista do guarda esvaziaria tambem o teste.
        with unittest.mock.patch.object(guarda, "ENCHIMENTO", guarda.ENCHIMENTO | set(PALAVRAS_QUE_NUNCA_LIBERAM)):
            for palavra in PALAVRAS_QUE_NUNCA_LIBERAM:
                with self.subTest(palavra=palavra):
                    self.assertFalse(guarda.eh_confirmacao("sim " + palavra))
                    self.assertFalse(guarda.eh_confirmacao("pode mandar " + palavra))

    def test_nenhuma_palavra_esta_nas_duas_listas_opostas(self):
        confirmam = guarda.CONFIRMADORES | guarda.ENCHIMENTO
        self.assertEqual(confirmam & guarda.RECUSA_OU_EDICAO, set())

    def test_o_arquivo_do_guarda_nao_tem_emoji_nem_caractere_especial(self):
        dados = CAMINHO.read_bytes()
        self.assertEqual([b for b in dados if b > 127], [])


if __name__ == "__main__":
    unittest.main()
