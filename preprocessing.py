"""
Módulo de preprocesamiento de texto.
Corrige: F.1 (import string al top), F.4 (stopwords duplicadas) y normalización de tildes/signos en español.
Configuración externalizada: correcciones, términos inmunes y expansiones se cargan desde config/.
"""
import string
import re
import json
import os
import logging

logger = logging.getLogger(__name__)

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'config')


# ═══════════════════════════════════════════════
#  CARGA DE CONFIGURACIÓN EXTERNALIZADA
# ═══════════════════════════════════════════════

def _cargar_terminos_inmunes():
    """Carga términos inmunes desde config/terminos_inmunes.txt con fallback a valores por defecto."""
    default = [
        "universidad", "koha", "vufind", "amibot", "tesis", "locker", "lockers",
        "apa", "vancouver", "wifi", "biblioteca", "estudiante", "alumno",
        "lunes", "martes", "miercoles", "miércoles", "jueves", "viernes",
        "sabado", "sabados", "sábado", "sábados", "domingo", "domingos",
        "hemeroteca", "tesistas", "tesista", "scopus", "ebsco", "proquest",
        "catalogo", "prestamo", "devolucion", "meson", "computador", "computadores",
        "sciencedirect", "isbn", "issn", "doi"
    ]
    config_path = os.path.join(_CONFIG_DIR, 'terminos_inmunes.txt')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = [l.strip().lower() for l in f if l.strip() and not l.startswith('#')]
        if lines:
            logger.info(f"Términos inmunes cargados desde config/ ({len(lines)} términos)")
            return lines
        return default
    except FileNotFoundError:
        return default
    except Exception as e:
        logger.warning(f"Error al cargar terminos_inmunes.txt: {e}. Usando valores por defecto.")
        return default


