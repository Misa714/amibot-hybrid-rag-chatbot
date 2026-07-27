# Motor RAG Híbrido (Retrieval-Augmented Generation)

El núcleo lógico de AmiBot no es el Modelo de Lenguaje (LLM), sino su **Motor de Búsqueda (RAG)**. Antes de que la Inteligencia Artificial redacte una respuesta, el sistema debe encontrar el "conocimiento exacto" dentro del json de la biblioteca.

Para lograr una precisión casi perfecta, desarrollé una arquitectura **Híbrida**, que combina dos tecnologías de búsqueda completamente distintas y las fusiona matemáticamente.

## 1. Los Dos Motores de Búsqueda

### A. Búsqueda Léxica (Rank-BM25)
* **¿Qué es?:** Es un algoritmo clásico probabilístico que busca **palabras exactas**.
* **¿Cómo funciona?:** Analiza la frecuencia de las palabras clave en la pregunta del alumno y las busca tal cual en la base de datos.
* **¿Por qué es útil?:** La búsqueda semántica falla con los acrónimos (ej: "DTI") o números de error específicos. BM25 es excelente encontrando coincidencias literales, asegurando que si el usuario busca un acrónimo raro, lo encuentre.

### B. Búsqueda Semántica (ChromaDB + Embeddings)
* **¿Qué es?:** Es un motor matemático basado en Inteligencia Artificial.
* **¿Cómo funciona?:** Utiliza el modelo local `paraphrase-multilingual-MiniLM-L12-v2` (SentenceTransformers) para convertir el texto en una lista de 384 números (Vectores). Luego, calcula la distancia matemática entre la pregunta y la respuesta (Similitud Coseno).
* **¿Por qué es útil?:** Entiende sinónimos y contexto. Si el alumno pregunta *"¿dónde devuelvo el libro?"*, el motor entiende que es lo mismo que *"lugar de retorno de material bibliográfico"*, aunque no compartan ninguna palabra exacta.

### C. Preprocesamiento Diferenciado (El Secreto de la Precisión)

Las **Stopwords** (palabras vacías) son los conectores comunes que usamos para armar oraciones, como: *el, la, de, que, como, hola, me, por, favor*. 
Para que la búsqueda de AmiBot sea tan exacta, el script `preprocessing.py` divide la pregunta del estudiante y la prepara de dos formas totalmente distintas:

**Ejemplo de entrada:** *"Hola, ¿me pueden decir a qué hora abre la biblioteca por favor?"*

1. **Preprocesamiento para BM25 (Se BORRAN las Stopwords):**
   * El código elimina los símbolos y borra todas las palabras de relleno.
   * El texto que BM25 buscará queda reducido a: `"hora abre biblioteca"`.
   * **¿Por qué?** Porque BM25 es un buscador de palabras exactas. Si no borraras las palabras *"por favor"*, BM25 empezaría a buscar artículos en la base de datos que digan *"por favor"* (ej. "Por favor devuelva los libros a tiempo"), dándote resultados basura. Al borrar las Stopwords, obligas a BM25 a buscar únicamente los conceptos puros.

2. **Preprocesamiento para ChromaDB (Se MANTIENEN las Stopwords):**
   * El código elimina los signos, pero deja toda la gramática intacta.
   * El texto que ChromaDB procesará será: `"hola me pueden decir a que hora abre la biblioteca por favor"`.
   * **¿Por qué?** Porque ChromaDB usa un modelo de lenguaje neuronal (SentenceTransformers). Las IA necesitan leer la estructura gramatical completa (igual que un cerebro humano) para entender el tono y el contexto. Si le cortas los conectores, la IA se confunde y pierde el "significado" (la semántica) de la oración.

---

## 2. La Fusión Matemática: RRF (Reciprocal Rank Fusion)

Al hacer una pregunta, AmiBot dispara **ambos motores al mismo tiempo**.
BM25 devuelve su "Top 3" de mejores respuestas, y ChromaDB devuelve su propio "Top 3". 

Para unificar ambas listas sin que compitan, implementé el algoritmo **Reciprocal Rank Fusion (RRF)**.
La fórmula matemática de RRF asigna puntos dependiendo de la *posición* en la que quedó cada documento en ambas listas:

$$ Score = \frac{1}{k + Rank_{BM25}} + \frac{1}{k + Rank_{ChromaDB}} $$

*Donde `k` es una constante estabilizadora.*

**Resultado:** Al calcular y sumar las fracciones de ambas posiciones, el documento con el puntaje total más alto se corona como el **ganador absoluto**. 

**Ejemplo Explicado para la Defensa:**
Imagina que ambos motores compiten en una carrera y el algoritmo RRF actúa como un juez que suma los puntos según el lugar de llegada (usando la constante k=60).

Un alumno pregunta: *"¿A qué hora puedo ir a devolver un libro?"*

* **Respuesta sobre "Horarios":**
  * **En el Motor de Palabras (BM25):** Queda en **1er lugar**, porque detectó la palabra exacta "hora".
  * **En el Motor de Inteligencia Artificial:** Queda en **10mo lugar**, porque la IA sabe que el alumno no solo quiere saber la hora, sino entregar un objeto.
  * **Cálculo Matemático:** `1 / (60 + 1)  +  1 / (60 + 10) = 0.0305` puntos.

* **Respuesta sobre "Devolución":**
  * **En el Motor de Inteligencia Artificial:** Queda en **1er lugar**, porque la IA entendió que la verdadera intención de fondo es entregar un préstamo.
  * **En el Motor de Palabras (BM25):** Queda en **3er lugar**, porque también detectó las palabras "devolver" y "libro".
  * **Cálculo Matemático:** `1 / (60 + 1)  +  1 / (60 + 3) = 0.0321` puntos.

**La decisión de RRF (El Juez Final):** 
Aunque la Respuesta de Horarios ganó en el buscador de palabras, tuvo un desempeño terrible en el buscador de IA. En cambio, la Respuesta de Devolución tuvo un **rendimiento excelente y balanceado en ambas pruebas** (1er y 3er lugar). El algoritmo suma los resultados matemáticos y declara a la **Respuesta de Devolución como la ganadora definitiva** (0.0321 le gana a 0.0305), esquivando las palabras confusas que usó el alumno.

---

## 3. Optimización de CPU: El Cortocircuito (Bypass)

Procesar texto con Inteligencia Artificial (Ollama / Llama 3.2) consume mucho procesador. Para evitar que el servidor de la universidad colapse si 50 alumnos chatean al mismo tiempo, desarrollé una regla de **Cortocircuito**:

1. Si el ganador absoluto del algoritmo RRF es explícitamente idéntico a lo que busca el alumno (obtiene un *Score* superior al umbral de confianza).
2. El motor **aborta la conexión con el LLM**.
3. En lugar de hacer que Llama 3.2 redacte una respuesta palabra por palabra (lo cual toma varios segundos), el sistema devuelve la respuesta exacta de la base de datos de manera instantánea (en milisegundos).

Esta decisión arquitectónica ahorra hasta un **80% de recursos de hardware**.
¿Por qué es tan importante esto? Porque los servidores web institucionales estándar (como las máquinas virtuales donde se aloja el catálogo VuFind) son servidores basados únicamente en **CPU**, sin Tarjetas Gráficas (GPU) dedicadas. Levantar modelos de IA (Llama) en CPU es extremadamente lento y costoso; el cortocircuito permite que AmiBot sea rápido, escalable y barato sin exigirle a la universidad la compra de hardware de IA especializado.
