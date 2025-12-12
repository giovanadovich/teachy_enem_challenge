# collect_data.py (Versão Final com Filtro de Imagem e Balanceamento de Tópicos)

import requests
import json
import os
import re # Necessário para a limpeza de texto
from tqdm import tqdm
from typing import List, Dict, Any, Optional

# --- Configurações ---
API_BASE_URL = "https://api.enem.dev/v1" 
OUTPUT_FILE = "data/initial_enem_data.json"

# Adicionado mais anos para maior chance de balanceamento e coleta de 100 itens
YEARS_TO_COLLECT = [2022, 2021, 2020, 2019, 2018] 
TOTAL_QUESTION_TARGET = 100 
LIMIT_PER_REQUEST = 30 

# Tópicos alvo (usando os valores que a API retorna)
TARGET_TOPICS = [
    "linguagens", 
    "ciencias-natureza", 
    "ciencias-humanas", 
    "matematica"
]
# Número ideal de questões por tópico (100 / 4 = 25)
TARGET_PER_TOPIC = TOTAL_QUESTION_TARGET // len(TARGET_TOPICS) 


# ----------------------------------------------------
# FUNÇÃO DE LIMPEZA DE TEXTO
# ----------------------------------------------------

def clean_statement_text(text: str) -> str:
    """Remove links de imagem Markdown, URLs e referências de rodapé."""
    
    if not isinstance(text, str):
        return ""
    
    # 1. Remove links de imagem Markdown (ex: ![](URL))
    text = re.sub(r'!\[.*?\]\((.*?)\)', '', text)
    
    # 2. Remove URLs standalone (http:// ou https://)
    text = re.sub(r'https?://\S+', '', text)
    
    # 3. Remove referências de rodapé comuns após a imagem
    # (ex: Disponível em: www.site.com. Acesso em: data.)
    text = re.sub(r'Disponível em:.*Acesso em:.*', '', text)
    
    # 4. Remove quebras de linha múltiplas e espaços extras
    text = text.replace('\n', ' ').strip()
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


# ----------------------------------------------------
# FUNÇÃO DE COLETA PAGINADA
# ----------------------------------------------------

def collect_questions_for_year(year: int, all_formatted_questions: List[Dict[str, Any]]):
    """Coleta questões de um ano, tentando balancear os tópicos."""
    
    questions_endpoint = f"{API_BASE_URL}/exams/{year}/questions"
    offset = 0
    total_expected = 1
    
    # Contador para monitorar o que já foi coletado
    current_topic_counts = {topic: 0 for topic in TARGET_TOPICS}
    for q in all_formatted_questions:
        if q['topic'] in current_topic_counts:
            current_topic_counts[q['topic']] += 1

    print(f"\n-> Iniciando coleta paginada para o ENEM {year}. Status inicial: {current_topic_counts}")
    
    while True:
        if len(all_formatted_questions) >= TOTAL_QUESTION_TARGET:
            break
            
        limit = min(LIMIT_PER_REQUEST, TOTAL_QUESTION_TARGET - len(all_formatted_questions))
        
        params = {
            "limit": limit,
            "offset": offset,
        }

        try:
            response = requests.get(questions_endpoint, params=params)
            response.raise_for_status() 
            raw_data = response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"   Erro na requisição para offset={offset}: {e}. Parando ano {year}.")
            break

        data_list: List[Dict[str, Any]] = raw_data.get('questions', [])
        metadata: Dict[str, Any] = raw_data.get('metadata', {})
        
        total_expected = metadata.get('total', 0)
        has_more = metadata.get('hasMore', False)
        
        if not data_list:
            break 
            
        # Processamento do lote
        for item in tqdm(data_list, desc=f"Processando {year} (Total: {total_expected}, Coletados: {len(all_formatted_questions)})"):
            if len(all_formatted_questions) >= TOTAL_QUESTION_TARGET:
                break
            
            item_topic = item.get('discipline')
            
            # Lógica de Balanceamento: Pula se já atingiu o limite para o tópico
            if item_topic in current_topic_counts and current_topic_counts[item_topic] >= TARGET_PER_TOPIC:
                continue

            try:
                correct_letter: Optional[str] = item.get('correctAlternative')
                alternatives_texts = []
                options = item.get('alternatives', [])
                
                if len(options) != 5 or not correct_letter:
                    continue

                for opt in options:
                    alternatives_texts.append(opt['text'])
                
                # ⬇️ APLICAÇÃO DO FILTRO DE LIMPEZA
                
                # 1. Tenta pegar o enunciado da forma mais provável
                raw_statement = item.get('statement') or item.get('text') or item.get('context', 'Sem enunciado')
                
                # 2. Limpa o texto de qualquer link/referência
                final_statement = clean_statement_text(raw_statement)
                
                # 3. Filtro de Qualidade: Descartar se o texto limpo for muito curto
                if len(final_statement) < 30: # 30 caracteres é um bom mínimo para um enunciado
                    # print(f"AVISO: Questão do ano {year} descartada por enunciado muito curto/vazio após limpeza.")
                    continue 

                # ----------------------------------------------------
                
                all_formatted_questions.append({
                    "statement": final_statement, 
                    "alternatives": alternatives_texts,
                    "correct_answer": correct_letter,
                    "topic": item_topic, 
                    "year": year
                })
                
                # Atualiza a contagem após a coleta bem-sucedida
                if item_topic in current_topic_counts:
                    current_topic_counts[item_topic] += 1
                
            except Exception:
                continue

        # Lógica de Paginação
        if not has_more or offset + limit >= total_expected:
            break
        
        offset += limit
        
    print(f"   Finalizado {year}. Status atual: {current_topic_counts}")
    return all_formatted_questions

# ----------------------------------------------------
# FUNÇÃO PRINCIPAL
# ----------------------------------------------------

def collect_enem_questions():
    all_formatted_questions: List[Dict[str, Any]] = []

    for year in YEARS_TO_COLLECT:
        if len(all_formatted_questions) >= TOTAL_QUESTION_TARGET:
            break
        
        collect_questions_for_year(year, all_formatted_questions)

    # --- Salvamento Final ---
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_formatted_questions, f, ensure_ascii=False, indent=2)
        
    print(f"\n--- Coleta Finalizada! {len(all_formatted_questions)} questões salvas em {OUTPUT_FILE} ---")
    
    final_counts = {}
    for q in all_formatted_questions:
        final_counts[q['topic']] = final_counts.get(q['topic'], 0) + 1
    
    print(f"Distribuição de Tópicos (Meta: {TARGET_PER_TOPIC} por tópico): {final_counts}")


if __name__ == "__main__":
    collect_enem_questions()