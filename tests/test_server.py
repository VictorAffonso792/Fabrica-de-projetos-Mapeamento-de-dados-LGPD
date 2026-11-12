"""Testa respostas HTTP locais, sem chamar a API Gemini."""
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from lgpd_agent import server
from test_mapping import entrevista


class TestServidorHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servidor = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.servidor.server_port}"
        cls.thread = threading.Thread(target=cls.servidor.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.thread.join(timeout=2)

    def solicitar(self, rota, metodo="GET", body=None):
        if body is not None and not isinstance(body, bytes):
            body = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.base + rota, data=body, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=3) as resposta:
                return resposta.status, resposta.read().decode("utf-8"), resposta.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8"), e.headers

    def test_index_css_js_modulares(self):
        """Verifica os pontos de entrada e os módulos independentes no HTTP."""
        expected = (
            ("/", 'lang="pt-BR"', "text/html"),
            ("/static/styles.css", 'css/base.css', "text/css"),
            ("/static/css/base.css", '--navy: #243155', "text/css"),
            ("/static/css/responsive.css", '@media (max-width:760px)', "text/css"),
            ("/static/app.js", 'js/main.js', "application/javascript"),
            ("/static/js/main.js", 'async function init()', "application/javascript"),
            ("/static/js/views/mapping.js", 'renderProcesses', "application/javascript"),
        )
        for rota, trecho, mime in expected:
            with self.subTest(rota=rota):
                status, conteudo, headers = self.solicitar(rota)
                self.assertEqual(status, 200)
                self.assertIn(trecho, conteudo)
                self.assertIn(mime, headers["Content-Type"])

    def test_arquivos_privados_nao_sao_expostos(self):
        for rota in ("/.env", "/static/js/../../.env", "/static/not-found.py"):
            with self.subTest(rota=rota):
                status, _, _ = self.solicitar(rota)
                self.assertEqual(status, 404)

    def test_config_json(self):
        status, texto, headers = self.solicitar("/api/config")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(texto)["campos"]), 12)
        self.assertIn("application/json", headers["Content-Type"])

    def test_criar_entrevista_mock(self):
        e = entrevista()
        with patch.object(server, "criar", return_value=(e, None)):
            status, texto, _ = self.solicitar("/api/entrevistas", "POST", {})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(texto)["entrevista"]["id"], e["id"])

    def test_json_invalido(self):
        status, texto, _ = self.solicitar("/api/entrevistas", "POST", b"{")
        self.assertEqual(status, 400)
        self.assertIn("JSON inválido", texto)

    def test_rota_inexistente(self):
        status, texto, _ = self.solicitar("/nao-existe")
        self.assertEqual(status, 404)
        self.assertIn("Não encontrado", texto)


if __name__ == "__main__":
    unittest.main()
