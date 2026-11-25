package main

import (
	"crypto/subtle"
	"fmt"
	"net"
	"net/http"
	"os"
	"strings"
)

// Variavel de ambiente com a senha da API da bridge. Quando definida, toda chamada precisa
// mandar "Authorization: Bearer <senha>". Sem ela, a API fica aberta (so para uso local).
const tokenEnv = "WHATSAPP_BRIDGE_TOKEN"

// requireToken protege a API com uma senha. Com a senha vazia, nao faz nada.
// A comparacao e em tempo constante, para a resposta nao revelar quantas letras acertaram.
func requireToken(token string, next http.Handler) http.Handler {
	if token == "" {
		return next
	}
	esperado := []byte("Bearer " + token)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		recebido := []byte(strings.TrimSpace(r.Header.Get("Authorization")))
		if subtle.ConstantTimeCompare(recebido, esperado) != 1 {
			w.Header().Set("WWW-Authenticate", "Bearer")
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// tokenDaAmbiente le a senha do ambiente, sem espacos nas pontas.
func tokenDaAmbiente() string {
	return strings.TrimSpace(os.Getenv(tokenEnv))
}

// Variavel de ambiente com o endereco em que a API escuta. O padrao e o proprio computador.
const enderecoEnv = "WHATSAPP_BRIDGE_ADDR"

// enderecoDeEscuta decide onde a API escuta. Fora do loopback (por exemplo 0.0.0.0, dentro de um
// container) a senha e obrigatoria: a API envia mensagens, entao nunca pode ficar aberta na rede.
func enderecoDeEscuta(host string, porta int, token string) (string, error) {
	host = strings.TrimSpace(host)
	if host == "" {
		host = "127.0.0.1"
	}
	if !ehLoopback(host) && token == "" {
		return "", fmt.Errorf("%s=%s exige a senha em %s: a API envia mensagens e nao pode ficar aberta na rede", enderecoEnv, host, tokenEnv)
	}
	return net.JoinHostPort(host, fmt.Sprintf("%d", porta)), nil
}

func ehLoopback(host string) bool {
	if host == "localhost" {
		return true
	}
	ip := net.ParseIP(strings.Trim(host, "[]"))
	return ip != nil && ip.IsLoopback()
}
