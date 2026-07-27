"""
Módulo de enrutamiento — Router de 2 capas (reglas determinísticas + embeddings).
"""
import json
import logging
import os
from sentence_transformers import util

logger = logging.getLogger(__name__)

# Descripciones semánticas para cada macro-intención
MACRO_INTENCIONES = {
    "catalogo": "consulta disponibilidad buscar libros novelas sagas catálogo biblioteca buscar título autor ejemplares stock existe vufind koha",
    "lockers": "casilleros lockers llave llaves mochila guardar pertenencias casillero mochilas perder llave dejar cosas",
    "salas_estudio": "salas de estudio salas de tesis reservar sala cubículos llaves de salas estudiar grupal",
    "bases_datos": "bases de datos revistas indexadas papers artículos científicos scopus web of science ebsco proquest sciencedirect investigación",
    "prestamos": "pedir libros prestados renovar días de préstamo notebooks calculadoras multas bloqueos moroso suspender",
    "recursos_institucionales": "logotipos logos manual de estilo formato vancouver formato apa referencias bibliográficas apa 7a edición investigación institucional pautas",
    "horario": "horarios horario atencion abierto cerrado hora de cierre a que hora abren fines de semana feriados"
}


def init_intent_embeddings(model):
    """Pre-computa los embeddings extrayendo dinámicamente las categorías del JSON."""
    json_path = os.path.join(os.path.dirname(__file__), 'conocimiento_base_ollama.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        dinamicas = {}
        for item in datos:
            cat = item.get("categoria")
            preguntas = item.get("usuario", "")
            if cat and preguntas:
                if cat in dinamicas:
                    dinamicas[cat] += " " + preguntas
                else:
                    dinamicas[cat] = preguntas
                    
        # Eliminar duplicados en las descripciones y limpiar ruido global
        for cat in dinamicas:
            palabras = list(set(dinamicas[cat].split()))
            if "biblioteca" in palabras:
                palabras.remove("biblioteca")
            if "universidad" in palabras:
                palabras.remove("universidad")
            dinamicas[cat] = " ".join(palabras)
            
        logger.info(f"Router dinámico cargado con {len(dinamicas)} categorías: {list(dinamicas.keys())}")
        intenciones = dinamicas
    except Exception as e:
        logger.warning(f"Fallo al cargar intents dinámicos, usando fallback: {e}")
        intenciones = MACRO_INTENCIONES

    return {k: model.encode(v, convert_to_tensor=True) for k, v in intenciones.items()}


def _cargar_reglas_router():
    """Carga reglas del router desde config/reglas_router.json con fallback a None."""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'reglas_router.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            reglas = json.load(f)
        logger.info(f"Router: {len(reglas)} reglas cargadas desde config/reglas_router.json")
        return reglas
    except FileNotFoundError:
        logger.info("config/reglas_router.json no encontrado. Usando reglas hardcodeadas por defecto.")
        return None
    except Exception as e:
        logger.warning(f"Error al cargar reglas_router.json: {e}. Usando reglas por defecto.")
        return None


_REGLAS_EXTERNAS = _cargar_reglas_router()


def detectar_intencion_dura(texto: str) -> str:
    """PASO 1: Reglas determinísticas para cortocircuitar drifts semánticos y evitar falsos positivos."""
    if _REGLAS_EXTERNAS is not None:
        return _detectar_desde_json(texto)
    return _detectar_hardcodeada(texto)


def _detectar_desde_json(texto: str) -> str:
    """Evalúa reglas cargadas desde JSON. Primera regla que matchea gana."""
    t = texto.lower()
    for regla in _REGLAS_EXTERNAS:
        palabras = regla.get("palabras", [])
        exclusiones = regla.get("exclusiones", [])
        requiere_contexto = regla.get("requiere_contexto", [])

        if not any(p in t for p in palabras):
            continue
        if exclusiones and any(e in t for e in exclusiones):
            continue
        if requiere_contexto and not any(c in t for c in requiere_contexto):
            continue

        return regla["intent"]
    return "rag_general"


def _detectar_hardcodeada(texto: str) -> str:
    """Fallback: reglas originales hardcodeadas (se usa solo si no existe config/reglas_router.json)."""
    t = texto.lower()

    palabras_bd = ["base de datos", "bases de datos", "scopus", "web of science", "wos", "ebsco", "proquest", "sciencedirect"]
    if any(p in t for p in palabras_bd):
        return "bases_datos"

    palabras_catalogo = ["buscar libro", "catalogo", "catálogo", "principito", "novela", "autor", "tienen el libro"]
    if any(p in t for p in palabras_catalogo):
        return "catalogo"

    palabras_lockers = ["casillero", "locker", "mochila", "mochilas"]
    tiene_palabra_locker = any(p in t for p in palabras_lockers)
    tiene_llave_locker = "llave" in t and not any(x in t for x in ["sala", "estudio", "tesis", "computador"])
    if tiene_palabra_locker or tiene_llave_locker:
        return "lockers"

    palabras_salas = ["sala", "salas", "cubiculo", "cubículo"]
    tiene_palabra_sala = any(p in t for p in palabras_salas)
    tiene_estudio_salas = ("estudio" in t or "estudiar" in t) and any(x in t for x in ["reservar", "reserva", "sala", "salas", "llave", "llaves", "pedir"])
    if tiene_palabra_sala or tiene_estudio_salas:
        return "salas_estudio"

    palabras_tesis = ["tesis", "tesina", "trabajo de titulo", "trabajo de título"]
    if any(p in t for p in palabras_tesis) and not any(x in t for x in ["sala", "cubículo", "cubiculo", "reservar", "estudio", "tesistas"]):
        return "tesis"

    palabras_prestamo = ["pedir", "prestar", "prestado", "llevar", "cuantos libros", "renovar", "multa", "moroso", "bloqueado"]
    palabras_perdida = ["pierdo", "perdi", "perdió"]
    tiene_palabra_prestamo = any(p in t for p in palabras_prestamo)
    tiene_perdida_material = any(p in t for p in palabras_perdida) and any(x in t for x in ["libro", "revista", "computador", "calculadora", "material"])
    if (tiene_palabra_prestamo or tiene_perdida_material) and not any(x in t for x in ["sala", "locker", "casillero", "base de datos"]):
        return "prestamos"

    palabras_devolucion = ["devolver", "devolucion", "devolución", "entregar el libro", "entregar los libros", "donde dejo el libro"]
    if any(p in t for p in palabras_devolucion):
        return "devolucion"

    palabras_inst = ["logotipos", "logo", "manual de estilo", "vancouver", "formato apa", "apa 7", "referencias bibliográficas", "referencia apa", "cita apa", "citar apa", "documentación oficial", "documentacion oficial", "apoyo a trabajos", "trabajos finales"]
    if any(p in t for p in palabras_inst):
        return "recursos_institucionales"

    palabras_acceso = ["recuperar clave", "recuperar contraseña", "problemas con la contraseña", "no puedo ingresar", "no puedo entrar", "no me deja entrar", "cambiar mi clave", "cambiar mi contraseña", "contraseña de biblioteca", "clave de biblioteca", "problemas para entrar"]
    if any(p in t for p in palabras_acceso):
        return "bases_datos"

    palabras_horario = ["horario", "horarios", "atencion", "atención", "abren", "cierran", "abierto", "cerrado", "fin de semana", "fines de semana", "sabado", "sabados", "sábado", "sábados", "domingo", "domingos", "feriado", "feriados"]
    if any(p in t for p in palabras_horario):
        return "horario"

    return "rag_general"


def clasificar_intencion_industrial(query_vector, embeddings_intenciones, threshold_minimo=0.45, delta_ambiguedad=0.05):
    """PASO 2: Fallback a embeddings estructurados cuando las reglas no matchean."""
    scores_crudos = {
        intent: util.cos_sim(query_vector, vec).item()
        for intent, vec in embeddings_intenciones.items()
    }
    ranking = sorted(scores_crudos.items(), key=lambda x: x[1], reverse=True)
    top1_intent, top1_score = ranking[0]
    top2_intent, top2_score = ranking[1]

    margin = top1_score - top2_score
    debajo_del_minimo = top1_score < threshold_minimo
    es_ambiguo = margin < delta_ambiguedad

    intent_elegido = "rag_general" if (debajo_del_minimo or es_ambiguo) else top1_intent
    telemetria = {
        "intent_elegido": intent_elegido,
        "top1_intent": top1_intent, "top1_score": round(top1_score, 3),
        "top2_intent": top2_intent, "top2_score": round(top2_score, 3),
        "margin": round(margin, 3),
        "status": "low_score" if debajo_del_minimo else ("ambiguo" if es_ambiguo else "clear")
    }
    return intent_elegido, top1_score, telemetria