def _cargar_correcciones():
    """Carga correcciones ortográficas desde config/correcciones_ortograficas.json."""
    default = {
        "waifai": "wifi", "wifai": "wifi", "orario": "horario",
        "orarios": "horarios", "livro": "libro", "livros": "libros",
        "komo": "como", "kiero": "quiero", "q": "que",
        "xq": "por que", "xque": "por que", "pa": "para",
        "biblio": "biblioteca", "tezis": "tesis", "tesi": "tesis",
        "tezs": "tesis", "dondevestan": "donde estan", "prestam": "prestamo",
        "tnego": "tengo", "sciencie": "science", "sciencia": "ciencia",
        "devolder": "devolver"
    }
    config_path = os.path.join(_CONFIG_DIR, 'correcciones_ortograficas.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Correcciones ortográficas cargadas desde config/ ({len(data)} entradas)")
        return data
    except FileNotFoundError:
        return default
    except Exception as e:
        logger.warning(f"Error al cargar correcciones_ortograficas.json: {e}. Usando valores por defecto.")
        return default


def _cargar_expansiones():
    """Carga expansiones de intención desde config/expansiones_intenciones.json."""
    default = {
        "extender": "renovacion plazo",
        "alargar": "renovacion plazo",
        "estirar": "renovacion plazo",
        "no alcanzo a ir": "renovacion plazo",
        "devolver": "devolucion entrega",
        "entregar": "devolucion entrega",
        "retirar": "prestamo pedir",
        "sacar": "prestamo pedir",
        "llevar": "prestamo pedir",
    }
    config_path = os.path.join(_CONFIG_DIR, 'expansiones_intenciones.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Expansiones de intención cargadas desde config/ ({len(data)} entradas)")
        return data
    except FileNotFoundError:
        return default
    except Exception as e:
        logger.warning(f"Error al cargar expansiones_intenciones.json: {e}. Usando valores por defecto.")
        return default


# ═══════════════════════════════════════════════
#  INICIALIZACIÓN CON CONFIG EXTERNALIZADA
# ═══════════════════════════════════════════════

try:
    from spellchecker import SpellChecker
    spell = SpellChecker(language='es')
    # Prevenimos que el corrector altere palabras clave de la institución o del RAG
    terminos_institucionales = _cargar_terminos_inmunes()
    spell.word_frequency.load_words(terminos_institucionales)
except ImportError:
    spell = None
    logger.warning("pyspellchecker no está instalado. Autocorrección predictiva desactivada.")

# Puntuación extendida para capturar apertura de interrogación y exclamación del español
PUNTUACION_ESPANOL = string.punctuation + '¿¡'

CORRECCIONES_RAPIDAS = _cargar_correcciones()

# Stopwords deduplicadas y cubriendo pares ortográficos con/sin tilde
STOPWORDS = {
    # Interrogativos
    "que", "qué", "como", "cómo", "donde", "dónde", "cuando", "cuándo",
    "cual", "cuál", "cuales", "cuáles", "cuanto", "cuánto", "cuanta", "cuánta",
    "cuantos", "cuántos", "cuantas", "cuántas", "quien", "quién", "quienes", "quiénes",
    # Verbos modales
    "puedo", "puedes", "puede", "podemos", "podeis", "pueden",
    "quisiera", "quiero", "quieres", "quiere", "queremos", "quereis", "quieren",
    "necesito", "necesitas", "necesita", "necesitamos", "necesitais", "necesitan",
    # Verbos comunes
    "hay", "tienen", "tiene", "tenemos", "teneis", "está", "esta", "están", "estan",
    "hacer", "hago", "haces", "hace", "hacemos", "haceis", "hacen",
    # Artículos
    "un", "una", "unos", "unas", "el", "él", "la", "los", "las",
    # Preposiciones
    "a", "al", "ante", "bajo", "cabe", "con", "contra", "de", "del",
    "desde", "durante", "en", "entre", "hacia", "hasta", "mediante",
    "para", "por", "según", "segun", "sin", "so", "sobre", "tras", "versus", "vía", "via",
    # Pronombres y adverbios
    "me", "te", "se", "nos", "os", "lo", "le", "les", "mas", "más",
    "mi", "tu", "su", "mis", "tus", "sus",
    # Slang chileno
    "onde", "pa", "po", "pos", "poh", "pue", "pu", "tonce", "tonces",
    "cachai", "cachay", "weon", "wn", "wea", "hueon", "huea", "ctm",
    "porfa", "plis", "bro", "hermano", "socio", "compadre"
}

EXPANSION_INTENCIONES = _cargar_expansiones()


def preprocesar_consulta(texto: str) -> str:
    """Elimina puntuación del español y stopwords del texto. Ideal para BM25 (bag-of-words)."""
    texto = texto.translate(str.maketrans('', '', PUNTUACION_ESPANOL.replace('-', '')))
    palabras = texto.lower().split()
    palabras_filtradas = [p for p in palabras if p not in STOPWORDS]
    return " ".join(palabras_filtradas)


def preprocesar_para_embeddings(texto: str) -> str:
    """Elimina puntuación pero MANTIENE stopwords. Los modelos de embeddings
    necesitan texto natural para capturar la semántica completa.
    Sin embargo, remueve palabras de contexto global que envenenan el espacio semántico.
    Ej: 'cómo puedo devolver un libro en la biblioteca' → 'como puedo devolver un libro en la'
    """
    texto = texto.translate(str.maketrans('', '', PUNTUACION_ESPANOL.replace('-', '')))
    palabras = texto.lower().split()
    
    # Remover ruido de contexto global
    palabras_limpias = [p for p in palabras if p not in ["biblioteca", "universidad"]]
    return ' '.join(palabras_limpias)


def pre_corregir_rapido(texto: str) -> str:
    """Aplica correcciones ortográficas usando diccionario estricto y luego spellchecker predictivo."""
    texto_sin_signos = texto.translate(str.maketrans('', '', PUNTUACION_ESPANOL))
    texto_limpio = re.sub(r'\s+', ' ', texto_sin_signos.lower().strip())
    palabras = texto_limpio.split()
    
    palabras_corregidas = []
    for p in palabras:
        if p in CORRECCIONES_RAPIDAS:
            palabras_corregidas.append(CORRECCIONES_RAPIDAS[p])
        elif spell and p not in STOPWORDS and not p.isdigit():
            # Spellchecker predictivo (solo para palabras no triviales)
            corr = spell.correction(p)
            palabras_corregidas.append(corr if corr else p)
        else:
            palabras_corregidas.append(p)
            
    return " ".join(palabras_corregidas)


def expandir_intencion(texto: str) -> str:
    """Agrega keywords de intención para mejorar el matching semántico."""
    texto_lower = texto.lower()
    for clave, expansion in EXPANSION_INTENCIONES.items():
        if clave in texto_lower:
            return f"{texto} {expansion}"
    return texto


def enmascarar_pii(texto: str) -> str:
    """Detecta y enmascara información sensible (PII) como RUTs, correos y teléfonos.
    Útil para auditoría y logs respetando la privacidad del estudiante.
    """
    if not texto:
        return texto

    # 1. Enmascarar correos electrónicos: ejemplo@correo.cl -> eje***@correo.cl
    def repl_email(match):
        email = match.group(0)
        local, domain = email.split('@', 1)
        if len(local) > 3:
            local_masked = f"{local[:3]}***"
        else:
            local_masked = "***"
        return f"{local_masked}@{domain}"

    texto = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', repl_email, texto)

    # 2. Enmascarar RUTs chilenos: 19876543-K o 19.876.543-k o 19876543k
    def repl_rut(match):
        rut_completo = match.group(0)
        rut_limpio = re.sub(r'[^0-9kK]', '', rut_completo)
        if len(rut_limpio) > 4:
            return f"{rut_limpio[:4]}*****"
        return "*****"

    # Regex para RUT chileno (7 a 9 digitos + DV k/K/numero)
    texto = re.sub(r'\b\d{1,2}(?:\.?\d{3}){2}-?[\dKk]\b', repl_rut, texto)

    # 3. Enmascarar números telefónicos (chilenos o formato internacional estándar)
    def repl_tel(match):
        tel = match.group(0)
        tel_limpio = re.sub(r'[^0-9+]', '', tel)
        if tel_limpio.startswith('+'):
            return f"{tel_limpio[:4]}*****"
        return f"{tel_limpio[:3]}*****"

    texto = re.sub(r'(?:\+?56\s?9\s?\d{4}\s?\d{4}|\b9\s?\d{4}\s?\d{4}\b)', repl_tel, texto)

    return texto
