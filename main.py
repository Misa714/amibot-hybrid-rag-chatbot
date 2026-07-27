"""
Chatbot RAG Biblioteca Universitaria — Punto de entrada principal.
Archivo refactorizado: lógica separada en módulos (config, db, preprocessing, guardrails, router, rag_engine).
Corrige: D.2 (CORS), D.3 (rate limiting + validación de input), F.2/F.3 (imports muertos), C.2 (monolito).
"""
import time
import json
import logging
import logging.handlers
import smtplib
import os
import hashlib
import asyncio
import torch
from email.mime.text import MIMEText

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import ollama

from config import (
    CORS_ORIGINS, EMBEDDING_MODEL, OLLAMA_MODEL, KNOWLEDGE_PATH,
    RATE_LIMIT, MAX_INPUT_LENGTH, HOST, PORT,
    SMTP_SERVER, SMTP_PORT, SMTP_SENDER, SMTP_RECEIVER, SMTP_PASSWORD,
    CHATBOT_API_KEY
)
from db import init_db, registrar_consulta, actualizar_feedback
from preprocessing import pre_corregir_rapido, preprocesar_consulta, preprocesar_para_embeddings, expandir_intencion, enmascarar_pii
from guardrails import (
    validar_guardrail, ClasificadorIntencionChitChat, completar_contexto,
    obtener_historial, actualizar_historial
)
from router import (
    init_intent_embeddings, detectar_intencion_dura,
    clasificar_intencion_industrial
)
from rag_engine import ejecutar_rag_general_hibrido

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler("chatbot.log", maxBytes=5_000_000, backupCount=3)
    ]
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Inicialización
# ------------------------------------------------------------
init_db()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Asistente de Biblioteca RAG")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

async def verificar_api_key(x_chatbot_token: str = Header(None, alias="X-Chatbot-Token")):
    if x_chatbot_token != CHATBOT_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado: Token de API inválido o ausente."
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Chatbot-Token"]
)

logger.info(f"Cargando modelo de embeddings ({EMBEDDING_MODEL})...")
model = SentenceTransformer(EMBEDDING_MODEL)

