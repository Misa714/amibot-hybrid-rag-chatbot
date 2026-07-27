#!/usr/bin/env python3
import json
import sys
import re

ARCHIVO_JSON = 'conocimiento_base_ollama.json'
ARCHIVO_MAIN = 'main.py'

def extraer_palabras(texto):
    """Extrae palabras significativas (más de 3 letras) de un texto."""
    return set(re.findall(r'\b[a-záéíóúñ]{4,}\b', texto.lower()))

def actualizar_verificar_contexto(categoria, pregunta, respuesta):
    """Agrega automáticamente una categoría al diccionario de verificar_contexto en main.py."""
    with open(ARCHIVO_MAIN, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    # Verificar si la categoría ya existe en el diccionario
    if f'"{categoria}":' in contenido:
        print(f"ℹ️ La categoría '{categoria}' ya existe en verificar_contexto.")
        return
    
    # Extraer palabras clave de pregunta y respuesta
    palabras_pregunta = extraer_palabras(pregunta)
    palabras_respuesta = extraer_palabras(respuesta)
    
    # Limitar a 8 palabras cada una para no sobrecargar
    palabras_pregunta = list(palabras_pregunta)[:8]
    palabras_respuesta = list(palabras_respuesta)[:8]
    
    # Crear la entrada para el diccionario
    nueva_categoria = f'''
        "{categoria}": {{
            "pregunta": {json.dumps(palabras_pregunta)},
            "respuesta": {json.dumps(palabras_respuesta)}
        }},'''
    
    # Insertar la nueva categoría en el diccionario (antes del cierre)
    marcador = '    }'
    posicion = contenido.rfind(marcador)
    if posicion == -1:
        print("⚠️ No se pudo encontrar el diccionario en main.py")
        return
    
    contenido = contenido[:posicion] + nueva_categoria + '\n' + contenido[posicion:]
    
    with open(ARCHIVO_MAIN, 'w', encoding='utf-8') as f:
        f.write(contenido)
    
    print(f"✅ Categoría '{categoria}' agregada automáticamente a verificar_contexto")
    print(f"   Palabras pregunta: {palabras_pregunta}")
    print(f"   Palabras respuesta: {palabras_respuesta}")

def agregar_entrada(archivo, categoria, pregunta, respuesta, confirmar_nueva=True):
    with open(archivo, 'r', encoding='utf-8') as f:
        datos = json.load(f)
    
    for entrada in datos:
        if entrada['usuario'].lower() == pregunta.lower():
            print(f"⚠️ Ya existe una entrada para: '{pregunta}'")
            return False
    
    # Validar categoría
    categorias_existentes = sorted(list(set(d['categoria'] for d in datos if 'categoria' in d)))
    if categoria not in categorias_existentes:
        print(f"\n⚠️  ADVERTENCIA: La categoría '{categoria}' es NUEVA.")
        print(f"   Categorías existentes: {', '.join(categorias_existentes)}")
        if confirmar_nueva and sys.stdin.isatty():
            confirmar = input("   ¿Estás seguro de que quieres crear esta nueva categoría? (s/n): ").strip().lower()
            if confirmar != 's':
                print("❌ Operación cancelada.")
                return False
        else:
            print("   (Se creará automáticamente)")

    datos.append({
        "categoria": categoria,
        "usuario": pregunta,
        "bot": respuesta
    })
    
    with open(archivo, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    
    # Actualizar verificación contextual automáticamente
    # actualizar_verificar_contexto(categoria, pregunta, respuesta)
    
    print(f"✅ Entrada agregada. Total: {len(datos)} registros")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python3 agregar_conocimiento.py <categoria> <pregunta> <respuesta>")
        try:
            with open(ARCHIVO_JSON, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            cats = sorted(list(set(d['categoria'] for d in datos if 'categoria' in d)))
            print("\nCategorías existentes en la base de conocimiento:")
            for c in cats:
                print(f"  - {c}")
        except Exception:
            pass
        sys.exit(1)
    
    agregar_entrada(ARCHIVO_JSON, sys.argv[1], sys.argv[2], sys.argv[3], confirmar_nueva=True)
