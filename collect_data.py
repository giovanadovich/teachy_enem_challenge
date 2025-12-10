# collect_data.py (Versão Final sem o Filtro de Idioma)
import requests
import json
import os
from tqdm import tqdm
from typing import List, Dict, Any, Optional

# --- Configurações ---
API_BASE_URL = "https://api.enem.dev/v1" 
OUTPUT_FILE = "data/initial_enem_data.json"

YEARS_TO_COLLECT = [2022, 2021, 2020] 
TOTAL_QUESTION_TARGET = 100 
LIMIT_PER_REQUEST = 30 

def collect_questions_for_year(year: int, all_formatted_questions: List[Dict[str, Any]]):
    """Coleta todas as questões de um ano específico usando paginação."""
    
    questions_endpoint = f"{API_BASE_URL}/exams/{year}/questions"
    offset = 0
    total_expected = 1
    questions_count = 0
    
    print(f"\n-> Iniciando coleta paginada para o ENEM {year}...")
    
    while True:
        if len(all_formatted_questions) >= TOTAL_QUESTION_TARGET:
            print("   Limite total de questões atingido.")
            break
            
        limit = min(LIMIT_PER_REQUEST, TOTAL_QUESTION_TARGET - len(all_formatted_questions))
        
        # ⚠️ CORREÇÃO DO ERRO 400: Parâmetro 'language' removido
        params = {
            "limit": limit,
            "offset": offset,
        }

        try:
            response = requests.get(questions_endpoint, params=params)
            response.raise_for_status() 
            raw_data = response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"   Erro na requisição para offset={offset}: {e}. Parando ano {year}.")
            break

        data_list: List[Dict[str, Any]] = raw_data.get('questions', [])
        metadata: Dict[str, Any] = raw_data.get('metadata', {})
        
        total_expected = metadata.get('total', 0)
        has_more = metadata.get('hasMore', False)
        
        if not data_list:
            break 
            
        # Processamento do lote
        for item in tqdm(data_list, desc=f"Processando {year} (Total: {total_expected})"):
            if len(all_formatted_questions) >= TOTAL_QUESTION_TARGET:
                break

            try:
                correct_letter: Optional[str] = item.get('correctAlternative')
                alternatives_texts = []
                options = item.get('alternatives', [])
                
                if len(options) != 5 or not correct_letter:
                    continue

                for opt in options:
                    alternatives_texts.append(opt['text'])
                
                all_formatted_questions.append({
                    "statement": item.get('context', 'Sem enunciado'), 
                    "alternatives": alternatives_texts,
                    "correct_answer": correct_letter,
                    "topic": item.get('discipline', 'Geral'), 
                    "year": year
                })
                questions_count += 1
                
            except Exception:
                continue

        # Lógica de Paginação
        if not has_more or offset + limit >= total_expected:
            break
        
        offset += limit
        
    print(f"   Finalizado {year}. Questões coletadas neste ano: {questions_count}")
    return all_formatted_questions

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


if __name__ == "__main__":
    collect_enem_questions()