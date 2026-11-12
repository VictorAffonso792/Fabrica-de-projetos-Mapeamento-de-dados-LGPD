"""Campos usados no registro de operações de tratamento (LGPD)."""

CAMPOS = [
    ("finalidade", "Finalidade (por que o processo existe)"),
    ("titulares", "Titulares (de quem são os dados)"),
    ("dados_pessoais", "Dados pessoais coletados"),
    ("dados_sensiveis", "Dados sensíveis (saúde, biometria, religião...)"),
    ("justificativa", "Por que cada dado é necessário"),
    ("coleta", "Como os dados são coletados"),
    ("armazenamento", "Onde e como são armazenados"),
    ("retencao", "Por quanto tempo ficam guardados / descarte"),
    ("compartilhamento", "Com quem são compartilhados"),
    ("transferencia_internacional", "Transferência para outro país"),
    ("seguranca", "Medidas de segurança"),
    ("base_legal", "Base legal (sugestão da IA)"),
]

CHAVES = [campo for campo, _ in CAMPOS]
NOMES = dict(CAMPOS)
ABERTURA = "Olá, vamos começar a entrevista."