def get_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def cargar_conocimiento():
    try:
        if not os.path.exists(KNOWLEDGE_PATH):
            logger.error(f"Archivo {KNOWLEDGE_PATH} no existe.")
            return [], None
            
        with open(KNOWLEDGE_PATH, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            
        if not datos:
            return [], None
        
        # Validar esquema: cada entrada debe tener al menos 'usuario' y 'bot'
        campos_requeridos = {'usuario', 'bot'}
        entradas_invalidas = []
        for i, entrada in enumerate(datos):
            campos_faltantes = campos_requeridos - set(entrada.keys())
            if campos_faltantes:
                entradas_invalidas.append((i, campos_faltantes))
        
        if entradas_invalidas:
            for idx, campos in entradas_invalidas:
                logger.error(f"Entrada #{idx} del JSON sin campos requeridos: {campos}")
            logger.error(f"Se encontraron {len(entradas_invalidas)} entradas inválidas in {KNOWLEDGE_PATH}. Corregir antes de continuar.")
            datos = [d for d in datos if campos_requeridos.issubset(set(d.keys()))]
            if not datos:
                return [], None
            
        # Inicializar ChromaDB
        from vector_db import init_chroma, populate_chroma
        collection = init_chroma()
        
        # Hash check para evitar repoblar si no hay cambios
        json_hash = get_file_hash(KNOWLEDGE_PATH)
        hash_file_path = os.path.join(os.path.dirname(KNOWLEDGE_PATH), "chroma_hash.txt")
        
        hash_valido = False
        if os.path.exists(hash_file_path):
            try:
                with open(hash_file_path, 'r') as hf:
                    cached_hash = hf.read().strip()
                if cached_hash == json_hash:
                    hash_valido = True
            except Exception:
                pass
                
        if hash_valido:
            logger.info("ChromaDB ya está sincronizado. Cargando colección existente...")
        else:
            logger.info("El archivo de conocimiento cambió o no está indexado. Repoblando ChromaDB...")
            populate_chroma(collection, datos, model)
            try:
                with open(hash_file_path, 'w') as hf:
                    hf.write(json_hash)
            except Exception:
                pass
            logger.info("ChromaDB indexado exitosamente.")
            
        return datos, collection
    except Exception as e:
        logger.error(f"Error al cargar conocimiento en ChromaDB: {e}")
        return [], None

datos_biblioteca, collection = cargar_conocimiento()

logger.info("Cargando índice léxico BM25...")
# Se limpia el corpus con preprocesar_consulta para emparejar con la entrada del usuario
corpus_bm25 = BM25Okapi([preprocesar_consulta(d['usuario']).split() for d in datos_biblioteca]) if datos_biblioteca else None

embeddings_intenciones = init_intent_embeddings(model)

clasificador_chitchat = ClasificadorIntencionChitChat()

logger.info(f"Calentando modelo Ollama ({OLLAMA_MODEL})...")
try:
    ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': 'hola'}], options={'num_predict': 1})
    logger.info("Modelo Ollama listo en memoria.")
except Exception as e:
    logger.warning(f"Ollama no disponible al inicio: {e}")

# ------------------------------------------------------------
# Modelos Pydantic
# ------------------------------------------------------------
class Consulta(BaseModel):
    pregunta: str
    sesion: str = "default"

class ConsultaHumano(BaseModel):
    rut: str
    correo: str
    pregunta: str

class FeedbackRequest(BaseModel):
    consulta_id: int
    voto: str
    comentario: str = None  # Campo opcional para comentario libre en dislike

# ------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------
@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/consultar")
@limiter.limit(RATE_LIMIT)
async def consultar(consulta: Consulta, request: Request, _ = Depends(verificar_api_key)):
    inicio = time.time()
    if not datos_biblioteca:
        raise HTTPException(status_code=500, detail="Base offline")

    if len(consulta.pregunta) > MAX_INPUT_LENGTH:
        return {"id": -1, "respuesta": "Tu consulta es demasiado larga. Por favor, resúmela.", "confianza": 0.0, "estado": "rechazo_largo"}

    sesion_id = consulta.sesion
    pregunta_original = consulta.pregunta
    pregunta_log = enmascarar_pii(pregunta_original)
    historial = obtener_historial(sesion_id)

    pregunta_con_contexto = completar_contexto(pregunta_original, historial)
    pregunta_procesada = pre_corregir_rapido(pregunta_con_contexto)

    if pregunta_procesada.lower().strip() in ["hola", "buenos dias", "buenas tardes", "buenas noches", "hey", "ola", "buenas"]:
        resp_saludo = "Hola. Soy AmiBot, el asistente virtual de la Biblioteca Universitaria. ¿En qué te puedo ayudar hoy?"
        consulta_id = await asyncio.to_thread(
            registrar_consulta, pregunta_log, resp_saludo, 1.0, "exito_saludo", time.time() - inicio,
            sesion_id=sesion_id, intent="saludo"
        )
        return {"id": consulta_id, "respuesta": resp_saludo, "confianza": 1.0, "estado": "exito_saludo"}

    pasa_guardrail, msj = validar_guardrail(pregunta_procesada)
    if not pasa_guardrail:
        consulta_id = await asyncio.to_thread(
            registrar_consulta, pregunta_log, msj, 0.0, "rechazo", time.time() - inicio,
            sesion_id=sesion_id, intent="rechazo_guardrail"
        )
        return {"id": consulta_id, "respuesta": msj, "confianza": 0.0, "estado": "rechazo"}

    es_directa, cat, resp_dir = clasificador_chitchat.evaluar(pregunta_procesada)
    if es_directa:
        consulta_id = await asyncio.to_thread(
            registrar_consulta, pregunta_log, resp_dir, 1.0, f"exito_{cat}", time.time() - inicio,
            sesion_id=sesion_id, intent=f"chitchat_{cat}"
        )
        return {"id": consulta_id, "respuesta": resp_dir, "confianza": 1.0, "estado": f"exito_{cat}"}

    # BM25: con stopwords removidas (bag-of-words)
    pregunta_limpia_bm25 = expandir_intencion(preprocesar_consulta(pregunta_procesada))
    # Embeddings: texto natural sin stopwords removidas (el modelo necesita contexto)
    pregunta_para_embedding = expandir_intencion(preprocesar_para_embeddings(pregunta_procesada))
    
    # Envolver en asyncio.to_thread para no bloquear el event loop principal de FastAPI
    query_vector = await asyncio.to_thread(model.encode, pregunta_para_embedding, convert_to_tensor=True)

    # Identificamos intención inicial para métricas
    intent = detectar_intencion_dura(pregunta_procesada)

    # Motor RAG híbrido normal
    intent_log, score_log, telemetria = clasificar_intencion_industrial(query_vector, embeddings_intenciones)
    intent = intent_log if intent == "rag_general" else intent

    # Ejecutar RAG en segundo plano para mantener la API completamente asíncrona y escalable
    respuesta_final, score_asignado, st, ctx_recuperado, ctx_idx, llm_flag = await asyncio.to_thread(
        ejecutar_rag_general_hibrido,
        pregunta_limpia_bm25, query_vector, pregunta_original,
        datos_biblioteca, collection, corpus_bm25, intent
    )
    estado = f"{intent}_{st}"

    consulta_id = await asyncio.to_thread(
        registrar_consulta, pregunta_log, respuesta_final, score_asignado, estado, time.time() - inicio,
        sesion_id=sesion_id, intent=intent,
        contexto_recuperado=ctx_recuperado, contexto_idx=ctx_idx, llm_usado=llm_flag
    )

    actualizar_historial(sesion_id, pregunta_original, respuesta_final)

    return {"id": consulta_id, "respuesta": respuesta_final, "confianza": score_asignado, "estado": estado}


def enviar_correo_smtp(rut: str, correo_estudiante: str, pregunta: str) -> bool:
    """Envía un correo electrónico al bibliotecario usando la configuración de smtp.conf."""
    if not SMTP_PASSWORD:
        logger.warning("SMTP_PASSWORD no configurada en las variables de entorno. Se omite el envío de correo.")
        return False
        
    cuerpo = f"""Se ha recibido una nueva consulta para el bibliotecario desde el Chatbot RAG.

Datos del Estudiante:
- RUT: {rut}
- Correo: {correo_estudiante}

Consulta:
{pregunta}
"""
    msg = MIMEText(cuerpo, "plain", "utf-8")
    msg["Subject"] = f"Nueva consulta Chatbot - RUT: {rut}"
    msg["From"] = SMTP_SENDER
    msg["To"] = SMTP_RECEIVER

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_SENDER, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Correo de consulta humana enviado a {SMTP_RECEIVER}")
        return True
    except Exception as e:
        logger.error(f"Error al enviar correo SMTP: {e}")
        return False


@app.post("/enviar-consulta")
@limiter.limit("5/minute")
async def enviar_consulta(c: ConsultaHumano, request: Request, background_tasks: BackgroundTasks, _ = Depends(verificar_api_key)):
    try:
        # 1. Enmascarar el RUT para proteger PII en la base de datos de auditoría local (ej: 19827364K -> 1982*****)
        rut_limpio = "".join(char for char in c.rut if char.isalnum())
        rut_enmascarado = f"{rut_limpio[:4]}{'*' * max(0, len(rut_limpio) - 4)}" if len(rut_limpio) > 4 else "****"
        
        pregunta_log = enmascarar_pii(c.pregunta)
        await asyncio.to_thread(
            registrar_consulta, pregunta_log, f"Enviada por RUT: {rut_enmascarado}", 1.0, "escalado_humano", 0,
            intent="escalado_humano"
        )
        
        # 2. Enviar el correo electrónico en segundo plano para no bloquear el hilo de FastAPI
        background_tasks.add_task(enviar_correo_smtp, c.rut, c.correo, c.pregunta)
        
        return {"mensaje": "Tu consulta ha sido enviada al bibliotecario."}
    except Exception as e:
        logger.error(f"Error en enviar-consulta: {e}")
        return {"mensaje": f"Error: {str(e)}"}


@app.post("/feedback")
async def recibir_feedback(fb: FeedbackRequest, _ = Depends(verificar_api_key)):
    if fb.voto.lower() not in ["like", "dislike"]:
        raise HTTPException(status_code=400, detail="El voto debe ser 'like' o 'dislike'")
    
    exito = await asyncio.to_thread(actualizar_feedback, fb.consulta_id, fb.voto.lower(), fb.comentario)
    if not exito:
        raise HTTPException(status_code=404, detail="ID de consulta no encontrado")
        
    return {"mensaje": "Feedback registrado correctamente"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
