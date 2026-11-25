package main

import (
	"os"
	"path/filepath"
)

// pastaDoStore e onde ficam os bancos e a sessao: WHATSAPP_STORE_DIR, ou ../data/store a partir
// da pasta da bridge. E a mesma variavel que o servidor MCP e os scripts das skills leem.
func pastaDoStore() string {
	if pasta := os.Getenv("WHATSAPP_STORE_DIR"); pasta != "" {
		return pasta
	}
	return filepath.Join("..", "data", "store")
}

// uriDoBanco monta o endereco "file:" do SQLite para um banco dentro da pasta do store.
func uriDoBanco(nome string) string {
	return "file:" + filepath.ToSlash(filepath.Join(pastaDoStore(), nome)) + "?_foreign_keys=on"
}
