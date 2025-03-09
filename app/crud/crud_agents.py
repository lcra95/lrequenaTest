# app/crud/crud_agents.py
from sqlalchemy.orm import Session
from app.models.models import (
    AgentDB, AgentLLMConfigDB, AgentMemoryConfigDB,
    AgentVectorStoreConfigDB, AgentToolDB, AgentDocumentDB
)
from app.schemas.schemas import AgentCreate, AgentStatusEnum

def create_agent(db: Session, agent_data: AgentCreate) -> AgentDB:
    # 1) Crear el registro principal
    agent_db = AgentDB(
        name=agent_data.name,
        description=agent_data.description,
        system_prompt=agent_data.system_prompt,
        status=agent_data.status
    )
    db.add(agent_db)
    db.flush()  # para tener agent_db.id

    # 2) LLM config
    llm_db = AgentLLMConfigDB(
        agent_id=agent_db.id,
        provider=agent_data.llm_config.provider,
        model_name=agent_data.llm_config.model_name,
        temperature=agent_data.llm_config.temperature,
        api_key=agent_data.llm_config.api_key
    )
    db.add(llm_db)

    # 3) Memory config
    mem_db = AgentMemoryConfigDB(
        agent_id=agent_db.id,
        memory_type=agent_data.memory_config.memory_type
    )
    db.add(mem_db)

    # 4) Vector store (opcional)
    if agent_data.vectorstore_config:
        vs_conf = agent_data.vectorstore_config
        vs_db = AgentVectorStoreConfigDB(
            agent_id=agent_db.id,
            store_type=vs_conf.store_type,
            config_json=vs_conf.config_json
        )
        db.add(vs_db)

    # 5) Tools
    for tool in agent_data.tools:
        tool_db = AgentToolDB(
            agent_id=agent_db.id,
            name=tool.name,
            tool_type=tool.tool_type,
            description=tool.description,
            tool_config=tool.tool_config
        )
        db.add(tool_db)

    # 6) Documents
    for doc in agent_data.documents:
        doc_db = AgentDocumentDB(
            agent_id=agent_db.id,
            content=doc.content,
            doc_metadata=doc.doc_metadata
        )
        db.add(doc_db)

    db.commit()
    db.refresh(agent_db)
    return agent_db

def get_agent(db: Session, agent_id: int) -> AgentDB | None:
    return db.query(AgentDB).filter(AgentDB.id == agent_id).first()

def list_agents(db: Session):
    return db.query(AgentDB).all()

def update_agent_status(db: Session, agent_id: int, status: AgentStatusEnum) -> AgentDB | None:
    agent = db.query(AgentDB).filter(AgentDB.id == agent_id).first()
    if not agent:
        return None
    agent.status = status
    db.commit()
    db.refresh(agent)
    return agent

#