"""
Configuración centralizada del Chatbot Biblioteca.
Todas las rutas y parámetros se controlan desde aquí o vía variables de entorno.
"""
import os
from pathlib import Path

# Directorio base (donde vive este archivo)
BASE_DIR = Path(__file__).parent

# Base de datos
DB_PATH = os.environ.get("CHATBOT_DB_PATH", str(BASE_DIR / "consultas.db"))

# Base de conocimiento
KNOWLEDGE_PATH = os.environ.get("CHATBOT_KNOWLEDGE_PATH", str(BASE_DIR / "conocimiento_base_ollama.json"))

# Patrones chit-chat externalizados
CHITCHAT_PATTERNS_PATH = os.environ.get("CHATBOT_CHITCHAT_PATH", str(BASE_DIR / "chitchat_patterns.json"))

# Configuración SMTP para envío de correos (Formulario Humano)
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_SENDER = os.environ.get("SMTP_SENDER", "noreply@example.edu")
SMTP_RECEIVER = os.environ.get("SMTP_RECEIVER", "soporte@example.edu")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

# Modelos
EMBEDDING_MODEL = os.environ.get("CHATBOT_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
OLLAMA_MODEL = os.environ.get("CHATBOT_OLLAMA_MODEL", "llama3.2:1b")

# Umbrales RAG
UMBRAL_BAJO = float(os.environ.get("CHATBOT_UMBRAL_BAJO", "0.42"))
INTENT_THRESHOLD = float(os.environ.get("CHATBOT_INTENT_THRESHOLD", "0.35"))
INTENT_AMBIGUITY_DELTA = float(os.environ.get("CHATBOT_INTENT_DELTA", "0.12"))

# Rate limiting
RATE_LIMIT = os.environ.get("CHATBOT_RATE_LIMIT", "30/minute")

# CORS — Orígenes permitidos (configurables por variable de entorno)
_cors_env = os.environ.get(
    "CHATBOT_CORS_ORIGINS",
    "*,null,http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000,https://catalogo.example.edu,https://biblioteca.example.edu"
)
CORS_ORIGINS = [origin.strip() for origin in _cors_env.split(",") if origin.strip()]

# Sesión
MAX_HISTORIAL = 3
SESSION_TTL_SECONDS = 1800  # 30 minutos

# Validación de entrada
MAX_INPUT_LENGTH = 500

# Servidor
HOST = os.environ.get("CHATBOT_HOST", "127.0.0.1")
PORT = int(os.environ.get("CHATBOT_PORT", "8000"))

# Palabras clave de respuestas críticas (bypass de LLM)
RESPUESTAS_CRITICAS = [
    "contraseña", "clave", "wifi", "pass", "$", "simultáneamente", "simultaneamente", "hábiles", "habiles", "locker", "casillero", "computadores", "calculadoras", "reposición", "reposicion", "pagar", "multa", "beneficios"
]

# API Key de seguridad para proteger los endpoints expuestos
CHATBOT_API_KEY = os.environ.get("CHATBOT_API_KEY", "CHANGE_ME_IN_PRODUCTION")
