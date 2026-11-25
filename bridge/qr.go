package main

import (
	"os"
	"path/filepath"

	"rsc.io/qr"
)

// caminhoDoQR e onde a bridge grava o QR de pareamento como imagem. Quem usa o plugin por um
// chat (sem terminal) abre ou anexa esse arquivo em vez de ler o desenho em texto do log.
func caminhoDoQR() string {
	return filepath.Join(pastaDoStore(), "qr.png")
}

// salvarQR grava o codigo como PNG. O arquivo e escrito inteiro em um temporario e depois
// renomeado, para quem le nunca pegar uma imagem pela metade.
func salvarQR(codigo, caminho string) error {
	imagem, err := qr.Encode(codigo, qr.M)
	if err != nil {
		return err
	}
	imagem.Scale = 10
	dados := imagem.PNG()
	temporario := caminho + ".tmp"
	if err := os.WriteFile(temporario, dados, 0o600); err != nil {
		return err
	}
	return os.Rename(temporario, caminho)
}

// apagarQR remove a imagem depois do pareamento ou da desistencia. O QR e um codigo de acesso
// a conta enquanto vale, entao nao fica guardado.
func apagarQR(caminho string) {
	_ = os.Remove(caminho)
	_ = os.Remove(caminho + ".tmp")
}
