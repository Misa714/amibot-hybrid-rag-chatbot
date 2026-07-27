import sys
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import os
import chromadb
import numpy as np
from config import BASE_DIR, KNOWLEDGE_PATH

CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

def init_chroma():
    """Inicializa el cliente de ChromaDB y retorna la colección."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    # Configuramos el espacio de distancia como 'cosine' para ser compatibles con cos_sim
    collection = client.get_or_create_collection(
        name="conocimiento_biblioteca",
        metadata={"hnsw:space": "cosine"}
    )
    return collection

def populate_chroma(collection, datos_biblioteca, model):
    """Sincroniza el JSON de conocimiento con ChromaDB utilizando el modelo para generar embeddings."""
    if not datos_biblioteca:
        return
        
    # Obtener documentos existentes para evitar duplicar/re-generar innecesariamente
    ids = [str(i) for i in range(len(datos_biblioteca))]
    documents = [d['usuario'] for d in datos_biblioteca]
    
    # Generamos los embeddings usando el modelo de SentenceTransformer ya cargado en RAM
    embeddings = model.encode(documents, convert_to_tensor=False)
    # Convertimos los numpy arrays a listas para que ChromaDB las acepte
    embeddings_list = [emb.tolist() for emb in embeddings]
    
    metadatas = [
        {
            "bot": d['bot'],
            "categoria": d.get('categoria', 'general'),
            "idx": i
        }
        for i, d in enumerate(datos_biblioteca)
    ]
    
    # Re-poblar la colección (upsert para actualizar existentes y añadir nuevos)
    collection.upsert(
        ids=ids,
        embeddings=embeddings_list,
        metadatas=metadatas,
        documents=documents
    )
