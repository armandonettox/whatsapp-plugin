package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func respostaDe(t *testing.T, token, cabecalho string) (int, bool) {
	t.Helper()
	chamado := false
	proximo := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		chamado = true
		w.WriteHeader(http.StatusOK)
	})
	req := httptest.NewRequest(http.MethodPost, "/api/send", nil)
	if cabecalho != "" {
		req.Header.Set("Authorization", cabecalho)
	}
	gravador := httptest.NewRecorder()
	requireToken(token, proximo).ServeHTTP(gravador, req)
	return gravador.Code, chamado
}

func TestSemSenhaDefinidaAApiFicaAberta(t *testing.T) {
	codigo, chamado := respostaDe(t, "", "")
	if codigo != http.StatusOK || !chamado {
		t.Fatalf("sem senha definida a chamada devia passar, veio %d (chamado=%v)", codigo, chamado)
	}
}

func TestComSenhaDefinidaChamadaCorretaPassa(t *testing.T) {
	codigo, chamado := respostaDe(t, "segredo-de-teste", "Bearer segredo-de-teste")
	if codigo != http.StatusOK || !chamado {
		t.Fatalf("chamada com a senha certa devia passar, veio %d (chamado=%v)", codigo, chamado)
	}
}

func TestComSenhaDefinidaChamadaErradaOuSemSenhaEBarrada(t *testing.T) {
	casos := map[string]string{
		"sem cabecalho":       "",
		"senha errada":        "Bearer outra-senha",
		"senha parecida":      "Bearer segredo-de-teste-",
		"sem a palavra":       "segredo-de-teste",
		"outro esquema":       "Basic segredo-de-teste",
		"so a palavra":        "Bearer",
		"maiuscula diferente": "Bearer SEGREDO-DE-TESTE",
	}
	for nome, cabecalho := range casos {
		t.Run(nome, func(t *testing.T) {
			codigo, chamado := respostaDe(t, "segredo-de-teste", cabecalho)
			if codigo != http.StatusUnauthorized || chamado {
				t.Fatalf("devia barrar com 401 e nao chamar o proximo, veio %d (chamado=%v)", codigo, chamado)
			}
		})
	}
}

func TestEspacosNasPontasDoCabecalhoSaoIgnorados(t *testing.T) {
	codigo, _ := respostaDe(t, "segredo-de-teste", "  Bearer segredo-de-teste  ")
	if codigo != http.StatusOK {
		t.Fatalf("espacos nas pontas nao deviam importar, veio %d", codigo)
	}
}

func TestTokenDaAmbienteTiraEspacos(t *testing.T) {
	t.Setenv(tokenEnv, "  abc123  ")
	if got := tokenDaAmbiente(); got != "abc123" {
		t.Fatalf("esperava abc123, veio %q", got)
	}
	t.Setenv(tokenEnv, "")
	if got := tokenDaAmbiente(); got != "" {
		t.Fatalf("esperava vazio, veio %q", got)
	}
}

func TestEnderecoDeEscuta(t *testing.T) {
	casos := []struct {
		nome, host, token, esperado string
		erro                        bool
	}{
		{"padrao e o proprio computador", "", "", "127.0.0.1:8081", false},
		{"loopback explicito", "127.0.0.1", "", "127.0.0.1:8081", false},
		{"localhost", "localhost", "", "localhost:8081", false},
		{"ipv6 local", "::1", "", "[::1]:8081", false},
		{"fora do computador sem senha", "0.0.0.0", "", "", true},
		{"rede privada sem senha", "10.0.0.5", "", "", true},
		{"ipv6 qualquer sem senha", "::", "", "", true},
		{"fora do computador com senha", "0.0.0.0", "segredo", "0.0.0.0:8081", false},
		{"espacos sao ignorados", "  127.0.0.1 ", "", "127.0.0.1:8081", false},
	}
	for _, c := range casos {
		t.Run(c.nome, func(t *testing.T) {
			got, err := enderecoDeEscuta(c.host, 8081, c.token)
			if c.erro {
				if err == nil {
					t.Fatalf("devia recusar, mas aceitou %q", got)
				}
				return
			}
			if err != nil || got != c.esperado {
				t.Fatalf("esperava %q, veio %q (erro %v)", c.esperado, got, err)
			}
		})
	}
}
