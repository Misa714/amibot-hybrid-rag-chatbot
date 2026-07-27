import os
import sys
import logging
from sentence_transformers import SentenceTransformer

# Configurar logs
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Importar funciones del router
from router import init_intent_embeddings, clasificar_intencion_industrial, detectar_intencion_dura

def main():
    print("⏳ Cargando modelo local para pruebas...")
    # Cargar el modelo MiniLM (el mismo que usa tu proyecto)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("\n🚀 Inicializando Router Dinámico...")
    embeddings_intenciones = init_intent_embeddings(model)
    
    preguntas_prueba = [
        "¿A qué hora cierran la biblioteca hoy?",
        "Hola, me gustaría saber si tienen el libro de Harry Potter",
        "Tengo clases hasta las 20:00 hrs, alcanzo a pasar a la biblioteca o está cerrado",
        "necesito pedir una sala de estudio para mi grupo de tesis",
        "cuanto es la multa estoy bloqueado debo dinero suspenden moroso",
        "estoy haciendo una investigación y necesito revistas indexadas"
    ]
    
    print("\n==========================================")
    print("🧪 INICIANDO BATERÍA DE PRUEBAS DEL ROUTER")
    print("==========================================\n")
    
    for pregunta in preguntas_prueba:
        print(f"🗣️ PREGUNTA: '{pregunta}'")
        
        # 1. Probar Reglas Duras
        intent_duro = detectar_intencion_dura(pregunta)
        if intent_duro != "rag_general":
            print(f"   🛡️ CORTOCIRCUITO (Reglas): {intent_duro}")
            print("-" * 40)
            continue
            
        # 2. Probar IA Semántica
        query_vector = model.encode(pregunta, convert_to_tensor=True)
        intent, score, telemetria = clasificar_intencion_industrial(
            query_vector, 
            embeddings_intenciones, 
            threshold_minimo=0.45
        )
        
        print(f"   🤖 INTENCIÓN IA: {intent}")
        print(f"   📊 SCORE: {score:.3f} (Estado: {telemetria['status']})")
        if intent == "rag_general":
            print(f"   ⚠️ Caída a Búsqueda General (Mejor intento fue {telemetria['top1_intent']} con {telemetria['top1_score']:.3f})")
        print("-" * 40)

if __name__ == '__main__':
    main()
