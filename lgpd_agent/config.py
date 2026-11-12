"""Configuração da aplicação e leitura de ambiente sem dependências externas."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASTA = ROOT / "entrevistas"
STATIC = ROOT / "static"


def configurar(nome, padrao=""):
    """Prefere variável do sistema e em seguida o .env na raiz do projeto."""
    valor = os.environ.get(nome, "").strip()
    if valor:
        return valor
    arquivo = ROOT / ".env"
    if arquivo.is_file():
        for linha in arquivo.read_text(encoding="utf-8-sig").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            if chave.strip() == nome:
                return valor.strip().strip('"\'')
    return padrao


def get_api_key():
    chave = configurar("GEMINI_API_KEY")
    if not chave or chave == "COLOQUE_SUA_CHAVE_AQUI":
        raise RuntimeError("Chave Gemini não configurada. Crie .env na raiz do projeto com GEMINI_API_KEY=...")
    return chave


def _inteiro(nome, padrao, minimo, maximo):
    """Lê um número do .env; se o valor for inválido, avisa e usa o padrão em vez de travar."""
    bruto = configurar(nome, str(padrao))
    try:
        valor = int(bruto)
    except ValueError:
        print(f"[config] {nome}={bruto!r} não é um número; usando {padrao}.")
        return padrao
    return min(max(valor, minimo), maximo)


PORTA = _inteiro("PORTA", 8000, 1, 65535)
# Modelo oficial estável de baixa latência e saída estruturada.
MODELO = configurar("GEMINI_MODELO", "gemini-3.5-flash-lite")
FALLBACK = configurar("GEMINI_FALLBACK", "gemini-3.5-flash")
TIMEOUT = _inteiro("GEMINI_TIMEOUT", 45, 10, 120)
# Pergunta em linguagem natural formulada pelo Gemini (1 = ligado, 0 = usa o texto fixo do roteiro).
PERGUNTAS_NATURAIS = configurar("PERGUNTAS_NATURAIS", "1") != "0"
TENTATIVAS = 2
