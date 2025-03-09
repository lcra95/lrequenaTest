# app/crud/crud_memory.py
from sqlalchemy.orm import Session
from app.models.models import AgentMemoryDB

def get_memory_by_agent_id(db: Session, agent_id: int):
    """Retorna el historial de mensajes para un agente, ordenados por timestamp."""
    return db.query(AgentMemoryDB).filter(AgentMemoryDB.agent_id == agent_id).order_by(AgentMemoryDB.timestamp).all()

def add_memory_message(db: Session, agent_id: int, role: str, content: str):
    """Agrega un mensaje de memoria para el agente."""
    mem_entry = AgentMemoryDB(
        agent_id=agent_id,
        role=role,
        content=content
    )
    db.add(mem_entry)
    db.commit()
    db.refresh(mem_entry)
    return mem_entry

def reset_memory_for_agent(db: Session, agent_id: int):
    """Elimina todos los mensajes de memoria para un agente."""
    db.query(AgentMemoryDB).filter(AgentMemoryDB.agent_id == agent_id).delete()
    db.commit()
