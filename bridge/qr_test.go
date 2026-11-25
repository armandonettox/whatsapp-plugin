package main

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestSalvarQRGravaPNGValido(t *testing.T) {
	caminho := filepath.Join(t.TempDir(), "qr.png")
	if err := salvarQR("2@exemplo,codigo,de,teste", caminho); err != nil {
		t.Fatal(err)
	}
	dados, err := os.ReadFile(caminho)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.HasPrefix(dados, []byte("\x89PNG\r\n\x1a\n")) {
		t.Fatalf("o arquivo nao comeca como PNG: %q", dados[:8])
	}
	if len(dados) < 200 {
		t.Fatalf("PNG pequeno demais: %d bytes", len(dados))
	}
	if _, err := os.Stat(caminho + ".tmp"); !os.IsNotExist(err) {
		t.Fatal("o arquivo temporario deveria ter sido renomeado")
	}
}

func TestSalvarQRSubstituiOCodigoAnterior(t *testing.T) {
	caminho := filepath.Join(t.TempDir(), "qr.png")
	if err := salvarQR("primeiro-codigo", caminho); err != nil {
		t.Fatal(err)
	}
	antes, _ := os.ReadFile(caminho)
	if err := salvarQR("segundo-codigo-diferente", caminho); err != nil {
		t.Fatal(err)
	}
	depois, _ := os.ReadFile(caminho)
	if bytes.Equal(antes, depois) {
		t.Fatal("o QR novo deveria trocar a imagem")
	}
}

func TestApagarQRRemoveOArquivo(t *testing.T) {
	caminho := filepath.Join(t.TempDir(), "qr.png")
	if err := salvarQR("codigo", caminho); err != nil {
		t.Fatal(err)
	}
	apagarQR(caminho)
	if _, err := os.Stat(caminho); !os.IsNotExist(err) {
		t.Fatal("o QR deveria ter sido apagado")
	}
	apagarQR(caminho) // apagar de novo nao pode dar erro
}

func TestCaminhoDoQRUsaAPastaDaVariavel(t *testing.T) {
	t.Setenv("WHATSAPP_STORE_DIR", filepath.Join("x", "pasta"))
	if got, want := caminhoDoQR(), filepath.Join("x", "pasta", "qr.png"); got != want {
		t.Fatalf("got %q, want %q", got, want)
	}
	t.Setenv("WHATSAPP_STORE_DIR", "")
	if got, want := caminhoDoQR(), filepath.Join("..", "data", "store", "qr.png"); got != want {
		t.Fatalf("got %q, want %q", got, want)
	}
}

func TestPastaDoStoreEOsEnderecosDosBancos(t *testing.T) {
	t.Setenv("WHATSAPP_STORE_DIR", "")
	if got, want := pastaDoStore(), filepath.Join("..", "data", "store"); got != want {
		t.Fatalf("got %q, want %q", got, want)
	}
	if got, want := uriDoBanco("messages.db"), "file:../data/store/messages.db?_foreign_keys=on"; got != want {
		t.Fatalf("got %q, want %q", got, want)
	}
	pasta := t.TempDir()
	t.Setenv("WHATSAPP_STORE_DIR", pasta)
	if got, want := uriDoBanco("whatsapp.db"), "file:"+filepath.ToSlash(filepath.Join(pasta, "whatsapp.db"))+"?_foreign_keys=on"; got != want {
		t.Fatalf("got %q, want %q", got, want)
	}
}

func TestBancoAbreNaPastaDaVariavel(t *testing.T) {
	pasta := t.TempDir()
	t.Setenv("WHATSAPP_STORE_DIR", pasta)
	loja, err := NewMessageStore()
	if err != nil {
		t.Fatal(err)
	}
	defer loja.Close()
	if _, err := os.Stat(filepath.Join(pasta, "messages.db")); err != nil {
		t.Fatalf("o banco deveria estar na pasta da variavel: %v", err)
	}
}
