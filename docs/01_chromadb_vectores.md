# Base de Datos Vectorial: ChromaDB

AmiBot utiliza una arquitectura de bases de datos dual. Para el almacenamiento del conocimiento y la búsqueda semántica, el sistema depende de **ChromaDB**.

A diferencia de una base de datos tradicional que guarda texto en tablas (como SQL), ChromaDB es una **Base de Datos Vectorial**. Su única función es guardar matrices matemáticas (Embeddings) de 384 dimensiones generadas por la Inteligencia Artificial y calcular rápidamente las distancias entre ellas en un espacio multidimensional (Similitud Coseno).

## 1. Diseño "Privacy-First" y Local

Una de las decisiones arquitectónicas clave del proyecto fue **no utilizar bases de datos en la nube** (como Pinecone o Weaviate).
ChromaDB está configurado para operar de forma 100% local (`PersistentClient`). Toda la información de la universidad se guarda dentro del mismo servidor en una carpeta física. Esto garantiza que la biblioteca tenga soberanía total sobre sus datos institucionales sin depender de conexiones a internet externas.

## 2. Optimización de Arranque: Hashing MD5

Generar Vectores Matemáticos (Embeddings) a partir del texto consume mucho procesador. Si AmiBot tuviera que leer todo el archivo `conocimiento_base_ollama.json` y convertirlo a vectores cada vez que el servidor se reinicia, el tiempo de arranque sería terriblemente lento.

Para solucionar esto, desarrollé un **Sistema de Caché basado en Hashing MD5** en `main.py`:

1. **Lectura y Hash:** Cuando AmiBot arranca, lee el archivo JSON de la biblioteca y genera una huella digital única (Hash MD5) de todo el documento.
2. **Comparación:** Luego, lee un pequeño archivo llamado `chroma_hash.txt` para ver cuál fue la última huella digital guardada.
3. **El Bypass:** Si las huellas son **idénticas**, significa que ningún humano ha modificado el JSON de conocimiento. Por lo tanto, AmiBot *se salta* todo el proceso de indexación y simplemente carga la base de datos ChromaDB existente de inmediato.
4. **Re-Indexación Automática:** Si las huellas son **distintas** (es decir, el administrador agregó o modificó una respuesta en el JSON), AmiBot elimina la colección vectorial antigua, vuelve a procesar texto por texto con la IA, guarda la nueva base de datos y actualiza el archivo de la huella digital.

### Beneficio Arquitectónico
Este sistema convierte a AmiBot en un servicio **Auto-sostenible**. El administrador o bibliotecario solo debe preocuparse de editar el archivo de texto JSON; el código backend se da cuenta del cambio por su cuenta y re-sincroniza el "cerebro" matemático sin necesidad de intervención de un ingeniero.
