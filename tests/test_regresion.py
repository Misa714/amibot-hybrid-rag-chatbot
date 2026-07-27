#!/usr/bin/env python3
import requests
import json

API_URL = "http://localhost:8000/consultar"

# Diccionario de pruebas genéricas: {"pregunta": "respuesta esperada (fragmento)"}
PRUEBAS = {
    # Horario
    "cual es el horario de la biblioteca": "08:00 a 20:00",
    "horario de atencion": "08:00 a 20:00",
    "hasta que hora atienden los viernes": "13:00 horas",
    "abren los sabados": "cerrada",

    # WiFi
    "clave del wifi": "campus2026",
    "cual es la clave del wifi": "campus2026",

    # Acceso a bases de datos
    "como acceder a las bases de datos": "catálogo",

    # Préstamos
    "cuantos libros puedo pedir": "3 libros",
    "como pedir un libro prestado": "mesón",
    "cuando tengo que devolver un libro": "mesón",
    "cuantos dias puedo tener un libro prestado": "7 días",

    # Devolución
    "como puedo devolver un libro": "mesón",
    "donde entrego los libros": "mesón",

    # Salas de estudio
    "como reservar sala de estudio": "reservas.example.edu",

    # Lockers
    "como funciona el sistema de lockers": "mesón",

    # Tesis
    "donde encontrar tesis digitales": "repositorio.example.edu",

    # Comida (debe rechazar)
    "venden comida": "alimentos",
    "venden pizza": "alimentos",
}

def ejecutar_pruebas():
    import time
    import os
    total = len(PRUEBAS)
    exitos = 0
    fallos = []
    latencias = []
    detalles_pruebas = []

    def evaluar_semantica(esperado, obtenido):
        if not obtenido:
            return False
        if esperado.lower() in obtenido.lower():
            return True
        
        try:
            import ollama
            prompt_juez = f"Eres un juez estricto. Revisa si la Respuesta del Bot tiene el mismo significado o contiene la información clave de la Respuesta Esperada.\nRespuesta Esperada: {esperado}\nRespuesta del Bot: {obtenido}\n¿Significan lo mismo o la información es correcta? Responde ÚNICAMENTE con YES o NO."
            resp_juez = ollama.chat(
                model="llama3.2:1b", 
                messages=[{"role": "user", "content": prompt_juez}],
                options={"temperature": 0.0, "num_predict": 5}
            )
            veredicto = resp_juez['message']['content'].strip().upper()
            es_valido = "YES" in veredicto
            if es_valido:
                print(f"  [Juez IA] Validó semánticamente: '{obtenido[:30]}...' (Esperaba: '{esperado}')")
            return es_valido
        except Exception as e:
            print(f"  Error de conexión Juez IA: {e}")
            return esperado.lower() in obtenido.lower()

    for pregunta, esperado in PRUEBAS.items():
        inicio = time.time()
        try:
            time.sleep(2.1)
            response = requests.post(API_URL,
                json={"pregunta": pregunta, "sesion": "test_regresion"},
                headers={"X-Chatbot-Token": "CHANGE_ME_IN_PRODUCTION"},
                timeout=10)
            latencia = time.time() - inicio
            latencias.append(latencia)
            
            if response.status_code == 429:
                respuesta = "ERROR: Bloqueado por Firewall (Rate Limit)"
                estado = "error_429"
                confianza = 0
            elif response.status_code != 200:
                respuesta = f"ERROR HTTP {response.status_code}: {response.text[:50]}"
                estado = "error_http"
                confianza = 0
            else:
                data = response.json()
                respuesta = data.get("respuesta", "").lower()
                estado = data.get("estado", "")
                confianza = data.get("confianza", 0)

            exito_item = evaluar_semantica(esperado, respuesta) and confianza >= 0.55
            
            detalles_pruebas.append({
                "pregunta": pregunta,
                "esperado": esperado,
                "obtenido": respuesta,
                "confianza": confianza,
                "estado": estado,
                "latencia": latencia,
                "resultado": "PASSED" if exito_item else "FAILED"
            })

            if exito_item:
                exitos += 1
                print(f"PASSED [{confianza:.2f} | {latencia:.2f}s] {pregunta[:50]}...")
            else:
                fallos.append({
                    "pregunta": pregunta,
                    "esperado": esperado,
                    "obtenido": respuesta[:100],
                    "confianza": confianza,
                    "estado": estado,
                    "latencia": latencia
                })
                print(f"FAILED [{confianza:.2f} | {latencia:.2f}s] {pregunta[:50]}...")

        except Exception as e:
            latencia = time.time() - inicio
            fallos.append({
                "pregunta": pregunta,
                "error": str(e),
                "latencia": latencia
            })
            detalles_pruebas.append({
                "pregunta": pregunta,
                "esperado": esperado,
                "obtenido": "ERROR: " + str(e),
                "confianza": 0,
                "estado": "error",
                "latencia": latencia,
                "resultado": "ERROR"
            })
            print(f"Error en '{pregunta[:50]}...': {e}")

    precisión = (exitos / total) * 100 if total > 0 else 0
    avg_latency = sum(latencias) / len(latencias) if latencias else 0
    min_latency = min(latencias) if latencias else 0
    max_latency = max(latencias) if latencias else 0

    print(f"\n{'='*50}")
    print(f"Resultados: {exitos}/{total} pruebas pasadas ({precisión:.2f}% de precisión)")
    print(f"Latencia: Promedio {avg_latency:.2f}s | Mínima {min_latency:.2f}s | Máxima {max_latency:.2f}s")

    try:
        reporte_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reporte_evaluacion_rag.md")
        with open(reporte_path, "w", encoding="utf-8") as f:
            f.write("# Reporte Cuantitativo de Calidad RAG - Biblioteca Universitaria\n\n")
            f.write(f"**Fecha de ejecución:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Resumen de Métricas Clave\n\n")
            f.write("| Métrica | Valor | Objetivo |\n")
            f.write("| --- | --- | --- |\n")
            f.write(f"| **Precisión (Accuracy)** | {precisión:.2f}% | >= 85.00% |\n")
            f.write(f"| **Pruebas Exitosas** | {exitos} / {total} | - |\n")
            f.write(f"| **Latencia Promedio** | {avg_latency:.3f} s | < 1.500 s |\n")
            f.write(f"| **Latencia Mínima** | {min_latency:.3f} s | - |\n")
            f.write(f"| **Latencia Máxima** | {max_latency:.3f} s | - |\n\n")
            
            f.write("## Detalle de Casos de Prueba\n\n")
            f.write("| Pregunta | Resultado | Confianza | Latencia | Estado RAG |\n")
            f.write("| --- | --- | --- | --- | --- |\n")
            for t in detalles_pruebas:
                res_emoji = "PASSED" if t["resultado"] == "PASSED" else "FAILED"
                f.write(f"| `{t['pregunta']}` | {res_emoji} | {t['confianza']:.2f} | {t['latencia']:.3f} s | `{t['estado']}` |\n")

        print(f"Reporte de calidad RAG generado en: {reporte_path}")
    except Exception as re:
        print(f"No se pudo escribir el reporte Markdown: {re}")

    return exitos == total

if __name__ == "__main__":
    import sys
    exito = ejecutar_pruebas()
    sys.exit(0 if exito else 1)
