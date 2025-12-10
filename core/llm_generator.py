# core/llm_generator.py
import json
from typing import List, Optional
from google import genai
from google.genai.errors import APIError
from api.models import QuestionIn, QuestionInternal

GENERATION_MODEL = 'gemini-2.5-flash' 

class LLMQuestionGenerator:
    """Responsável por gerar novas questões ENEM no formato JSON."""
    
    def __init__(self):
        try:
            self.client = genai.Client()
        except Exception as e:
            print(f"ERRO: Cliente GenAI não pôde ser inicializado. Verifique GEMINI_API_KEY. {e}")
            raise

    def generate_questions(self, topic: str, count: int, existing_statements: List[str] = None) -> List[QuestionInternal]:
        """Gera 'count' novas questões ENEM sobre o 'topic', evitando 'existing_statements'."""
        
        json_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string", "description": "O enunciado longo e contextualizado."},
                    "alternatives": {"type": "array", "items": {"type": "string"}, "description": "Lista de 5 opções."},
                    "correct_answer": {"type": "string", "enum": ["A", "B", "C", "D", "E"], "description": "A letra da resposta correta."},
                },
                "required": ["statement", "alternatives", "correct_answer"],
            },
        }

        system_instruction = (
            "Você é um especialista em elaboração de itens para o Exame Nacional do Ensino Médio (ENEM). "
            "Sua tarefa é gerar APENAS uma lista de objetos JSON. "
            "As questões devem ter: "
            "1. Enunciado longo, contextualizado e interdisciplinar. "
            "2. Cinco alternativas (A, B, C, D, E). "
            "3. A alternativa correta deve ser indicada no campo 'correct_answer'."
        )

        user_prompt = (
            f"Gere exatamente {count} questões no estilo ENEM sobre o seguinte tópico: **{topic}**. "
            "Garanta que o conteúdo seja relevante para o ensino médio brasileiro e mantenha alta fidelidade ao estilo do exame. "
        )
        
        if existing_statements:
            user_prompt += "Mantenha a originalidade; não gere questões que sejam semanticamente iguais aos seguintes enunciados:\n"
            user_prompt += "\n---\n".join(existing_statements[:5])
            
        try:
            response = self.client.models.generate_content(
                model=GENERATION_MODEL,
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=json_schema,
                    temperature=0.7
                ),
            )
            
            generated_data = json.loads(response.text)
            
            questions = []
            for item in generated_data:
                q_in = QuestionIn(**item, topic=topic)
                questions.append(QuestionInternal(
                    statement=q_in.statement,
                    alternatives=q_in.alternatives,
                    correct_answer=q_in.correct_answer,
                    topic=topic,
                    source="GENERATED"
                ))
            
            return questions

        except (APIError, json.JSONDecodeError, KeyError) as e:
            print(f"Erro na geração do LLM ou parsing: {e}")
            return []

llm_generator = LLMQuestionGenerator()