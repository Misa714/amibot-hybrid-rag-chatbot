import requests
import concurrent.futures
import time
import random
from datetime import datetime

URL = "http://127.0.0.1:8000/consultar"
USUARIOS_SIMULTANEOS = 12
TIMEOUT_SEGUNDOS = 60

PREGUNTAS_TOTALES = [
    "Cual es el horario de la biblioteca?", "a que hora abren", "hasta que hora atienden los viernes", "abren los sabados", "horario de atencion", "horario hemeroteca",
    "Como puedo pedir un libro?", "me prestan libros", "cuantos libros me puedo llevar", "necesito un libro para la casa", "prestan calculadoras", "hay computadores disponibles",
    "Clave del WiFi?", "wifi clave", "pass del wifi", "contraseña del wifi", "password wifi",
    "Como reservar una sala de tesis?", "como puedo pedir una sala de tesis", "donde se reservan las salas",
    "Como funciona el sistema de lockers?", "como funcionan los casilleros", "perdi la llave del locker", "no devolvi la llave y estoy bloqueado",
    "Que bases de datos tienen?", "no puedo ingresar a scopus", "problemas con proquest", "scopus no me acepta la contraseña",
    "Donde encontrar tesis digitales?", "como puedo pedir una tesis digital", "buscar tesis de anos anteriores", "hay tesis en pdf",
    "Como renovar un libro?", "puedo extender el plazo de un libro", "se me vence mañana como lo renuevo",
    "se me quedo una pertenencia", "se me perdio mi mochila", "encontre algo que hago",
    "venden comida", "quiero una pizza", "quien gano el partido", "va a llover hoy",
    "cuanto cobran por atraso", "estoy moroso que hago", "tengo una multa", "que pasa si entrego el libro tarde", "bloqueado por multa", "como pago el atraso del libro",
    "donde imprimo", "tienen para sacar fotocopias", "cuanto sale la impresion", "hay enchufes para cargar el notebook", "donde estan los banos", "en que piso estan los libros de informatica",
    "wena a q ora abren", "oe el wifi no funca", "se puede comer un completo aentro?", "me prestai un libro pa la casa", "donde saco la tne", "uta perdi la llave del locker",
    "ncesito lbiro de arqutiectura", "dondevestan las tezs", "komo me conekto al wfi", "orario d atencion oi", "prestan calcualdoras sientificas", "kiero rnovar un livor", "baces d dats",
    "y los sabados?", "cuanto cuesta?", "donde queda eso?", "como lo hago?", "y si no tengo?",
    "quien me puede ayudar con una busqueda", "cuando abren la sala de estudio", "por que no puedo entrar a scopus", "cual es el limite de renovaciones",
    # --- PRUEBAS DE COLISIÓN SEMÁNTICA (La prueba de fuego del Re-Ranking) ---
    "quiero pedir un libro de anatomia", "donde devuelvo el libro de anatomia",
    "como extiendo el plazo de un libro de enfermeria", "tengo que entregar un libro hoy",
    "necesito sacar el libro de derecho comercial", "vengo a dejar un libro que saque la semana pasada",
    "se puede renovar un libro de kinesiologia online", "donde se entregan los libros que te prestan",

    # --- PRUEBAS DE BÚSQUEDA TEMÁTICA POR CARRERA (Tu último ajuste del JSON) ---
    "tienen libros de ingenieria civil informatica?", "donde encuentro material de agronomia",
    "necesito guias de estudio de obstetricia", "hay libros de nutricion en la biblioteca?",
    "donde estan los libros de educacion parvularia", "busco apuntes de contador auditor",
    "tienen el libro de teologia?", "donde estan los tomos de derecho penal",
    "necesito un libro de fonoaudiologia para una tarea", "libros de medicina",

    # --- PRUEBAS DE LITERATURA GENERAL (La prueba de Harry Potter / Señor de los Anillos) ---
    "tienen novelas de ficcion?", "busco el libro de cronica de una muerte anunciada",
    "tienen la saga de crepusculo en la biblioteca", "donde encuentro libros de literatura o cuentos",
    "tienen el libro de don quijote de la mancha?", "hay libros de narnia disponibles para llevar",
    "busco cuentos de terror o suspenso", "tienen sagas de libros juveniles",

    # --- REGLAMENTO, MULTAS Y BLOQUEOS (Casos Críticos) ---
    "que pasa si se me pierde un libro?", "cuanto es la multa por dia de atraso",
    "puedo sacar libros si estoy moroso?", "me bloquearon la cuenta por no entregar un libro",
    "donde se pagan las multas de la biblioteca", "cuantos dias te suspenden por devolver tarde",
    "puedo llevarme un libro de referencia a mi casa?", "los test de psicologia se prestan por el fin de semana?",

    # --- INFRAESTRUCTURA, ESPACIOS FÍSICOS Y SERVICIOS ---
    "hay salas de estudio grupal?", "como se pide la sala para ensayar una presentacion",
    "la biblioteca tiene aire acondicionado o calefaccion?", "en que piso esta la hemeroteca",
    "donde se guardan las mochilas antes de entrar", "tienen cargadores de celular para prestar",
    "se puede entrar con un termo de agua para el mate?", "hay computadores para buscar en el catalogo",

    # --- RECURSOS DIGITALES Y CONSULTAS AVANZADAS ---
    "como entro al repositorio digital", "cuales son las bases de datos cientificas",
    "necesito el link de biblioteca virtual", "como busco revistas cientificas en proquest",
    "el acceso a scopus es gratis para estudiantes?", "donde veo las tesis en formato pdf",

    # --- SLANG CHILENO EXTREMO Y ERRORES DE TIPEO ---
    "uta toy bloqueao por no pasar el lbiro a tiempo", "donde dejos los bolsos antes d meterme",
    "oie kero saer si tienn el livor d harry boter", "esta abrida la biblio los fines de samana?",
    "me dio hambre tiran alguna promo de completo aki", "como extendo la cuestion del prestamo",
    "se cayo el wifi de nuevo no me conecta la wa"
]

