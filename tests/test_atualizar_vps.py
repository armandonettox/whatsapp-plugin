"""Testes da acao `atualizar` do container/instalar-vps.sh, com git local e podman/systemctl de mentira.

Um repositorio "origin" local tem as tags v0.0.1 e v0.0.2 (a segunda muda a tag das imagens). O
script e rodado a partir de um clone dele. Nada e instalado de verdade.
Travas: so atualiza para a ultima release e sem misturar historicos, so com o "sim", recusa
alteracoes locais, nao toca na senha, e refaz as imagens com a tag nova.
"""

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_instalar_vps as base  # noqa: E402

RAIZ = base.RAIZ
BASH = base.BASH
TEM_GIT = shutil.which("git") is not None
AMBIENTE_GIT = {"GIT_AUTHOR_NAME": "Teste", "GIT_AUTHOR_EMAIL": "teste@example.com",
                "GIT_COMMITTER_NAME": "Teste", "GIT_COMMITTER_EMAIL": "teste@example.com"}


def git(pasta, *args):
    env = dict(os.environ)
    env.update(AMBIENTE_GIT)
    r = subprocess.run(["git", "-C", str(pasta), *args], capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0, (args, r.stderr)
    return r.stdout.strip()


@unittest.skipUnless(BASH and TEM_GIT, "precisa do bash e do git")
class AtualizarNaVps(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        b = Path(self.tmp.name)
        self.casa, self.bin, self.estado = b / "casa", b / "bin", b / "estado"
        for p in (self.casa, self.bin, self.estado):
            p.mkdir()
        self.log = b / "log.txt"
        self.log.write_text("")
        for nome, corpo in (("podman", base.PODMAN_FALSO), ("systemctl", base.SYSTEMCTL_FALSO)):
            f = self.bin / nome
            f.write_text(corpo, newline="\n")
            f.chmod(f.stat().st_mode | stat.S_IXUSR)
        self.quadlet = self.casa / ".config" / "containers" / "systemd"

        self.origin, self.autor, self.clone = b / "origin.git", b / "autor", b / "instalado"
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(self.origin)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.autor)], check=True)
        git(self.autor, "remote", "add", "origin", str(self.origin))
        shutil.copytree(RAIZ / "container", self.autor / "container", ignore=shutil.ignore_patterns(".env"))
        (self.autor / "container" / "instalar-vps.sh").chmod(0o755)
        for arquivo in (self.autor / "container" / "quadlet").glob("whatsapp-*.container"):
            texto = arquivo.read_text(encoding="utf-8")
            arquivo.write_text(self.com_tag(texto, "0.0.1"), encoding="utf-8", newline="\n")
        git(self.autor, "add", "-A")
        git(self.autor, "commit", "-q", "-m", "v0.0.1")
        git(self.autor, "tag", "v0.0.1")
        git(self.autor, "push", "-q", "origin", "main", "--tags")
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.clone)], check=True)

    @staticmethod
    def com_tag(texto, tag):
        linhas = []
        for linha in texto.splitlines():
            if linha.startswith("Image="):
                linha = linha.rsplit(":", 1)[0] + ":" + tag
            linhas.append(linha)
        return "\n".join(linhas) + "\n"

    def publicar_v002(self):
        for arquivo in (self.autor / "container" / "quadlet").glob("whatsapp-*.container"):
            arquivo.write_text(self.com_tag(arquivo.read_text(encoding="utf-8"), "0.0.2"), encoding="utf-8", newline="\n")
        git(self.autor, "add", "-A")
        git(self.autor, "commit", "-q", "-m", "v0.0.2")
        git(self.autor, "tag", "v0.0.2")
        git(self.autor, "push", "-q", "origin", "main", "--tags")

    def rodar(self, *args, pasta=None):
        env = dict(os.environ)
        env.update({"HOME": str(self.casa), "FAKE_LOG": str(self.log), "FAKE_STATE": str(self.estado),
                    "PATH": str(self.bin) + os.pathsep + env["PATH"]})
        script = (pasta or self.clone) / "container" / "instalar-vps.sh"
        return subprocess.run([BASH, str(script), *args], capture_output=True, text=True, encoding="utf-8",
                              env=env, timeout=120, stdin=subprocess.DEVNULL)

    def log_texto(self):
        return self.log.read_text()

    def test_atualiza_para_a_ultima_release_e_refaz_as_imagens_com_a_tag_nova(self):
        self.publicar_v002()
        r = self.rodar("atualizar", "--sim")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(git(self.clone, "describe", "--tags", "--exact-match"), "v0.0.2")
        log = self.log_texto()
        self.assertIn("-t localhost/whatsapp-bridge:0.0.2 ", log + " ")
        self.assertIn("-t localhost/whatsapp-mcp:0.0.2 ", log + " ")
        for nome in ("whatsapp-bridge.container", "whatsapp-mcp.container"):
            self.assertIn(":0.0.2", (self.quadlet / nome).read_text())
        self.assertIn("systemctl --user restart whatsapp-bridge.service", log)
        self.assertIn("systemctl --user restart whatsapp-mcp.service", log)
        self.assertIn("nao precisa recadastrar", r.stdout)

    def test_nao_toca_na_senha_nem_no_openbot(self):
        (self.estado / "segredo").write_text("senha-antiga-de-teste")
        self.quadlet.mkdir(parents=True)
        (self.quadlet / "openbot.container").write_text("[Container]\nImage=x\n")
        self.publicar_v002()
        self.rodar("atualizar", "--sim")
        self.assertEqual((self.estado / "segredo").read_text(), "senha-antiga-de-teste")
        self.assertEqual((self.quadlet / "openbot.container").read_text(), "[Container]\nImage=x\n")
        self.assertNotIn("secret create", self.log_texto())
        self.assertNotIn("openbot", self.log_texto())

    def test_ja_na_ultima_release_nao_constroi_nem_reinicia(self):
        r = self.rodar("atualizar", "--sim")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Ja esta na ultima release", r.stdout)
        self.assertEqual(self.log_texto(), "")

    def test_sem_o_sim_e_sem_terminal_nao_altera_nada(self):
        self.publicar_v002()
        antes = git(self.clone, "rev-parse", "HEAD")
        r = self.rodar("atualizar")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(git(self.clone, "rev-parse", "HEAD"), antes)
        self.assertNotIn("build", self.log_texto())
        self.assertNotIn("restart", self.log_texto())

    def test_alteracao_local_recusa_antes_de_qualquer_coisa(self):
        self.publicar_v002()
        (self.clone / "container" / "compose.yaml").write_text("# remendo\n")
        antes = git(self.clone, "rev-parse", "HEAD")
        r = self.rodar("atualizar", "--sim")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("alteracoes locais", r.stderr)
        self.assertEqual(git(self.clone, "rev-parse", "HEAD"), antes)
        self.assertEqual(self.log_texto(), "")

    def test_historico_divergente_nao_e_misturado(self):
        self.publicar_v002()
        (self.clone / "extra.txt").write_text("so meu")
        git(self.clone, "add", "extra.txt")
        git(self.clone, "commit", "-q", "-m", "commit local")
        antes = git(self.clone, "rev-parse", "HEAD")
        r = self.rodar("atualizar", "--sim")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(git(self.clone, "rev-parse", "HEAD"), antes)
        self.assertNotIn("restart", self.log_texto())

    def test_pasta_sem_git_recusa_com_orientacao(self):
        copia = Path(self.tmp.name) / "sem-git"
        shutil.copytree(self.clone, copia, ignore=shutil.ignore_patterns(".git"))
        r = self.rodar("atualizar", "--sim", pasta=copia)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("clone do git", r.stderr)


if __name__ == "__main__":
    unittest.main()
