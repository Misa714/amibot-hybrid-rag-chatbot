#!/usr/bin/env python3
"""
Analizador de Brechas de Conocimiento — Chatbot Biblioteca Universitaria.

Extrae del dashboard SQLite todas las preguntas que el bot NO pudo responder
o que los alumnos marcaron como incorrectas (dislike), las agrupa por similitud
y genera un informe accionable para que el bibliotecario pueda agregar las
respuestas faltantes antes del correo masivo.

Uso:
    python3 analizar_brechas.py              → Muestra informe en terminal
    python3 analizar_brechas.py --exportar   → Genera brechas_pendientes.md
"""
import sqlite3
import sys
import os
from datetime import datetime
from collections import Counter

try:
    from config import DB_PATH
    DB = DB_PATH
except ImportError:
    DB = os.path.join(os.path.dirname(__file__), "consultas.db")


def obtener_brechas():
    """Extrae preguntas no respondidas, con baja confianza o con dislike."""
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    # 1. Preguntas escaladas a humano (el bot NO supo responder)
    cursor.execute("""
        SELECT pregunta, COUNT(*) as veces, MAX(fecha) as ultima_vez
        FROM consultas 
        WHERE estado LIKE '%escalado_humano%'
        GROUP BY pregunta 
        ORDER BY veces DESC
    """)
    escaladas = cursor.fetchall()

    # 2. Preguntas con dislike (el bot respondió MAL según el alumno)
    cursor.execute("""
        SELECT pregunta, respuesta, feedback_comentario, fecha
        FROM consultas 
        WHERE feedback = 'dislike'
        ORDER BY fecha DESC
    """)
    dislikes = cursor.fetchall()

    # 3. Preguntas con baja confianza (score < 0.5) que SÍ se respondieron
    cursor.execute("""
        SELECT pregunta, respuesta, score, estado, fecha
        FROM consultas 
        WHERE score < 0.5 AND score > 0 
        AND estado NOT LIKE '%rechazo%' 
        AND estado NOT LIKE '%escalado%'
        AND estado NOT LIKE '%saludo%'
        ORDER BY score ASC
    """)
    baja_confianza = cursor.fetchall()

    # 4. Estadísticas generales
    cursor.execute("SELECT COUNT(*) FROM consultas")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM consultas WHERE feedback = 'like'")
    likes = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM consultas WHERE feedback = 'dislike'")
    n_dislikes = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM consultas WHERE estado LIKE '%escalado_humano%'")
    n_escaladas = cursor.fetchone()[0]

    conn.close()
    return escaladas, dislikes, baja_confianza, total, likes, n_dislikes, n_escaladas


def generar_informe(exportar=False):
    escaladas, dislikes, baja_confianza, total, likes, n_dislikes, n_escaladas = obtener_brechas()

    lineas = []
    lineas.append("# Informe de Brechas de Conocimiento")
    lineas.append(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lineas.append(f"**Base de datos:** `{DB}`\n")

    # Resumen
    lineas.append("## Resumen")
    lineas.append(f"- Total de consultas: **{total}**")
    lineas.append(f"- Likes 👍: **{likes}**")
    lineas.append(f"- Dislikes 👎: **{n_dislikes}**")
    lineas.append(f"- Escaladas a humano (sin respuesta): **{n_escaladas}**")
    lineas.append(f"- Respuestas de baja confianza (<0.5): **{len(baja_confianza)}**")

    tasa_precision = ((total - n_escaladas - n_dislikes) / total * 100) if total > 0 else 0
    lineas.append(f"- **Tasa de precisión estimada: {tasa_precision:.1f}%**\n")

    # Sección 1: Preguntas sin respuesta
    lineas.append("---")
    lineas.append("## 1. Preguntas que el bot NO supo responder")
    lineas.append("*Estas son las brechas más importantes. Cada una necesita una respuesta nueva en el JSON.*\n")
    if escaladas:
        lineas.append("| # | Pregunta | Veces | Última vez |")
        lineas.append("|---|----------|-------|------------|")
        for i, (preg, veces, fecha) in enumerate(escaladas, 1):
            lineas.append(f"| {i} | {preg[:80]} | {veces} | {fecha[:10]} |")
    else:
        lineas.append("✅ No hay preguntas sin respuesta.")

    # Sección 2: Dislikes con comentarios
    lineas.append("\n---")
    lineas.append("## 2. Respuestas marcadas como incorrectas por alumnos")
    lineas.append("*Los comentarios de los alumnos indican qué esperaban recibir.*\n")
    if dislikes:
        lineas.append("| # | Pregunta | Respuesta del bot | Comentario del alumno | Fecha |")
        lineas.append("|---|----------|-------------------|----------------------|-------|")
        for i, (preg, resp, com, fecha) in enumerate(dislikes, 1):
            preg_corta = (preg or "-")[:50]
            resp_corta = (resp or "-")[:50]
            com_corta = (com or "Sin comentario")[:50]
            lineas.append(f"| {i} | {preg_corta} | {resp_corta} | {com_corta} | {fecha[:10]} |")
    else:
        lineas.append("✅ No hay respuestas con dislike.")

    # Sección 3: Baja confianza
    lineas.append("\n---")
    lineas.append("## 3. Respuestas con baja confianza (riesgo de imprecisión)")
    lineas.append("*El bot respondió, pero con poca seguridad. Revisar si la respuesta fue correcta.*\n")
    if baja_confianza:
        lineas.append("| # | Pregunta | Respuesta | Score | Estado |")
        lineas.append("|---|----------|-----------|-------|--------|")
        for i, (preg, resp, score, estado, fecha) in enumerate(baja_confianza[:20], 1):
            preg_corta = (preg or "-")[:45]
            resp_corta = (resp or "-")[:45]
            lineas.append(f"| {i} | {preg_corta} | {resp_corta} | {score:.2f} | {estado} |")
    else:
        lineas.append("✅ Todas las respuestas tienen confianza >= 0.5.")

    # Sección 4: Acciones sugeridas
    lineas.append("\n---")
    lineas.append("## 4. Acciones sugeridas antes del correo masivo")
    lineas.append("")
    if escaladas:
        lineas.append(f"1. **Agregar {len(escaladas)} respuestas nuevas** al archivo `conocimiento_base_ollama.json` para cubrir las preguntas sin respuesta.")
        lineas.append("   - Usar: `python3 agregar_conocimiento.py <categoria> \"<pregunta>\" \"<respuesta>\"`")
    if dislikes:
        lineas.append(f"2. **Revisar {len(dislikes)} respuestas con dislike** y corregir o ampliar las entradas existentes en el JSON.")
    if baja_confianza:
        lineas.append(f"3. **Verificar {min(len(baja_confianza), 20)} respuestas de baja confianza** manualmente para asegurar que son correctas.")
    lineas.append(f"4. **Ejecutar `python3 test_regresion.py`** después de agregar el nuevo conocimiento para verificar que no se rompió nada.")
    lineas.append(f"5. **Re-ejecutar este script** para confirmar que las brechas se cerraron.\n")

    texto = "\n".join(lineas)

    if exportar:
        ruta = os.path.join(os.path.dirname(__file__), "brechas_pendientes.md")
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(texto)
        print(f"✅ Informe exportado a: {ruta}")
    else:
        print(texto)


if __name__ == "__main__":
    exportar = "--exportar" in sys.argv
    generar_informe(exportar=exportar)
