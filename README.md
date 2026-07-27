# AmiBot — Chatbot RAG Híbrido para Biblioteca Universitaria

> Asistente virtual basado en **Retrieval-Augmented Generation (RAG) híbrido**, diseñado para responder consultas de estudiantes en una biblioteca universitaria real. Desplegado en producción atendiendo a ~2,000 estudiantes.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![Ollama](https://img.shields.io/badge/LLM-Llama_3.2-orange)
![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-purple)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)

---

## Arquitectura

```
┌────────────────┐     ┌─────────────────────────────────────────────┐
│   Frontend     │     │              Backend (FastAPI)               │
│  Widget JS     │────▶│                                             │
│  (Vanilla)     │     │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
└────────────────┘     │  │ Guardrails│─▶│  Router  │─▶│ RAG Engine│  │
                       │  │ + PII Mask│  │(Intención)│  │ (Híbrido) │  │
                       │  └──────────┘  └──────────┘  └─────┬────┘  │
                       │                                     │       │
                       │                    ┌────────────────┼───┐   │
                       │                    │                │   │   │
                       │               ┌────▼───┐  ┌────────▼┐  │   │
                       │               │ BM25   │  │ChromaDB │  │   │
                       │               │(Léxico)│  │(Semánt.)│  │   │
                       │               └────┬───┘  └────┬────┘  │   │
                       │                    │           │       │   │
                       │                    └─────┬─────┘       │   │
                       │                          │             │   │
                       │                    ┌─────▼─────┐       │   │
                       │                    │    RRF     │       │   │
                       │                    │  (Fusión)  │       │   │
                       │                    └─────┬─────┘       │   │
                       │                          │             │   │
                       │                    ┌─────▼─────┐       │   │
                       │                    │  Ollama   │       │   │
                       │                    │(Llama 3.2)│       │   │
                       │                    └───────────┘       │   │
                       │                                        │   │
                       │  ┌──────────┐                          │   │
                       │  │ SQLite   │◀─── Telemetría ──────────┘   │
                       │  │ (WAL)    │                              │
                       │  └──────────┘                              │
                       └────────────────────────────────────────────┘
```

**Stack Técnico:**

| Capa | Tecnología |
|---|---|
| API | FastAPI + Uvicorn (async) |
| Motor de búsqueda | RAG Híbrido: BM25 (léxico) + Embeddings (semántico) + RRF (fusión) |
| Base vectorial | ChromaDB (persistente, espacio coseno) |
| LLM | Ollama — Llama 3.2:1b (local, sin APIs externas) |
| Embeddings | paraphrase-multilingual-MiniLM-L12-v2 (multilingüe) |
| Telemetría | SQLite con WAL mode (thread-safe) |
| Frontend | Widget JavaScript vanilla inyectado en catálogo existente |
| Despliegue | systemd + Docker (bare-metal) |

---

## Características Técnicas

### Motor RAG Híbrido
- **BM25 (Okapi):** Búsqueda léxica por frecuencia de términos.
- **Embeddings semánticos:** Búsqueda por similitud de significado vía ChromaDB.
- **Reciprocal Rank Fusion (RRF):** Fusión de rankings con k=60 para combinar ambos enfoques.
- **Boost de intención configurable:** +0.40 al score cuando la categoría coincide con la intención detectada.

### Router de Intenciones
- Clasificación determinista por reglas configurables (JSON externo).
- Clasificación semántica como fallback (cosine similarity con embeddings de intenciones).
- Manejo de ambigüedad con delta configurable.
- Soporte para exclusiones y contexto requerido por regla.

### Seguridad y Privacidad
- **PII Masking automático:** RUTs, emails y teléfonos se enmascaran antes del logging.
- **Guardrails de dominio:** Filtrado de consultas fuera de ámbito en tiempo real.
- **Bypass inteligente de LLM:** Respuestas factuales (precios, URLs, horarios) van directo sin pasar por el modelo para preservar precisión.
- **Rate limiting:** SlowAPI con límites configurables por endpoint.
- **API Key:** Protección de endpoints con token en header.
- **CORS restringido:** Solo orígenes autorizados.

### Filtro Anti-Ruido
- Evita que búsquedas genéricas de libros retornen información de multas/sanciones.
- Configurable vía JSON externo con palabras de castigo, específicas y excepciones.

