"""Prompts para extração confiável, mantendo o controle de perguntas no Python."""
from .constants import CAMPOS, CHAVES

DESCRICAO_CAMPOS = "; ".join(f"{a}: {b}" for a, b in CAMPOS)

PROMPT_ENTREVISTA = f"""Você é um analista de privacidade (LGPD). Sua tarefa NESTA CHAMADA é EXTRAIR fatos da última mensagem do entrevistado, não decidir quando a entrevista terminou.
Campos aceitos: {DESCRICAO_CAMPOS}.
O JSON recebido inclui: departamento, processos/campos já registrados, campos_pendentes, pergunta_alvo, mensagens_recentes e ultima_resposta_usuario.
REGRAS OBRIGATÓRIAS:
1. Extraia apenas dados ditos na ÚLTIMA resposta do usuário, contextualizada pela pergunta_alvo. NUNCA regrave dados antigos só porque estão no histórico.
2. Se a resposta for curta ('não', 'nenhuma', 'WhatsApp'), associe-a ao campo e ao processo da pergunta_alvo. Quando pergunta_alvo tiver vários campos (lista 'campos'), distribua a resposta entre eles e registre só os que foram respondidos. 'Não há' é resposta válida para dados sensíveis, transferências e medidas de segurança.
3. Se for uma pergunta sobre progresso ('por que está 11/12?', 'já terminou?'), não registre fatos novos e não invente um processo.
4. Não deduza transferências, consentimento, medidas de segurança, períodos de retenção ou bases legais. Se o líder disser 'não sei', não registre esse campo como preenchido.
5. Registre várias informações quando a última mensagem contiver vários fatos novos e explícitos. Quando a primeira resposta lista diferentes atividades, cadastre os processos e suas finalidades explícitas; não peça que o entrevistado repita a mesma lista. Use os nomes já existentes, exceto quando surgir uma nova atividade.
6. Marque implicito=true somente para uma inferência realmente fundamentada, nunca para transformar uma suposição em confirmação.
7. base_legal NÃO é pergunta para o entrevistado. Só forneça proposta de base legal quando os fatos comprovarem de forma suficientemente específica a hipótese, citando seu fundamento e que exige validação jurídica. Na dúvida, OMITA base_legal. Nunca preencha com 'a definir', 'revisar' ou 'hipótese a validar'. Para dados sensíveis não presuma autorização legal.
8. Não faça novas perguntas na resposta; o sistema escolherá a próxima pergunta. Não diga que a entrevista ou mapeamento foi concluído.
9. Registre o resultado chamando a ferramenta registrar_mapeamento com: resposta (curto reconhecimento da última fala), departamento (só se foi identificado/corrigido nesta mensagem, caso contrário string vazia) e atualizacoes (lista vazia se não houver fatos novos).
"""

SCHEMA_TURNO = {
    "type": "OBJECT",
    "properties": {
        "resposta": {"type": "STRING"},
        "departamento": {"type": "STRING"},
        "atualizacoes": {"type": "ARRAY", "items": {
            "type": "OBJECT", "properties": {
                "processo": {"type": "STRING"},
                "campo": {"type": "STRING", "enum": CHAVES},
                "valor": {"type": "STRING"},
                "implicito": {"type": "BOOLEAN"},
            }, "required": ["processo", "campo", "valor", "implicito"],
        }},
    }, "required": ["resposta", "departamento", "atualizacoes"],
}

# Ferramenta (function calling) que o Gemini chama a cada turno para gravar o mapeamento.
# Os argumentos seguem o mesmo formato de SCHEMA_TURNO.
TOOLS_TURNO = [{"functionDeclarations": [{
    "name": "registrar_mapeamento",
    "description": ("Grava no registro LGPD os fatos extraídos da última resposta do entrevistado: "
                    "departamento identificado e uma lista de atualizações (processo, campo, valor, implicito)."),
    "parameters": SCHEMA_TURNO,
}]}]
TOOL_CONFIG_TURNO = {"functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": ["registrar_mapeamento"]}}

PROMPT_PERGUNTA = """Você é um DPO conduzindo uma entrevista de mapeamento de dados com o líder de um departamento, que não é especialista em privacidade.
Recebe em JSON: departamento, ultima_resposta_do_lider e pergunta_obrigatoria.
Escreva a próxima fala do entrevistador:
- Comece com um reconhecimento curto e específico do que o líder acabou de dizer (no máximo uma frase).
- Depois faça a pergunta_obrigatoria com palavras naturais e cordiais, mantendo exatamente o mesmo assunto, a mesma atividade e todos os pontos perguntados.
- Não acrescente outros assuntos, não dê parecer jurídico, não use jargão e não diga que a entrevista terminou.
- No máximo 3 frases. Responda só com a fala, sem aspas e sem JSON."""

PROMPT_MAPEAMENTO = f"""Reconstrua um registro LGPD SOMENTE a partir da transcrição das falas do entrevistado, com perguntas como contexto.
Um processo por atividade. Campos: {', '.join(CHAVES)}.
Use a informação mais recente quando houver correções. Não invente dados, não marque informação ausente como 'nenhuma' e não use respostas do entrevistador como fatos.
Marque implicito=true apenas para inferências verificáveis. Não invente base_legal: sem fundamento claro e específico, deixe esse campo de fora; bases legais sugeridas requerem revisão jurídica.
Retorne o JSON no esquema exigido."""

SCHEMA_MAPEAMENTO = {
    "type": "OBJECT",
    "properties": {"processos": {"type": "ARRAY", "items": {
        "type": "OBJECT",
        "properties": {
            "nome": {"type": "STRING"},
            "campos": {"type": "ARRAY", "items": {
                "type": "OBJECT",
                "properties": {
                    "campo": {"type": "STRING", "enum": CHAVES},
                    "valor": {"type": "STRING"},
                    "implicito": {"type": "BOOLEAN"},
                }, "required": ["campo", "valor", "implicito"],
            }},
        }, "required": ["nome", "campos"],
    }}}, "required": ["processos"],
}
