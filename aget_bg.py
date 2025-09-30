from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.schema import HumanMessage, SystemMessage, AIMessage

#usuario = "root"
#password = "MiPasswordSegura"
#host = "localhost"  # o la IP de tu servidor
#puerto = 3306       # Puerto por defecto de MariaDB
#base_datos = "auxiliar"

usuario = "infoll"
password = "prueba2025"
host = "164.92.204.181"  # o la IP de tu servidor
puerto = 3306       # Puerto por defecto de MariaDB
base_datos = "loginfo"

engine_root = create_engine(f"mysql+pymysql://{usuario}:{password}@{host}:{puerto}/{base_datos}")

DATABASE_URL = f"mysql+pymysql://{usuario}:{password}@{host}:{puerto}/{base_datos}"

Base = declarative_base()

# Define the Session model
class Session(Base):
    __tablename__ = "sessions_info"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), unique=True, nullable=False)
    
    # Relación con mensajes
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan"
    )

# Define the Message model
class Message(Base):
    __tablename__ = "messages_info"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions_info.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False) 
    
    # Relación con sesión
    session = relationship("Session", back_populates="messages")

# Create the database and the tables
engine = create_engine(DATABASE_URL, echo=True, future=True)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Dependencia para obtener sesión de DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_message(session_id: str, role: str, content: str):
    db = next(get_db())
    try:
        # Buscar sesión por su ID lógico
        sesion = db.query(Session).filter(Session.session_id == session_id).first()
        if not sesion:
            # Crear nueva sesión si no existe
            sesion = Session(session_id=session_id)
            db.add(sesion)
            db.commit()
            db.refresh(sesion)  # obtiene el id autogenerado

        # Crear mensaje ligado a la sesión
        mensaje = Message(
            session_id=sesion.id,
            role=role,
            content=content
        )
        db.add(mensaje)
        db.commit()
        db.refresh(mensaje)

        return mensaje

    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error al guardar mensaje: {e}")
        return None
    finally:
        db.close()

def load_session_history(session_id: str) -> ChatMessageHistory:
    db = next(get_db())
    chat_history = ChatMessageHistory()
    try:
        # Recuperar la sesión
        sesion = db.query(Session).filter(Session.session_id == session_id).first()
        if sesion:
            # Traer últimos 10 mensajes ordenados por fecha
            messages = (
                db.query(Message)
                .filter(Message.session_id == sesion.id)
                .order_by(Message.created_at.desc())
                .limit(10)
                .all()
            )
            # Como vienen en orden descendente, invertirlos
            messages = list(reversed(messages))

            for mensaje in messages:
                if mensaje.role in ["human", "user"]:
                    chat_history.add_message(HumanMessage(content=mensaje.content))
                elif mensaje.role in ["ai", "gpt", "assistant"]:
                    chat_history.add_message(AIMessage(content=mensaje.content))
                else:
                    # fallback para roles personalizados
                    chat_history.add_message({"role": mensaje.role, "content": mensaje.content})

    except SQLAlchemyError as e:
        print(f"Error al cargar historial: {e}")
    finally:
        db.close()

    return chat_history

def load_history_chat(session_id: str) -> ChatMessageHistory:
    db = next(get_db())
    messages = []
    try:
        # Recuperar la sesión
        sesion = db.query(Session).filter(Session.session_id == session_id).first()
        if sesion:
            # Traer últimos 10 mensajes ordenados por fecha
            messages_query = (
                db.query(Message)
                .filter(Message.session_id == sesion.id)
                .order_by(Message.created_at.desc())
                .limit(10)
                .all()
            )
            # Como vienen en orden descendente, invertirlos
            messages_query = list(reversed(messages_query))

            messages = []
            for item in messages_query:
                role = item.role
                message = item.content

                messages.append({'role':role, 'message':message })

    except SQLAlchemyError as e:
        print(f"Error al cargar historial: {e}")
    finally:
        db.close()

    return messages

