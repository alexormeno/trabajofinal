from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools.retriever import create_retriever_tool
from langchain_core.messages import HumanMessage
import os
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.chains.combine_documents import create_stuff_documents_chain
#from langchain.embeddings import OpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings
#from langchain.vectorstores import Chroma
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_core.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor

from langchain_community.vectorstores import Chroma
#from langchain_chroma import Chroma

from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_core.chat_history import BaseChatMessageHistory

from aget_bg import load_session_history, save_message

from dotenv import load_dotenv
load_dotenv()

NOMBRE_INDICE_CHROMA = "instruct-embeddings-manual-informatica"

# CARGAR VARIABLES DE ENTORN
os.environ['OPENAI_API_KEY'] = os.getenv("OPENAI_API_KEY") #OPENAI_API_KEY
os.environ['TAVILY_API_KEY'] = os.getenv("API_TAVILITY_SEARCH") #API_TAVILITY_SEARCH

# VECTORSTORE
embedding_openai = OpenAIEmbeddings(model="text-embedding-ada-002")

# CHROMA
#vectorstore_chroma_pers = Chroma(
#    persist_directory=NOMBRE_INDICE_CHROMA,
#    embedding_function=embedding_openai
#)

#retriever_chroma = vectorstore_chroma_pers.as_retriever(
#    search_kwargs={'k': 4}
#)

# QDRANT
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain.schema import BaseRetriever 

# URL de tu instancia Qdrant
url_qdrant= os.getenv("url_qdrant") 
api_key_qdrant= os.getenv("api_key_qdrant")
collection_name = "manual"
k_documentos = 5

# 1. Inicializar el Cliente de Qdrant
qdrant_client = QdrantClient(url=url_qdrant, api_key=api_key_qdrant)

# 2. Conectar el Almacén de Vectores de LangChain a la colección
vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=collection_name,
    embedding=embedding_openai,
)

# 3. Convertir el VectorStore en un Retriever
retriever_qdrant = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": k_documentos}
)


# CREAR MODELO LLM
llm = ChatOpenAI(
    model = 'gpt-4o',
    temperature = 0
)

# GUARDAR HISTORIAL
#store = {}

#def get_session_history(session_id : str) -> RunnableWithMessageHistory:
#    if session_id not in store:
#        store[session_id] = ChatMessageHistory()

#    return store[session_id]

def get_session_history(session_id : str) -> BaseChatMessageHistory:
    store = load_session_history(session_id)
    return store


# INTERACTUAR CON EL HISTORIAL
contextualize_q_system_ptompt = (
    #"Responde segun el historial de chat y la última pregunta del usuario"
    #"Si no está en el historial de chat o en el contexto. No respondas la preguna"
    #"Además responde de manera profesional a la pregunta del usuario"
    "Tu tarea es reformular la última pregunta del usuario para que sea una pregunta independiente, "
    "considerando el historial de chat. Esto permitirá que la pregunta sea comprendida sin el"
    "historial de conversación previo. Si la pregunta del usuario no requiere contexto, devuélvela tal cual."
    "Asegúrate de que la nueva pregunta esté completa y sea clara."
)

contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ('system', contextualize_q_system_ptompt),
        MessagesPlaceholder('chat_history'),
        ('human', '{input}')
    ]
)

history_aware_retriever = create_history_aware_retriever(
    llm,
   #retriever_chroma,
    retriever_qdrant,
    contextualize_q_prompt
)

# HERRAMIENTAS DE BUSQUEDA
# Inicializa la herramienta Tavily Search
search = TavilySearchResults(max_results=3)

# Crea una herramienta a partir de tu retriever existente
@tool
def retriever_tool(query: str):
    """ Busca información en la base de datos de conocimiento local. """
    return history_aware_retriever.invoke({"input": query})

from langchain.agents import Tool

tools = [
    Tool(
        name="Retriever",
        func=retriever_tool,
        description="Recupera información relevante de la base de datos o documentos cargados."
    ),
    Tool(
        name="BusquedaWeb",
        func=search,
        description="Realiza búsquedas web recientes y devuelve títulos, links y resúmenes."
    )
]

agent_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """
            Eres un asistente de IA experto, diseñado para responder de manera precisa y profesional. Tu objetivo principal es utilizar la herramienta 'retriever_tool' para obtener la información necesaria.

            **Jerarquía de Herramientas:**
            1.  **'retriever_tool'**: Tu prioridad es buscar información **exclusivamente** en el contexto local provisto. Usa esta herramienta para responder a preguntas que se basen en tu base de conocimiento interna.
            2.  **'tavily_search'**: Si la pregunta requiere datos actuales, utiliza esta herramienta. **Siempre incluye las URLs (fuentes) de la información que encuentres.**

            **Condiciones de uso de las herramientas:**
            * **Utiliza la 'retriever_tool' únicamente si el contenido de la pregunta del usuario se refiere explícitamente a temas de informática o a conceptos guardados en tu base de conocimiento local.**
            * **Cuando utilices 'retriever_tools' devuelve la pagina de donde sacaste el contenido solo si existe la pagina o si esta contenida en el indice del manual.
            * **Si la pregunta del usuario requiere información que no está en tu base de conocimiento local, utiliza la herramienta 'tavily_search' para realizar una búsqueda en internet.**
            * **Cuando hagas una búsqueda en internet y devuelvas resultados, debes informar al usuario que el contenido de esos enlaces es externo al material de la cátedra, por lo cual no te haces responsable de su contenido.**
            * **Cuando el contenido no sea encontrado en retriever_tool responde que no tienes informacion para responder acerca del tema
            * **Cuando contengas links de videos de youtube, agrega en markdown un iframe donde visualizar el video
                  
            **Restricciones Clave:**
            * **Si el contenido de la pregunta NO se refiere a tu base de conocimiento, no utilices ninguna herramienta y responde que no puedes contestar sobre ese tema.**
            * **Cuando se te pida contenido externo, primero verifica que exista en un base de conocimiento y luego realiza la busqueda
            * **Si la busqueda que se va a realizar en tavility_search, realizala siempre y cuando el contenido exista en retriever_tools
            * **No inventes ni alucines respuestas.** Si no tienes información suficiente para responder, dilo de manera cortés.
            * **Responde de forma concisa y directa.** Evita divagaciones.
            * **Asegúrate de que tus respuestas sean relevantes para la pregunta del usuario.**

            Comienza tu proceso de pensamiento analizando la pregunta del usuario para determinar si puede ser respondida con tu base de conocimiento local o si requiere una búsqueda externa."""),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)


# Crea el agente
agent = create_tool_calling_agent(llm, tools, agent_prompt)

# Crea el executor del agente
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


# Crea la cadena conversacional con el historial de mensajes
conversation_agent_chain = RunnableWithMessageHistory(
    agent_executor,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)

def answer_rag_chain(query, id_session):


    save_message(id_session, "human", query)

    response = conversation_agent_chain.invoke(
        {"input": query},
        config={"configurable": {"session_id": id_session}} 
    )

    save_message(id_session, "ai", response["output"])

    return response['output']

