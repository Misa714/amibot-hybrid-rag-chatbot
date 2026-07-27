"""
Módulo de base de datos — SQLite con WAL mode y thread-safety.
Corrige: E.1 (thread-safety), D.4 (corrupción por kill -9), C.3 (rutas hardcodeadas).
Ampliado para telemetría de piloto: sesion_id, intent, contexto_recuperado, feedback_comentario.
"""
import sqlite3
import logging
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger(__name__)

def init_db():
    """Inicializa la base de datos con WAL mode para mejor concurrencia."""
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consultas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            sesion_id TEXT,
            pregunta TEXT,
            respuesta TEXT,
            contexto_recuperado TEXT,
            contexto_idx INTEGER,
            score REAL,
            intent TEXT,
            estado TEXT,
            tiempo REAL,
            llm_usado INTEGER DEFAULT 0,
            feedback TEXT,
            feedback_comentario TEXT,
            revisado INTEGER DEFAULT 0
        )
    """)
    # Migrar tablas existentes que no tengan las nuevas columnas
    try:
        cursor.execute("PRAGMA table_info(consultas)")
        columnas_existentes = {row[1] for row in cursor.fetchall()}
        nuevas_columnas = {
            "sesion_id": "TEXT",
            "contexto_recuperado": "TEXT",
            "contexto_idx": "INTEGER",
            "intent": "TEXT",
            "llm_usado": "INTEGER DEFAULT 0",
            "feedback_comentario": "TEXT"
        }
        for col, tipo in nuevas_columnas.items():
            if col not in columnas_existentes:
                cursor.execute(f"ALTER TABLE consultas ADD COLUMN {col} {tipo}")
                logger.info(f"Columna '{col}' agregada a la tabla consultas.")
    except Exception as e:
        logger.warning(f"Error al migrar columnas: {e}")
    conn.commit()
    conn.close()
    logger.info(f"Base de datos inicializada en {DB_PATH} (WAL mode)")


def registrar_consulta(pregunta: str, respuesta: str, score: float, estado: str,
                       duracion: float, sesion_id: str = None, intent: str = None,
                       contexto_recuperado: str = None, contexto_idx: int = None,
                       llm_usado: int = 0) -> int:
    """Registra una consulta de forma thread-safe y devuelve su ID.
    
    Args:
        pregunta: Texto de la pregunta (con PII enmascarado).
        respuesta: Texto de la respuesta generada.
        score: Score de confianza del RAG.
        estado: Estado de la consulta (ej: 'rag_generado', 'bypass_router_lockers').
        duracion: Tiempo de procesamiento en segundos.
        sesion_id: Identificador de la sesión del usuario.
        intent: Intención clasificada (ej: 'lockers', 'catalogo', 'rag_general').
        contexto_recuperado: Texto crudo del JSON que el RAG recuperó como contexto.
        contexto_idx: Índice del documento recuperado en el JSON de conocimiento.
        llm_usado: 1 si la respuesta pasó por Ollama, 0 si fue bypass directo.
    """
    conn = None
    row_id = -1
    try:
            conn = sqlite3.connect(DB_PATH, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO consultas 
                   (fecha, sesion_id, pregunta, respuesta, contexto_recuperado, contexto_idx,
                    score, intent, estado, tiempo, llm_usado) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (datetime.now().isoformat(), sesion_id, pregunta, respuesta,
                 contexto_recuperado, contexto_idx, score, intent, estado, duracion, llm_usado)
            )
            conn.commit()
            row_id = cursor.lastrowid
    except Exception as e:
        logger.error(f"Error al guardar consulta: {e}")
    finally:
        if conn:
            conn.close()
    return row_id


def actualizar_feedback(consulta_id: int, feedback_valor: str, comentario: str = None) -> bool:
    """Actualiza el feedback ('like' o 'dislike') y comentario opcional de una consulta por su ID."""
    conn = None
    success = False
    try:
            conn = sqlite3.connect(DB_PATH, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE consultas SET feedback = ?, feedback_comentario = ? WHERE id = ?",
                (feedback_valor, comentario, consulta_id)
            )
            conn.commit()
            success = cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error al actualizar feedback: {e}")
    finally:
        if conn:
            conn.close()
    return success
