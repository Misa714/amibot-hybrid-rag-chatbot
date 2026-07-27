# Base de Datos Relacional: SQLite (Telemetría)

Mientras ChromaDB se encarga del "cerebro" matemático del bot, AmiBot utiliza una segunda base de datos, **SQLite**, para actuar como su sistema de "memoria y auditoría".

En lugar de instalar motores pesados como MySQL o PostgreSQL, la decisión arquitectónica fue utilizar SQLite3 configurado en **Modo WAL (Write-Ahead Logging)**. Esto permite tener una base de datos ligera, guardada en un solo archivo físico en el servidor, pero que es capaz de manejar múltiples alumnos chateando al mismo tiempo sin sufrir bloqueos (*Database is locked*).

## 1. El Propósito: Analítica y Mejora Continua

El objetivo principal de esta base de datos relacional no es que el bot recuerde el pasado, sino registrar **Telemetría**.
Cada mensaje que envía un alumno y cada respuesta que genera AmiBot quedan registrados en tablas. Esto le permite al personal de la biblioteca:

* Descubrir cuáles son las dudas más frecuentes de los alumnos.
* Detectar qué preguntas fallan (para luego ir al JSON y agregar la respuesta faltante).
* Revisar el sistema de **Feedback (Likes/Dislikes)**: si un alumno califica negativamente una respuesta del bot, el registro en SQLite permite analizar por qué el algoritmo se equivocó en ese caso particular.

## 2. Privacidad y Seguridad: Enmascaramiento PII (Regex)

Guardar conversaciones reales en una base de datos institucional implica un riesgo grave: **Ley de Protección de Datos Personales**. Los alumnos suelen escribir datos sensibles (como su RUT, número telefónico o correo) en el chat.

Para evitar que el administrador de la base de datos tenga acceso a esta información privada, desarrollé un sistema de **Enmascaramiento Preventivo PII** (Información Personal Identificable):

1. Antes de que el mensaje del alumno se guarde en SQLite, el texto pasa por un filtro de Expresiones Regulares (Regex) en `preprocessing.py`.
2. Si el código detecta el patrón matemático de un RUT (ej: 8 números seguidos de un guion), o un correo, o un celular... lo censura automáticamente.
3. El mensaje original *"Mi RUT es 19876543-K y mi correo es juan@example.edu"* se guarda en la base de datos de telemetría como *"Mi RUT es 1987***** y mi correo es jua***@example.edu"*.

Gracias a esta arquitectura, AmiBot puede recolectar toda la estadística necesaria para mejorar la inteligencia del bot a futuro, pero garantizando el **100% de anonimato** y resguardando la privacidad de los estudiantes de la universidad.
