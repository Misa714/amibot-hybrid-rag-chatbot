"""
Motor RAG General Híbrido — BM25 + Semántico + RRF.
Corrige: E.3 (try/except en Ollama), falsos negativos en multas y fallos de BM25 nulo.
Configuración externalizada: filtro de ruido y familias de categorías se cargan desde config/.
"""
import json
import logging
import os
import torch
import numpy as np
from sentence_transformers import util
import ollama

from config import UMBRAL_BAJO, RESPUESTAS_CRITICAS, OLLAMA_MODEL

logger = logging.getLogger(__name__)

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'config')


def _cargar_filtro_ruido():
    """Carga configuración del filtro anti-ruido desde config/filtro_ruido.json."""
    default = {
        "palabras_castigo": ["multa", "reposición", "reposicion", "pagar", "perder beneficios", "sanción", "sancion"],
        "palabras_especificas": ["devolver", "devolucion", "devolución", "entrega", "entregar", "perdi", "perdio", "perdió", "pierdo", "pierde", "pierda", "pierden", "perdido", "dañado", "roto", "mal estado"],
        "excepciones": []
    }
    config_path = os.path.join(_CONFIG_DIR, 'filtro_ruido.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Filtro de ruido cargado desde config/")
        return data
    except FileNotFoundError:
        return default
    except Exception as e:
        logger.warning(f"Error al cargar filtro_ruido.json: {e}. Usando valores por defecto.")
        return default


def _cargar_familias_categorias():
    """Carga agrupaciones de categorías para boost desde config/familias_categorias.json."""
    default = {
        "bases_datos": ["recursos_cientificos"],
        "catalogo": ["catalogo_carreras"],
        "prestamos": ["renovacion", "devolucion", "multas_bloqueos"]
    }
    config_path = os.path.join(_CONFIG_DIR, 'familias_categorias.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Familias de categorías cargadas desde config/ ({len(data)} familias)")
        return data
    except FileNotFoundError:
        return default
    except Exception as e:
        logger.warning(f"Error al cargar familias_categorias.json: {e}. Usando valores por defecto.")
        return default


_FILTRO_RUIDO = _cargar_filtro_ruido()
_FAMILIAS_CATEGORIAS = _cargar_familias_categorias()

SYSTEM_PROMPT = """Eres AmiBot, el asistente oficial de la Biblioteca Universitaria.
Tu objetivo es responder de forma clara, directa y precisa a las dudas de los estudiantes, utilizando EXCLUSIVAMENTE la información provista en el CONTEXTO.

REGLAS CRÍTICAS:
1. BASADO EN CONTEXTO: Usa solo los datos del contexto. Si el contexto menciona un procedimiento, explícalo paso a paso sin omitir advertencias.
2. COMPRENSIÓN SEMÁNTICA: El usuario puede usar sinónimos (ej: "extravié" = "perdí", "plata" = "multa"). Analiza el significado, no solo las palabras exactas.
3. CERO RELLENO: Responde directamente. NO empieces con frases como "Según el contexto...", "El texto dice..." o "Hola, te ayudo".
4. LÍMITE FACTUAL: Si el contexto claramente NO guarda relación con la pregunta, responde únicamente con: "No encontré información."

CONTEXTO: 
{contexto}

PREGUNTA DEL ESTUDIANTE: 
{pregunta}

RESPUESTA:"""


def es_ruido_catalogo(pregunta: str, respuesta: str) -> bool:
    """Evita que consultas generales de libros devuelvan castigos, salvo que el usuario pregunte por ellos o por devolución/pérdida."""
    p_lower = pregunta.lower()
    r_lower = respuesta.lower()
    
    palabras_castigo = _FILTRO_RUIDO.get("palabras_castigo", [])
    palabras_especificas = _FILTRO_RUIDO.get("palabras_especificas", [])
    excepciones = _FILTRO_RUIDO.get("excepciones", [])
    
    # Si la respuesta contiene una palabra de excepción configurada, nunca se filtra
    if excepciones and any(e in r_lower for e in excepciones):
        return False
    
    # Si la pregunta ya busca una palabra de sanción (ej: "¿Cuál es la multa?"), la respuesta NO es ruido.
    if any(w in p_lower for w in palabras_castigo):
        return False

    # Si la pregunta es específicamente sobre devoluciones o pérdidas, la respuesta NO es ruido.
    if any(w in p_lower for w in palabras_especificas):
        return False

    if "libro" in p_lower and any(x in r_lower for x in palabras_castigo):
        return True

    return False


def es_respuesta_critica(texto: str) -> bool:
    """Determina si una respuesta contiene datos factuales que NO deben ser reformulados por el LLM.
    
    Protege: URLs, horarios, montos, procedimientos con pasos, credenciales, 
    y cualquier información donde la precisión literal es crítica.
    """
    texto_lower = texto.lower()
    
    # Palabras clave de contenido factual sensible
    tiene_keyword = any(p in texto_lower for p in RESPUESTAS_CRITICAS)
    
    # Contiene URLs (https://, http://, .cl, .com)
    tiene_url = "http" in texto_lower or ".cl" in texto_lower or ".com" in texto_lower
    
    # Contiene montos o precios ($, CLP, pesos)
    tiene_monto = ('$' in texto and any(c.isdigit() for c in texto))
    
    # Contiene horarios (08:00, lunes a viernes, etc.)
    tiene_horario = ":" in texto and any(h in texto_lower for h in ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo", "hrs", "horas"])
    
    # Contiene pasos o procedimientos numerados
    tiene_procedimiento = any(f"{n}." in texto or f"{n})" in texto for n in range(1, 6))
    
    return tiene_keyword or tiene_url or tiene_monto or tiene_horario or tiene_procedimiento


def ejecutar_rag_general_hibrido(pregunta_limpia: str, query_vector, pregunta_original: str,
                                  datos_biblioteca, collection, corpus_bm25, intent: str = None):
    # Convertir query_vector a lista (soporta tensor de PyTorch o lista nativa)
    query_list = query_vector.cpu().numpy().tolist() if hasattr(query_vector, "cpu") else query_vector.tolist()
    
    top_k = 15
    # Consultar ChromaDB
    results = collection.query(
        query_embeddings=[query_list],
        n_results=top_k
    )
    
    indices_semanticos = [int(idx) for idx in results['ids'][0]]
    distances = results['distances'][0]
    
    # Mapear similitud coseno: sim = 1.0 - dist
    semantico_scores = {}
    for i, idx in enumerate(indices_semanticos):
        semantico_scores[idx] = 1.0 - distances[i]

    query_tokens = pregunta_limpia.split()
    
    # Safelock por si el índice BM25 llega nulo
    if corpus_bm25:
        scores_bm25_total = corpus_bm25.get_scores(query_tokens)
        indices_lexicos = np.argsort(scores_bm25_total)[::-1][:top_k].tolist()
    else:
        indices_lexicos = []

    # Reciprocal Rank Fusion (k=60)
    k_rrf = 60
    scores_rrf = {}
    for rank, idx in enumerate(indices_semanticos):
        scores_rrf[idx] = scores_rrf.get(idx, 0) + 1.0 / (k_rrf + rank + 1)
    for rank, idx in enumerate(indices_lexicos):
        scores_rrf[idx] = scores_rrf.get(idx, 0) + 1.0 / (k_rrf + rank + 1)

    indices_rrf = sorted(scores_rrf, key=scores_rrf.get, reverse=True)[:5]
    
    # Calcular scores de similitud coseno para los candidatos finales
    candidatos_con_score = []
    for idx in indices_rrf:
        if idx >= len(datos_biblioteca):
            logger.warning(f"Ignorando ID fantasma {idx} proveniente de ChromaDB antiguo.")
            continue
            
        if idx in semantico_scores:
            base_score = semantico_scores[idx]
        else:
            try:
                doc_data = collection.get(ids=[str(idx)], include=['embeddings'])
                if doc_data and doc_data.get('embeddings') is not None and len(doc_data['embeddings']) > 0:
                    doc_emb = doc_data['embeddings'][0]
                    u = np.array(query_list)
                    v = np.array(doc_emb)
                    sim = np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v))
                    base_score = float(sim)
                else:
                    base_score = 0.0
            except Exception as e:
                logger.error(f"Error al calcular similitud coseno al vuelo para idx {idx}: {e}")
                base_score = 0.0

        # Aplicar boost si la categoría del candidato coincide con la intención detectada
        if intent and intent != "rag_general":
            candidato = datos_biblioteca[idx]
            cand_cat = candidato.get('categoria', '')
            match_intent = False
            
            # Boost dinámico universal para cualquier categoría
            if intent == cand_cat:
                match_intent = True
            # Agrupaciones lógicas cargadas desde config/familias_categorias.json
            elif cand_cat in _FAMILIAS_CATEGORIAS.get(intent, []):
                match_intent = True
                
            if match_intent:
                base_score += 0.40
                logger.info(f"Aplicando boost de intención '{intent}' a candidato idx {idx} (categoría '{cand_cat}'). Score final: {base_score:.4f}")

        candidatos_con_score.append((base_score, idx))

    # Re-ordenar candidatos por su score (con boost aplicado) descendente
    candidatos_con_score.sort(key=lambda x: x[0], reverse=True)

    respuesta_final, estado = None, "escalado_humano"
    score_final = candidatos_con_score[0][0] if candidatos_con_score else 0
    contexto_recuperado = None
    contexto_idx = None
    llm_usado = 0

    for score, idx in candidatos_con_score:
        candidato = datos_biblioteca[idx]
        text_bot = candidato['bot']

        if es_ruido_catalogo(pregunta_limpia, text_bot):
            continue

        if score >= UMBRAL_BAJO:
            respuesta_cruda = candidato['bot']
            score_final = score
            contexto_recuperado = respuesta_cruda
            contexto_idx = idx

            if es_respuesta_critica(respuesta_cruda):
                respuesta_final, estado = respuesta_cruda, "rag_textual"
                llm_usado = 0
            else:
                try:
                    prompt_final = SYSTEM_PROMPT.replace("{contexto}", respuesta_cruda).replace("{pregunta}", pregunta_original)
                    resp = ollama.chat(
                        model=OLLAMA_MODEL,
                        messages=[{'role': 'user', 'content': prompt_final}],
                        options={'temperature': 0.0, 'num_predict': 100}
                    )
                    salida_llm = resp['message']['content'].strip()
                    llm_usado = 1
                    
                    # Si Ollama entrega un string en blanco, caemos al texto seguro del JSON
                    if not salida_llm:
                        respuesta_final = respuesta_cruda
                        estado = "rag_generado_vacio_fallback"
                    else:
                        respuesta_final = salida_llm
                        estado = "rag_generado"

                except Exception as e:
                    logger.warning(f"Ollama no disponible, usando respuesta textual: {e}")
                    respuesta_final = respuesta_cruda
                    estado = "rag_textual_fallback"
                    llm_usado = 0
            break

    if not respuesta_final:
        respuesta_final = "Lo siento, no tengo información exacta para responder a tu duda sobre ese tema en particular. Por favor, consulta directamente en el mesón de atención."

    return respuesta_final, round(score_final, 4), estado, contexto_recuperado, contexto_idx, llm_usado

