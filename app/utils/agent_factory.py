# app/utils/agent_factory.py
import requests
import sqlalchemy
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType, AgentExecutor, Tool
from langchain.memory import ConversationBufferMemory, ConversationBufferWindowMemory
from langchain.schema import Document, HumanMessage, AIMessage
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain

from app.crud.crud_memory import get_memory_by_agent_id


def custom_get(url: str) -> str:
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error al hacer GET a {url}: {e}"

def list_tables_in_db(connection_string: str) -> str:
    try:
        engine = sqlalchemy.create_engine(connection_string)
        inspector = sqlalchemy.inspect(engine)
        tables = inspector.get_table_names()
        return f"Tablas en la base de datos: {tables}"
    except Exception as e:
        return f"Error al listar tablas: {str(e)}"

def call_pagerduty_api(base_url: str, api_token: str) -> str:
    url = f"{base_url}"
    headers = {
        "Authorization": f"Token token={api_token}",
        "Accept": "application/vnd.pagerduty+json;version=2"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return f"Respuesta de PagerDuty: {response.json()}"
    except Exception as e:
        return f"Error en la llamada a PagerDuty: {str(e)}"

def call_api(base_url: str, api_token: str) -> str:
    url = f"{base_url}"
    headers = {
        "Authorization": f"{api_token}",
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return f"Respuesta de API: {response.json()}"
    except Exception as e:
        return f"Error en la llamada a la API: {str(e)}"

def internal_custom_task() -> str:
    return "Tarea interna realizada exitosamente."

# ---------------------------
# Generación dinámica de tools
# ---------------------------
def generate_langchain_tools(tools_config) -> list:
    tools = []
    for tool_db in tools_config:
        t_type = tool_db.tool_type
        name = tool_db.name
        description = tool_db.description or ""
        # Se accede al atributo correcto: tool_config
        config = getattr(tool_db, "tool_config", {})

        if t_type == "RequestsGetTool":
            def _get_tool(input_str: str, func=custom_get):
                return func(input_str)
            tools.append(Tool(
                name=name,
                func=_get_tool,
                description=description or "Herramienta GET que recibe una URL como input."
            ))
        elif t_type == "db":
            connection_string = config.get("connection_string", "")
            def _db_tool(input_str: str, connection_string=connection_string):
                return list_tables_in_db(connection_string)
            tools.append(Tool(
                name=name,
                func=_db_tool,
                description=description or "Herramienta para listar tablas en la base de datos."
            ))
        elif t_type == "apiPD":
            base_url = config.get("base_url", "")
            api_token = config.get("api_token", "")
            def _apiPD_tool(input_str: str, base_url=base_url, token=api_token):
                return call_pagerduty_api(base_url, token)
            tools.append(Tool(
                name=name,
                func=_apiPD_tool,
                description=description or "Herramienta para interactuar con la API de PagerDuty."
            ))
        elif t_type == "api":
            base_url = config.get("base_url", "")
            api_token = config.get("api_token", "")
            def _api_tool(input_str: str, base_url=base_url, token=api_token):
                return call_api(base_url, token)
            tools.append(Tool(
                name=name,
                func=_api_tool,
                description=description or "Herramienta para interactuar con la API."
            ))
        elif t_type == "function":
            def _internal_tool(input_str: str):
                return internal_custom_task()
            tools.append(Tool(
                name=name,
                func=_internal_tool,
                description=description or "Herramienta para ejecutar una función interna."
            ))
    return tools

# ---------------------------
# Función principal: build_agent
# ---------------------------
def build_agent(agent_db, db) -> AgentExecutor:
    # 1. Crear el LLM según la configuración
    llm_config = agent_db.llm_config
    provider = llm_config.provider  # "openai"
    model_name = llm_config.model_name
    temperature = llm_config.temperature
    openai_api_key = getattr(llm_config, "api_key", None)

    if provider == "openai":
        llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            openai_api_key=openai_api_key,
        )
    else:
        raise ValueError(f"Proveedor LLM desconocido: {provider}")

    # 2. Configurar la memoria (si aplica)
    memory_config = agent_db.memory_config
    memory = None
    if memory_config:
        mem_type = memory_config.memory_type
        if mem_type == "ConversationBufferMemory":
            memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        elif mem_type == "ConversationBufferWindowMemory":
            memory = ConversationBufferWindowMemory(k=5, memory_key="chat_history", return_messages=True)
        else:
            raise ValueError(f"Tipo de memoria no soportado: {mem_type}")

    if memory:
        mem_entries = get_memory_by_agent_id(db, agent_db.id)
        conversation_history = []
        for entry in mem_entries:
            if entry.role.lower() == "user":
                conversation_history.append(HumanMessage(content=entry.content))
            elif entry.role.lower() == "assistant":
                conversation_history.append(AIMessage(content=entry.content))
        memory.chat_memory.messages = conversation_history

    # 3. Configurar el vectorstore (si aplica)
    vectorstore_config = agent_db.vectorstore_config
    vs_retriever = None
    if vectorstore_config and vectorstore_config.store_type == "FAISS":
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        docs = []
        for doc_db in agent_db.documents:
            doc = Document(
                page_content=doc_db.content,
                metadata={"id": doc_db.id, "extra": doc_db.doc_metadata}
            )
            docs.append(doc)
        index_path = vectorstore_config.config_json.get("index_path", "./faiss_index")
        try:
            vs = FAISS.load_local(index_path, embeddings)
        except Exception as e:
            vs = FAISS.from_documents(docs, embeddings)
            vs.save_local(index_path)
        vs_retriever = vs.as_retriever(search_type="similarity", search_kwargs={"k": 2})

    # 4. Decidir la estrategia de agente:
    #    - Si hay herramientas configuradas en la BD, usar initialize_agent con esas tools.
    #    - Sino, si existe vectorstore, usar retrieval chain.
    #    - Sino, fallback a un agente simple sin herramientas.
    system_prompt = agent_db.system_prompt
    if agent_db.tools and len(agent_db.tools) > 0:
        # Crear herramientas según la configuración
        tools = generate_langchain_tools(agent_db.tools)
        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            memory=memory
        )
    elif vs_retriever is not None:
        agent = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vs_retriever,
            memory=memory,
            return_source_documents=False
        )
    else:
        # Fallback: agente básico sin tools ni retrieval
        agent = initialize_agent(
            tools=[],
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            memory=memory
        )

    # 5. Asignar el system prompt proveniente de la BD (si corresponde)
    # Solo sobreescribimos el prompt si el agente tiene un atributo 'agent' y
    # si el system_prompt contiene los placeholders requeridos.
    if system_prompt:
        try:
            # Verifica que el prompt incluya los placeholders requeridos
            current_prompt = agent.agent.llm_chain.prompt
            required_vars = {"agent_scratchpad", "input"}
            # Solo se asigna si el system_prompt los incluye
            if all(ph in system_prompt for ph in ["{agent_scratchpad}", "{input}"]):
                agent.agent.llm_chain.prompt.template = system_prompt
        except AttributeError:
            # Si el agente no tiene 'agent.llm_chain.prompt' (por ejemplo, en el retrieval chain), se omite.
            pass

    return agent
