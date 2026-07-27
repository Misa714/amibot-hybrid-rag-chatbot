"""
Módulo de guardrails — Validación, chit-chat y memoria de sesión.
Corrige: E.2 (patrones externalizados), C.4 (sesiones con TTL).
Configuración externalizada: palabras fuera de dominio y ambiguas se cargan desde config/.
"""
import re
import json
import os
import logging
from cachetools import TTLCache
from config import MAX_HISTORIAL, SESSION_TTL_SECONDS, CHITCHAT_PATTERNS_PATH

logger = logging.getLogger(__name__)

# Memoria de sesiones con TTL automático (Resuelve ítem C.4)
historial_sesiones: TTLCache = TTLCache(maxsize=1000, ttl=SESSION_TTL_SECONDS)


def _cargar_guardrails_dominio():
    """Carga palabras fuera de dominio y ambiguas desde config/guardrails_dominio.json."""
    default_ood = {
        "vacacion", "vacaciones", "arancel", "aranceles", "matricula", "matrícula",
        "beca", "becas", "financiamiento",
        "admision", "admisión", "inscripcion", "inscripción",
        "certificado", "certificados", "nota", "notas"
    }
    default_amb = {
        "medicina", "psicologia", "psicología", "ingenieria", "ingeniería",
        "derecho", "enfermeria", "enfermería", "tesis", "libro", "libros",
        "prestamo", "revista", "revistas", "catalogo"
    }
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'guardrails_dominio.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ood = set(data.get('out_of_domain', []))
        amb = set(data.get('ambiguous_single_words', []))
        logger.info(f"Guardrails cargados desde config/ ({len(ood)} bloqueadas, {len(amb)} ambiguas)")
        return ood, amb
    except FileNotFoundError:
        return default_ood, default_amb
    except Exception as e:
        logger.warning(f"Error al cargar guardrails_dominio.json: {e}. Usando valores por defecto.")
        return default_ood, default_amb


OUT_OF_DOMAIN, AMBIGUOUS_SINGLE_WORDS = _cargar_guardrails_dominio()


def validar_guardrail(pregunta: str):
    """Valida que la pregunta sea procesable dentro del dominio bibliotecario."""
    q_limpia = pregunta.lower().strip()
    palabras = set(re.findall(r"\w+", q_limpia))

    if len(palabras) <= 1:
        palabras_list = list(palabras)
        if not palabras or palabras_list[0] in AMBIGUOUS_SINGLE_WORDS:
            return False, f"¿Podrías especificar tu consulta sobre '{pregunta}'? Por ejemplo: buscar libros, pedir una tesis, o saber la ubicación del material."
        return False, "Necesito más información para ayudarte. Por favor formula tu consulta con más detalle."

    # Comparar por intersección de palabras exactas para evitar falsos positivos por subcadenas (ej. "nota" en "anotación")
    if palabras.intersection(OUT_OF_DOMAIN):
        return False, "Solo puedo responder consultas estrictamente relacionadas con los servicios, recursos y normativas de la Biblioteca Universitaria."
    return True, "continue"


class ClasificadorIntencionChitChat:
    """Clasificador de intenciones fuera de ámbito basado en regex."""

    def __init__(self):
        try:
            with open(CHITCHAT_PATTERNS_PATH, 'r', encoding='utf-8') as f:
                patrones = json.load(f)
            self.intenciones = {k: (v["patron"], v["respuesta"]) for k, v in patrones.items()}
            logger.info(f"Cargadas {len(self.intenciones)} categorías chit-chat desde archivo.")
        except Exception as e:
            logger.warning(f"No se encontró {CHITCHAT_PATTERNS_PATH}. Cargando fallback en memoria: {e}")
            # Fallback en memoria por si el archivo JSON aún no se crea en el directorio
            self.intenciones = {
                "insulto": (r"(?i)(idiota|estupido|imbecil|tonto|callate)", "Por favor, mantengamos un lenguaje respetuoso dentro de la plataforma."),
                "comida": (r"(?i)(pizza|hamburguesa|comida|hambre|cafeteria|almuerzo)", "No ofrezco servicios de alimentación. La cafetería se encuentra en el edificio central."),
            }

    def evaluar(self, pregunta: str):
        pregunta_lower = pregunta.lower()
        for categoria, (patron, respuesta) in self.intenciones.items():
            if re.search(patron, pregunta_lower):
                return True, categoria, respuesta
        return False, None, None


def completar_contexto(pregunta: str, historial: list) -> str:
    """Completa preguntas cortas usando la pregunta anterior como pivote."""
    if len(pregunta.split()) >= 5 or not historial:
        return pregunta

    # Se limpia la puntuación inicial para que startswith evalúe la primera letra real
    q_test = pregunta.lower().lstrip('¿¡.- ')
    
    # Espacios añadidos a los conectores cortos para evitar colisiones con palabras reales
    referencias = ["y ", "los ", "las ", "el ", "como", "cómo", "cuando", "cuándo", "donde", "dónde", "por que", "por qué"]

    if any(q_test.startswith(ref) for ref in referencias):
        ultimo = historial[-1]
        # Se reemplaza el guión (-) por un punto (.) para favorecer la estructura natural en el modelo de embeddings
        return f"{ultimo['pregunta']}. {pregunta}"

    return pregunta


def obtener_historial(sesion_id: str) -> list:
    return list(historial_sesiones.get(sesion_id, []))


def actualizar_historial(sesion_id: str, pregunta: str, respuesta: str):
    historial = list(historial_sesiones.get(sesion_id, []))
    historial.append({"pregunta": pregunta, "respuesta": respuesta})
    if len(historial) > MAX_HISTORIAL:
        historial = historial[-MAX_HISTORIAL:]
    historial_sesiones[sesion_id] = historial
