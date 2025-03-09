# app/routers/agents.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.schemas.schemas import AgentCreate, AgentRead, AgentStatusEnum, AskRequest
from app.core.database import SessionLocal
from app.crud.crud_agents import create_agent, get_agent, list_agents, update_agent_status
from app.crud.crud_memory import add_memory_message, reset_memory_for_agent
from app.utils.agent_factory import build_agent
from app.utils.agent_registry import running_agents
from app.core.redis_client import redis_client

router = APIRouter(prefix="/agents", tags=["agents"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=AgentRead)
def create_agent_endpoint(agent_data: AgentCreate, db: Session = Depends(get_db)):
    agent_db = create_agent(db, agent_data)
    return convert_agent_db_to_read(agent_db)


@router.get("/", response_model=List[AgentRead])
def list_agents_endpoint(db: Session = Depends(get_db)):
    agents_db = list_agents(db)
    return [convert_agent_db_to_read(a) for a in agents_db]


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent_endpoint(agent_id: int, db: Session = Depends(get_db)):
    agent_db = get_agent(db, agent_id)
    if not agent_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    return convert_agent_db_to_read(agent_db)


@router.patch("/{agent_id}/status", response_model=AgentRead)
def update_agent_status_endpoint(agent_id: int, status: AgentStatusEnum, db: Session = Depends(get_db)):
    updated_agent = update_agent_status(db, agent_id, status)
    if not updated_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return convert_agent_db_to_read(updated_agent)


# Helper para convertir AgentDB -> AgentRead
def convert_agent_db_to_read(agent_db):
    return AgentRead(
        id=agent_db.id,
        name=agent_db.name,
        description=agent_db.description,
        system_prompt=agent_db.system_prompt,
        status=agent_db.status,
        llm_config={
            "provider": agent_db.llm_config.provider,
            "model_name": agent_db.llm_config.model_name,
            "temperature": agent_db.llm_config.temperature
        },
        memory_config={
            "memory_type": agent_db.memory_config.memory_type
        },
        vectorstore_config=(
            {
                "store_type": agent_db.vectorstore_config.store_type,
                "config_json": agent_db.vectorstore_config.config_json
            }
            if agent_db.vectorstore_config else None
        ),
        tools=[
            {
                "name": t.name,
                "tool_type": t.tool_type,
                "description": t.description,
                "tool_config": t.tool_config
            }
            for t in agent_db.tools
        ],
        documents=[
            {
                "id": d.id,
                "content": d.content,
                "doc_metadata": d.doc_metadata
            }
            for d in agent_db.documents
        ]
    )


@router.post("/{agent_id}/build")
def build_agent_endpoint(agent_id: int, db: Session = Depends(get_db)):
    """
    Construye el agente, rehidrata la memoria conversacional persistida y lo registra en memoria y en Redis con TTL.
    """
    agent_db = get_agent(db, agent_id)
    if not agent_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent_db.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Agent is not active")
    agent = build_agent(agent_db, db)
    running_agents[agent_id] = {"agent": agent}
    redis_client.setex(f"agent:{agent_id}", 3600, "active")
    return {"message": f"Agent {agent_id} built and ready in memory."}


@router.post("/{agent_id}/ask")
def ask_agent_endpoint(agent_id: int, request_body: AskRequest, db: Session = Depends(get_db)):
    question = request_body.question

    key = f"agent:{agent_id}"
    if not redis_client.exists(key):
        if agent_id in running_agents:
            del running_agents[agent_id]
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} has expired due to inactivity.")

    redis_client.expire(key, 600)

    agent_entry = running_agents.get(agent_id)
    if not agent_entry:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found in memory.")

    agent = agent_entry["agent"]

    add_memory_message(db, agent_id, role="user", content=question)

    try:
        if hasattr(agent, "output_keys") and len(agent.output_keys) > 1:
            output = agent({"question": question, "chat_history": []})
            answer = output.get("answer", output)
        else:
            answer = agent.run(question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while running agent: {e}")

    add_memory_message(db, agent_id, role="assistant", content=answer)

    return {"answer": answer}


@router.post("/{agent_id}/reset_memory")
def reset_agent_memory_endpoint(agent_id: int, db: Session = Depends(get_db)):
    """
    Reinicia la memoria persistida en la BD y limpia la memoria en el agente en memoria.
    """
    if agent_id not in running_agents:
        raise HTTPException(status_code=404, detail="Agent not found in memory.")

    reset_memory_for_agent(db, agent_id)
    agent = running_agents.get(agent_id)
    if agent and hasattr(agent, "memory") and agent.memory:
        agent.memory.clear()
    return {"message": f"Memory reset for agent {agent_id}."}
