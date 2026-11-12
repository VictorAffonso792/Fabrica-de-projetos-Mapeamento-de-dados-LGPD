"""Servidor HTTP local para a API e os arquivos da interface.

Rotas /api/... atendem entrevistas; /static/... entrega CSS e módulos JS.
Não disponibiliza arquivos .env, dados pessoais nem arquivos fora de static/.
"""
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import PASTA, PORTA, STATIC
from .constants import CAMPOS
from .report import markdown
from .service import acao, criar, trava_entrevista
from .storage import carregar, excluir, listar

TIPOS_ESTATICOS = {".css": "text/css", ".js": "application/javascript"}


def arquivo_publico(caminho):
    """Retorna um arquivo permitido da interface; impede navegação fora da pasta."""
    if caminho == "/":
        return STATIC / "index.html", "text/html"
    if not caminho.startswith("/static/"):
        return None
    relativo = caminho[len("/static/"):]
    arquivo = (STATIC / relativo).resolve()
    if (arquivo != STATIC.resolve() and
            STATIC.resolve() not in arquivo.parents):
        return None
    tipo = TIPOS_ESTATICOS.get(arquivo.suffix)
    if not tipo or not arquivo.is_file():
        return None
    return arquivo, tipo


class Handler(BaseHTTPRequestHandler):
    def responder(self, status, corpo, tipo="application/json", baixar=None):
        dados = corpo.encode("utf-8") if isinstance(corpo, str) else json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{tipo}; charset=utf-8")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        if baixar:
            self.send_header("Content-Disposition", f'attachment; filename="{baixar}"')
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def rotear(self, metodo):
        try:
            caminho = self.path.split("?", 1)[0]
            publico = arquivo_publico(caminho) if metodo == "GET" else None
            if publico:
                arquivo, tipo = publico
                return self.responder(200, arquivo.read_text(encoding="utf-8"), tipo)
            if metodo == "GET" and caminho == "/api/config":
                return self.responder(200, {"campos": CAMPOS})
            partes = [p for p in caminho.split("/") if p]
            if partes[:2] != ["api", "entrevistas"]:
                raise FileNotFoundError(caminho)
            tamanho = int(self.headers.get("Content-Length") or 0)
            if tamanho < 0 or tamanho > 1024 * 1024:
                return self.responder(413, {"erro": "Requisição muito grande."})
            try:
                corpo = json.loads(self.rfile.read(tamanho) or b"{}") if tamanho else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self.responder(400, {"erro": "JSON inválido."})
            if not isinstance(corpo, dict):
                return self.responder(400, {"erro": "Corpo deve ser um objeto JSON."})
            resto = partes[2:]
            if metodo == "GET" and not resto:
                return self.responder(200, listar())
            if metodo == "POST" and not resto:
                ent, erro = criar()
                return self.responder(200, {"entrevista": ent, "erro": erro})
            if len(resto) == 1 and metodo == "GET":
                with trava_entrevista(resto[0]):
                    return self.responder(200, {"entrevista": carregar(resto[0])})
            if metodo == "GET" and len(resto) == 2 and resto[1] == "md":
                with trava_entrevista(resto[0]):
                    ent = carregar(resto[0])
                return self.responder(200, markdown(ent), "text/markdown", f"{ent['id']}.md")
            if metodo == "DELETE" and len(resto) == 1:
                with trava_entrevista(resto[0]):
                    excluir(resto[0])
                return self.responder(200, {"ok": True})
            if metodo == "POST" and len(resto) == 2:
                return self.responder(200, {"entrevista": acao(resto[0], resto[1], corpo)})
            raise FileNotFoundError(caminho)
        except FileNotFoundError:
            self.responder(404, {"erro": "Não encontrado."})
        except ValueError as e:
            # Mensagens de ValueError são escritas pelo próprio sistema para o usuário.
            self.responder(400, {"erro": str(e)})
        except (KeyError, IndexError, TypeError) as e:
            print(f"[erro] requisição inválida: {type(e).__name__}")
            self.responder(400, {"erro": "Dados da requisição incompletos ou inválidos."})
        except Exception as e:
            print(f"[erro] tipo={type(e).__name__}")
            self.responder(500, {"erro": str(e) if isinstance(e, RuntimeError) else "Erro interno. Confira o terminal."})

    def do_GET(self):
        self.rotear("GET")

    def do_POST(self):
        self.rotear("POST")

    def do_DELETE(self):
        self.rotear("DELETE")

    def log_message(self, *args):
        """Oculta log redundante de requisições; erros seguem no terminal."""
        pass


def main():
    porta = PORTA
    while True:
        try:
            servidor = ThreadingHTTPServer(("127.0.0.1", porta), Handler)
            break
        except OSError:
            porta += 1
    url = f"http://localhost:{porta}"
    print(f"Agente rodando em {url}")
    print(f"Entrevistas salvas em: {PASTA}")
    print("Para parar: Ctrl+C")
    timer = threading.Timer(1, lambda: webbrowser.open(url))
    timer.daemon = True
    timer.start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")
    finally:
        servidor.server_close()