### Herramientas de Administración
- **CLI unificada** (`gestionar_amibot.py`): Módulos para gestión del router, correcciones, guardrails, expansiones, filtros.
- **Dashboard de telemetría** (`ver_consultas.py`): TUI en tiempo real con Rich.
- **Análisis de brechas** (`analizar_brechas.py`): Identificación automática de preguntas sin respuesta.
- **Carga masiva** (`cargar_conocimiento_masivo.py`): Importación desde archivos TSV.

### Testing
- **Unitarios:** Con mocking de dependencias pesadas (torch, sentence-transformers, ollama).
- **Regresión E2E:** Suite completa con patrón **LLM-as-a-Judge** para validación semántica.
- **Estrés:** Tests de carga concurrente para validar rate limiting y estabilidad.

---

## Estructura del Proyecto

```
amibot/
├── main.py                        # API FastAPI — punto de entrada
├── config.py                      # Configuración centralizada (env vars)
├── rag_engine.py                  # Motor RAG Híbrido (BM25 + Semántico + RRF)
├── router.py                      # Router de intenciones (determinista + semántico)
├── preprocessing.py               # Pipeline NLP: corrección, stopwords, PII
├── guardrails.py                  # Seguridad de dominio y chitchat
├── db.py                          # Telemetría SQLite (WAL, thread-safe)
├── vector_db.py                   # Integración ChromaDB
├── conocimiento_base_ollama.json  # Base de conocimiento (ejemplo)
├── chitchat_patterns.json         # Patrones regex de conversación casual
├── config/                        # Configuración externalizada (JSON/TXT)
│   ├── reglas_router.json
│   ├── correcciones_ortograficas.json
│   ├── terminos_inmunes.txt
│   ├── expansiones_intenciones.json
│   ├── guardrails_dominio.json
│   ├── familias_categorias.json
│   └── filtro_ruido.json
├── tools/                         # Herramientas de administración
│   ├── gestionar_amibot.py        # CLI unificada de configuración
│   ├── agregar_conocimiento.py
│   ├── cargar_conocimiento_masivo.py
│   ├── ver_consultas.py           # Dashboard de telemetría (Rich TUI)
│   ├── analizar_brechas.py
│   └── backup_db.sh
├── frontend/
│   └── chat-widget.js             # Widget del chatbot (vanilla JS)
├── tests/
│   ├── test_unitarios.py
│   ├── test_regresion.py          # E2E con LLM-as-a-Judge
│   ├── test_router.py
│   └── test_estres.py
├── docs/                          # Documentación técnica
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Inicio Rápido

### Requisitos previos
- Python 3.11+
- [Ollama](https://ollama.com/) instalado con el modelo `llama3.2:1b`

### Instalación local

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/amibot.git
cd amibot

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Descargar el modelo de Ollama
ollama pull llama3.2:1b

# Iniciar el servidor
python3 main.py
```

### Con Docker

```bash
docker-compose up --build
```

### Verificar funcionamiento

```bash
# Health check
curl http://localhost:8000/

# Consulta de prueba
curl -X POST http://localhost:8000/consultar \
  -H "Content-Type: application/json" \
  -H "X-Chatbot-Token: CHANGE_ME_IN_PRODUCTION" \
  -d '{"pregunta": "¿cuál es el horario de la biblioteca?"}'
```

---

## Ejecución de Tests

```bash
# Tests unitarios
python3 -m pytest tests/test_unitarios.py -v

# Tests de regresión E2E (requiere servidor corriendo + Ollama)
python3 tests/test_regresion.py

# Tests de estrés
python3 tests/test_estres.py
```

---

## Métricas de Producción

| Métrica | Valor |
|---|---|
| Precisión (Accuracy) | > 90% |
| Latencia promedio | ~400ms |
| Latencia P95 | < 1.5s |
| Uptime | 99.9% (systemd auto-restart) |
| Base de conocimiento | ~80 entradas categorizadas |

---

## Licencia

Copyright (c) 2026 Misael (Misa714). Todos los derechos reservados.

Este repositorio y su código fuente están publicados únicamente con fines de portafolio técnico y evaluación profesional.

Queda estrictamente prohibida la copia, reproducción, modificación, distribución o uso comercial/no comercial de este código fuente sin la autorización previa y por escrito del autor.
