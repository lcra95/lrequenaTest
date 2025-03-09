# app/models/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON, func
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class AgentStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AgentDB(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    status = Column(Enum(AgentStatusEnum), nullable=False, default=AgentStatusEnum.ACTIVE)

    # Relaciones con las configuraciones y otros componentes
    llm_config = relationship("AgentLLMConfigDB", uselist=False, back_populates="agent", cascade="all, delete-orphan")
    memory_config = relationship("AgentMemoryConfigDB", uselist=False, back_populates="agent",
                                 cascade="all, delete-orphan")
    vectorstore_config = relationship("AgentVectorStoreConfigDB", uselist=False, back_populates="agent",
                                      cascade="all, delete-orphan")
    tools = relationship("AgentToolDB", back_populates="agent", cascade="all, delete-orphan")
    documents = relationship("AgentDocumentDB", back_populates="agent", cascade="all, delete-orphan")
    memories = relationship("AgentMemoryDB", back_populates="agent", cascade="all, delete-orphan")


class AgentLLMConfigDB(Base):
    __tablename__ = "agent_llm_config"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    provider = Column(String(50), default="openai")
    model_name = Column(String(100), nullable=False, default="gpt-3.5-turbo")
    temperature = Column(Integer, nullable=False, default=0)
    api_key = Column(String(200), nullable=True)

    agent = relationship("AgentDB", back_populates="llm_config")


class AgentMemoryConfigDB(Base):
    __tablename__ = "agent_memory_config"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    memory_type = Column(String(100), nullable=False, default="ConversationBufferMemory")

    agent = relationship("AgentDB", back_populates="memory_config")


class AgentVectorStoreConfigDB(Base):
    __tablename__ = "agent_vectorstore_config"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    store_type = Column(String(50), nullable=False, default="FAISS")
    config_json = Column(JSON, nullable=True)

    agent = relationship("AgentDB", back_populates="vectorstore_config")


class AgentToolDB(Base):
    __tablename__ = "agent_tools"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    name = Column(String(100), nullable=False)
    tool_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    tool_config = Column(JSON, nullable=True)

    agent = relationship("AgentDB", back_populates="tools")


class AgentDocumentDB(Base):
    __tablename__ = "agent_documents"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    content = Column(Text, nullable=False)
    doc_metadata = Column(JSON, nullable=True)

    agent = relationship("AgentDB", back_populates="documents")


# Modelo para la memoria persistida:
class AgentMemoryDB(Base):
    __tablename__ = "agent_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())

    agent = relationship("AgentDB", back_populates="memories")