contador_estados = {}
latencias = []
resultados_detallados = []
inicio_test = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def simular_usuario(id_usuario):
    pregunta_random = random.choice(PREGUNTAS_TOTALES)
    payload = {"pregunta": pregunta_random, "sesion": f"test_estres_usr_{id_usuario}"}
    inicio = time.time()
    try:
        respuesta = requests.post(URL, json=payload, timeout=TIMEOUT_SEGUNDOS)
        latencia = time.time() - inicio
        if respuesta.status_code == 200:
            datos = respuesta.json()
            estado = datos.get('estado', 'desconocido')
            texto_bot = datos.get('respuesta', 'Sin respuesta') # <--- NUEVA LÍNEA

            # MODIFICADO: Agregamos la respuesta corta del bot al string de salida
            resultado = f"[Usuario {id_usuario:02d}] | {latencia:.2f}s | Estado: {estado}\n  Q: '{pregunta_random}'\n  A: {texto_bot[:90]}..."
            return ("exito", estado, latencia, resultado)
        else:
            return ("error_http", f"HTTP_{respuesta.status_code}", 0, f"[Usuario {id_usuario:02d}] | Error HTTP {respuesta.status_code}")
    except requests.exceptions.Timeout:
        return ("timeout", "timeout", 0, f"[Usuario {id_usuario:02d}] | TIMEOUT (>{TIMEOUT_SEGUNDOS}s)")
    except Exception as e:
        return ("critico", "critico", 0, f"[Usuario {id_usuario:02d}] | ERROR CRITICO: {e}")

if __name__ == "__main__":
    print(f"Iniciando Test de Estres Realista con {USUARIOS_SIMULTANEOS} usuarios simultaneos...")
    inicio_total = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=USUARIOS_SIMULTANEOS) as executor:
        resultados_raw = list(executor.map(simular_usuario, range(USUARIOS_SIMULTANEOS)))
    duracion_total = time.time() - inicio_total

    for tipo, estado, latencia, mensaje in resultados_raw:
        resultados_detallados.append(mensaje)
        if tipo == "exito":
            contador_estados[estado] = contador_estados.get(estado, 0) + 1
            latencias.append(latencia)
        else:
            contador_estados[estado] = contador_estados.get(estado, 0) + 1

    for res in resultados_detallados:
        print(res)

    print("-" * 80)
    print("RESUMEN DE ESTADOS:")
    for estado, cantidad in sorted(contador_estados.items(), key=lambda x: x[1], reverse=True):
        print(f"  {estado}: {cantidad}")

    if latencias:
        print("-" * 80)
        print("ESTADISTICAS DE LATENCIA:")
        print(f"  Minima:  {min(latencias):.2f}s")
        print(f"  Maxima:  {max(latencias):.2f}s")
        print(f"  Promedio: {sum(latencias)/len(latencias):.2f}s")

    print("-" * 80)
    print(f"Test finalizado en {duracion_total:.2f} segundos.")

    archivo_log = f"resultados_estres_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(archivo_log, "w", encoding="utf-8") as f:
        f.write(f"Test de Estres - {inicio_test}\n")
        f.write(f"Usuarios: {USUARIOS_SIMULTANEOS}, Timeout: {TIMEOUT_SEGUNDOS}s\n")
        f.write(f"Duracion total: {duracion_total:.2f}s\n")
        f.write("-" * 80 + "\n")
        for res in resultados_detallados:
            f.write(res + "\n")
        f.write("-" * 80 + "\nRESUMEN DE ESTADOS:\n")
        for estado, cantidad in sorted(contador_estados.items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {estado}: {cantidad}\n")
        if latencias:
            f.write("-" * 80 + "\nESTADISTICAS DE LATENCIA:\n")
            f.write(f"  Minima:  {min(latencias):.2f}s\n")
            f.write(f"  Maxima:  {max(latencias):.2f}s\n")
            f.write(f"  Promedio: {sum(latencias)/len(latencias):.2f}s\n")
    print(f"Resultados guardados en: {archivo_log}")
