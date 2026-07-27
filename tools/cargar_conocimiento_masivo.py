#!/usr/bin/env python3
"""
Carga masiva de conocimiento desde un archivo CSV/TSV.

Permite al bibliotecario preparar todas las respuestas faltantes en un archivo
de texto simple y cargarlas de una sola vez al JSON de conocimiento.

Formato del archivo (separado por tabulación):
    categoria\tpregunta\trespuesta

Uso:
    python3 cargar_conocimiento_masivo.py nuevas_respuestas.tsv
    python3 cargar_conocimiento_masivo.py nuevas_respuestas.tsv --dry-run   (solo muestra, no guarda)

Ejemplo de archivo nuevas_respuestas.tsv:
    horario\t¿A qué hora abre la biblioteca?\tLa biblioteca abre de lunes a viernes de 08:00 a 20:00 hrs.
    prestamo\t¿Cuántos libros puedo sacar?\tPuedes sacar hasta 3 libros por 7 días.
"""
import json
import sys
import os

ARCHIVO_JSON = os.path.join(os.path.dirname(__file__), 'conocimiento_base_ollama.json')


def cargar_masivo(archivo_tsv, dry_run=False):
    # Leer JSON actual
    with open(ARCHIVO_JSON, 'r', encoding='utf-8') as f:
        datos = json.load(f)

    preguntas_existentes = {d['usuario'].lower().strip() for d in datos}
    nuevas = []
    duplicadas = []
    errores = []

    with open(archivo_tsv, 'r', encoding='utf-8') as f:
        for num_linea, linea in enumerate(f, 1):
            linea = linea.strip()
            if not linea or linea.startswith('#'):
                continue

            partes = linea.split('\t')
            if len(partes) != 3:
                errores.append(f"  Línea {num_linea}: Esperaba 3 columnas (categoría, pregunta, respuesta), encontré {len(partes)}")
                continue

            categoria, pregunta, respuesta = [p.strip() for p in partes]

            if pregunta.lower().strip() in preguntas_existentes:
                duplicadas.append(f"  Línea {num_linea}: \"{pregunta[:50]}...\" (ya existe)")
                continue

            nuevas.append({
                "categoria": categoria,
                "usuario": pregunta,
                "bot": respuesta
            })
            preguntas_existentes.add(pregunta.lower().strip())

    # Informe
    print(f"\n{'═' * 60}")
    print(f"  CARGA MASIVA DE CONOCIMIENTO")
    print(f"{'═' * 60}")
    print(f"  Archivo: {archivo_tsv}")
    print(f"  Entradas actuales en JSON: {len(datos)}")
    print(f"  Nuevas a agregar: {len(nuevas)}")
    print(f"  Duplicadas (omitidas): {len(duplicadas)}")
    print(f"  Errores de formato: {len(errores)}")
    print(f"{'═' * 60}\n")

    if errores:
        print("❌ ERRORES DE FORMATO:")
        for e in errores:
            print(e)
        print()

    if duplicadas:
        print("⏭️  DUPLICADAS (omitidas):")
        for d in duplicadas:
            print(d)
        print()

    if nuevas:
        print("✅ NUEVAS ENTRADAS:")
        for i, n in enumerate(nuevas, 1):
            print(f"  {i}. [{n['categoria']}] {n['usuario'][:60]}")
            print(f"     → {n['bot'][:80]}...")
            print()

    if dry_run:
        print("🔍 MODO DRY-RUN: No se guardó nada. Ejecuta sin --dry-run para aplicar.")
        return

    if not nuevas:
        print("ℹ️  No hay entradas nuevas para agregar.")
        return

    # Guardar
    datos.extend(nuevas)
    with open(ARCHIVO_JSON, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(nuevas)} entradas agregadas. Total ahora: {len(datos)} registros.")
    print(f"⚠️  IMPORTANTE: Reinicia el servidor para que los nuevos embeddings se generen.")
    print(f"   Ejecuta: python3 reiniciar.sh")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 cargar_conocimiento_masivo.py <archivo.tsv> [--dry-run]")
        print("\nFormato del archivo (separado por TAB):")
        print("  categoria\\tpregunta\\trespuesta")
        sys.exit(1)

    archivo = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    if not os.path.exists(archivo):
        print(f"❌ Archivo no encontrado: {archivo}")
        sys.exit(1)

    cargar_masivo(archivo, dry_run=dry_run)
