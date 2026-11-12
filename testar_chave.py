"""Teste rápido da chave e do modelo Gemini: python testar_chave.py"""
from lgpd_agent.config import FALLBACK, MODELO, get_api_key
from lgpd_agent.gemini import gemini, texto_de

chave = get_api_key()
print(f"Chave lida do .env: {chave[:6]}... | modelo: {MODELO} | reserva: {FALLBACK}")
try:
    resposta = texto_de(gemini({"contents": [{"role": "user", "parts": [{"text": "Responda apenas: funcionou"}]}]}))
    print("OK! Resposta do Gemini:", resposta)
except RuntimeError as erro:
    print("FALHOU:", erro)
