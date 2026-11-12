"""API Gemini REST: um pedido por turno, retries curtos e métricas sem dados sensíveis."""
import json
import time
import urllib.error
import urllib.request

from .config import FALLBACK, MODELO, TENTATIVAS, TIMEOUT, get_api_key


def chamar_modelo(modelo, payload):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={
        "Content-Type": "application/json", "x-goog-api-key": get_api_key(),
    }, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        dados = json.load(resp)
    candidato = (dados.get("candidates") or [{}])[0]
    partes = candidato.get("content", {}).get("parts", [])
    if not partes:
        raise RuntimeError("O Gemini não retornou conteúdo. Reformule a mensagem e tente novamente.")
    return partes


def gemini(payload):
    """Repete erros temporários e troca para o modelo reserva em 404, 429 e sobrecarga (5xx)."""
    modelos = [MODELO] + ([FALLBACK] if FALLBACK and FALLBACK != MODELO else [])
    inicio = time.perf_counter()
    chamadas = 0
    ultimo = None  # código HTTP do último erro, para a mensagem final
    for modelo in modelos:
        for tentativa in range(TENTATIVAS):
            chamadas += 1
            try:
                partes = chamar_modelo(modelo, payload)
                print(f"[ia] modelo={modelo} chamadas={chamadas} duracao={time.perf_counter() - inicio:.2f}s")
                return partes
            except urllib.error.HTTPError as e:
                # Não logar resposta HTTP completa, que pode conter informações sensíveis.
                ultimo = e.code
                if e.code in (401, 403):
                    raise RuntimeError(f"Acesso ao Gemini negado (HTTP {e.code}). Verifique sua chave e permissões.") from None
                if e.code in (404, 429):
                    # Modelo inexistente ou cota esgotada (a cota gratuita é por modelo): tenta o reserva.
                    print(f"[ia] modelo {modelo} retornou HTTP {e.code}; tentando o modelo reserva")
                    break
                if e.code in (500, 502, 503, 504):
                    if tentativa + 1 < TENTATIVAS:
                        time.sleep(.6 * (tentativa + 1))
                        continue
                    print(f"[ia] modelo {modelo} sobrecarregado (HTTP {e.code}); tentando o modelo reserva")
                    break
                raise RuntimeError(f"Gemini recusou a requisição (HTTP {e.code}). Tente novamente.") from None
            except (urllib.error.URLError, TimeoutError) as e:
                raise RuntimeError("Não foi possível acessar o Gemini. Verifique conexão e tente novamente.") from e
    if ultimo == 429:
        raise RuntimeError("Limite de uso do Gemini atingido (429) em todos os modelos configurados. "
                           "Aguarde um minuto ou verifique a cota no Google AI Studio.")
    if ultimo == 404:
        raise RuntimeError("Modelo Gemini não disponível. Configure GEMINI_MODELO no arquivo .env.")
    raise RuntimeError("Os modelos Gemini estão sobrecarregados no momento. Aguarde alguns segundos e reenvie.")


def texto_de(partes):
    return "".join(p.get("text", "") for p in partes if isinstance(p, dict) and not p.get("thought")).strip()


def para_gemini(mensagens):
    return [{"role": m["role"], "parts": [{"text": m["texto"]}]} for m in mensagens]
