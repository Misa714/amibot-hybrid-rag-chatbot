# Router Semántico y Reglas Duras (Intent Routing)

AmiBot no depende ciegamente del motor RAG ni de la Inteligencia Artificial. Para garantizar que los estudiantes reciban respuestas institucionales estrictas en temas críticos (como accesos, claves o soporte), diseñé un **Router de Intenciones** en la capa media del backend (`router.py`).

Este sistema actúa como un "semáforo" que intercepta la pregunta antes y durante la búsqueda RAG, aplicando *Reglas Duras* (Hard Rules) para forzar comportamientos específicos.

---

## 1. Detección de Intenciones Críticas

El sistema escanea la consulta del estudiante buscando patrones clave (Reglas 1 a 7) que denotan urgencia o problemas de acceso institucionales.

**Ejemplo de palabras clave interceptadas:**
* "olvidé mi clave"
* "no puedo ingresar"
* "problemas con el correo"
* "recuperar contraseña"

Cuando el router detecta esta intención, sabe que no puede dejar que el LLM (Ollama) intente redactar una respuesta libre o inventada (Alucinación), ya que es un tema de soporte informático.

## 2. Ponderación Forzada (Intent Boosting)

En un motor RAG normal, el documento que mejor coincide semánticamente gana. Pero, ¿qué pasa si el sistema RAG se confunde con una pregunta ambigua sobre contraseñas?

Para solucionarlo, el Router aplica la técnica de **Intent Boosting**:
Si se detecta una intención de "Problemas de Acceso", el Router interviene en la clasificación de RRF (Reciprocal Rank Fusion) y le inyecta matemáticamente una bonificación de **`+0.25` de Score** (puntos extra) a la respuesta oficial de la base de datos que contiene el correo de soporte institucional (`soporte@example.edu`).

**Efecto:**
Al inyectar estos puntos extra, el artículo oficial salta forzosamente al Top #1 de resultados. Luego, debido al sistema de **Cortocircuito** (explicado en `motor_rag_hibrido.md`), el Score final es tan alto que aborta la conexión con el LLM y le dispara la respuesta exacta al estudiante en milisegundos. 

Esto garantiza un **100% de precisión** en temas de soporte vital.

---

## 3. Escalado a Humano (Fallback)

Otra regla dura del Router es la protección contra el ruido. Si un alumno hace una pregunta que no tiene ninguna relación con la biblioteca (ej: *"¿Quién ganó el mundial?"* o *"¿Cómo está el clima?"*):

1. Los motores RAG arrojarán Scores extremadamente bajos (similitud matemática cercana a cero).
2. El Router lee este Score final y, si está por debajo del umbral mínimo de confianza, activa el **Fallback**.
3. En lugar de derivar la pregunta al LLM, devuelve un texto enlatado: *"Lo siento, soy un asistente bibliotecario y no tengo información sobre eso. Si tienes dudas académicas, acércate al mesón."*

Gracias a este enrutador, AmiBot está blindado contra inyecciones de temas externos, protegiendo los recursos de la universidad.
