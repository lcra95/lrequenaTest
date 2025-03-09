
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
import enum

class AgentStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class LLMConfig(BaseModel):
    provider: Optional[str] = "openai"
    model_name: str = "gpt-3.5-turboljlj"
    temperature: int = 0
    api_key: Optional[str] = None

class MemoryConfig(BaseModel):
    memory_type: str = "ConversationBufferMemory"

class VectorStoreConfig(BaseModel):
    store_type: str = "FAISS"
    config_json: Dict[str, Any] = {}

class ToolConfig(BaseModel):
    name: str
    tool_type: str
    description: Optional[str] = None
    tool_config: Optional[Dict[str, Any]] = None

class DocumentCreate(BaseModel):
    content: str
    doc_metadata: Optional[Dict[str, Any]] = None

class DocumentRead(BaseModel):
    id: int
    content: str
    doc_metadata: Optional[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)

# Creación (POST) del agente
class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    status: AgentStatusEnum = AgentStatusEnum.ACTIVE

    llm_config: LLMConfig
    memory_config: MemoryConfig
    vectorstore_config: Optional[VectorStoreConfig] = None
    tools: List[ToolConfig] = []
    documents: List[DocumentCreate] = []

# Lectura (GET) del agente
class AgentRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    system_prompt: Optional[str]
    status: AgentStatusEnum

    # Expandir configuración si lo deseas
    llm_config: LLMConfig
    memory_config: MemoryConfig
    vectorstore_config: Optional[VectorStoreConfig] = None
    tools: List[ToolConfig]
    documents: List[DocumentRead]

    model_config = ConfigDict(from_attributes=True)

class AskRequest(BaseModel):
    question: str