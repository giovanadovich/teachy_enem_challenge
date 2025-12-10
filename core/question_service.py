# core/question_service.py
import uuid
from typing import List, Tuple
from sqlalchemy.orm import Session

from api.models import QuestionIn, QuestionOut, QuestionInternal
from db.sql_db import QuestionModel, SessionLocal
from db.vector_db import vector_db_manager
from core.embedding_model import embedding_model
from core.llm_generator import llm_generator

class QuestionService:
    """Serviço que orquestra a busca, geração e persistência de questões."""

    def __init__(self):
        print("QuestionService initialized. DBs and AI clients are ready.")

    # --- Persistência e Indexação ---

    def _save_and_index_question(self, question: QuestionInternal, db: Session):
        """Salva a questão no DB principal e indexa o vetor no Vector DB."""
        
        if not question.id:
            question.id = str(uuid.uuid4())
        
        if not question.embedding:
            question.embedding = embedding_model.generate_embedding(question.statement)

        # 1. Salvar no DB Principal
        db_question = QuestionModel(
            id=question.id,
            statement=question.statement,
            alternatives=question.alternatives,
            correct_answer=question.correct_answer,
            topic=question.topic,
            source=question.source
        )
        db.add(db_question)
        db.commit()
        db.refresh(db_question)
        
        # 2. Indexar no Vector DB
        vector_db_manager.insert_vector(
            vector=question.embedding,
            q_id=question.id,
            payload={"topic": question.topic, "source": question.source}
        )
        return QuestionOut(
            id=db_question.id,
            statement=db_question.statement,
            alternatives=db_question.alternatives,
            correct_answer=db_question.correct_answer
        )

    def persist_new_question(self, question_in: QuestionIn, source: str = "UPLOADED") -> QuestionOut:
        """Endpoint POST: Recebe QuestionIn, processa e armazena."""
        db = SessionLocal()
        try:
            question_internal = QuestionInternal(**question_in.model_dump(), source=source)
            question_internal.embedding = embedding_model.generate_embedding(question_internal.statement)
            
            return self._save_and_index_question(question_internal, db)
        finally:
            db.close()


    # --- Lógica de Recuperação e Geração (GET) ---

    def _retrieve_relevant_questions(self, topic: str, limit: int) -> List[QuestionOut]:
        """Busca as questões mais relevantes no Vector DB."""
        
        query_vector = embedding_model.generate_embedding(topic)
        relevant_hits: List[Tuple[str, float]] = vector_db_manager.search_vectors(query_vector, limit)
        
        if not relevant_hits:
            return []

        unique_ids = [hit[0] for hit in relevant_hits]
        
        db = SessionLocal()
        try:
            questions_data = db.query(QuestionModel).filter(QuestionModel.id.in_(unique_ids)).all()
            
            questions_out = [
                QuestionOut(
                    id=q.id,
                    statement=q.statement,
                    alternatives=q.alternatives,
                    correct_answer=q.correct_answer
                )
                for q in questions_data
            ]
            return questions_out
        finally:
            db.close()
            
    def get_or_generate_questions(self, topic: str, amount: int) -> List[QuestionOut]:
        """Busca e, se necessário, gera o número total de questões."""
        
        # 1. Recuperação
        retrieved_questions = self._retrieve_relevant_questions(topic, amount * 2)
        
        # 2. Seleção
        final_list: List[QuestionOut] = []
        retrieved_ids = set()
        for q in retrieved_questions:
            if q.id not in retrieved_ids:
                final_list.append(q)
                retrieved_ids.add(q.id)
            if len(final_list) >= amount:
                break
        
        # 3. Geração (Fallback)
        questions_needed = amount - len(final_list)
        
        if questions_needed > 0:
            print(f"Gerando {questions_needed} novas questões para o tópico: {topic}.")
            existing_statements = [q.statement for q in final_list]
            
            generated_questions_internal: List[QuestionInternal] = llm_generator.generate_questions(
                topic=topic,
                count=questions_needed,
                existing_statements=existing_statements
            )
            
            # Persistir e Indexar as questões geradas
            db = SessionLocal()
            try:
                for q_internal in generated_questions_internal:
                    q_out = self._save_and_index_question(q_internal, db)
                    final_list.append(q_out)
                    
            finally:
                db.close()
        
        return final_list[:amount]