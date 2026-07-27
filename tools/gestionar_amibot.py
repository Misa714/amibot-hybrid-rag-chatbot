#!/usr/bin/env python3
"""
Herramienta unificada de configuración avanzada de AmiBot.

Permite al bibliotecario gestionar las reglas del router, correcciones ortográficas,
términos inmunes, expansiones de intención, guardrails, familias de categorías
y filtros anti-ruido sin necesidad de modificar código fuente.

Uso: python3 gestionar_amibot.py <módulo> <acción> [argumentos]

Módulos disponibles:
  router          Reglas de enrutamiento determinista
  correcciones    Diccionario de errores de tipeo frecuentes
  inmunidad       Palabras que el corrector ortográfico no debe tocar
  expansiones     Sinónimos que amplían la búsqueda de intención
  guardrails      Palabras fuera del dominio de la biblioteca
  familias        Agrupaciones de categorías para el boost de intención
  filtro          Excepciones al filtro anti-ruido de catálogo
"""
import sys
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')


# ═══════════════════════════════════════════════
#  UTILIDADES DE LECTURA/ESCRITURA
# ═══════════════════════════════════════════════

def _leer_json(nombre_archivo):
    path = os.path.join(CONFIG_DIR, nombre_archivo)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _escribir_json(nombre_archivo, data):
    path = os.path.join(CONFIG_DIR, nombre_archivo)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Archivo guardado: {path}")


def _leer_txt(nombre_archivo):
    path = os.path.join(CONFIG_DIR, nombre_archivo)
    with open(path, 'r', encoding='utf-8') as f:
        return [l.strip().lower() for l in f if l.strip() and not l.startswith('#')]


def _escribir_txt(nombre_archivo, lineas, encabezado=""):
    path = os.path.join(CONFIG_DIR, nombre_archivo)
    with open(path, 'w', encoding='utf-8') as f:
        if encabezado:
            f.write(encabezado)
        for l in sorted(set(lineas)):
            f.write(l + '\n')
    print(f"💾 Archivo guardado: {path}")


def _recordar_reinicio():
    print("\n⚠️  IMPORTANTE: Ejecuta ./reiniciar.sh para que los cambios tomen efecto.")


# ═══════════════════════════════════════════════
#  MÓDULO 1: ROUTER (reglas_router.json)
# ═══════════════════════════════════════════════

def gestionar_router(accion, args):
    ARCHIVO = 'reglas_router.json'

    if accion == 'listar':
        reglas = _leer_json(ARCHIVO)
        print(f"\n📋 Reglas del router ({len(reglas)} reglas):\n")
        for i, r in enumerate(reglas, 1):
            palabras_cortas = ', '.join(r['palabras'][:4])
            extra = f" (+{len(r['palabras'])-4} más)" if len(r['palabras']) > 4 else ""
            print(f"  {i:2d}. [{r['intent']:24s}] {palabras_cortas}{extra}")
            if r.get('exclusiones'):
                print(f"      Exclusiones: {', '.join(r['exclusiones'])}")
            if r.get('requiere_contexto'):
                print(f"      Requiere contexto: {', '.join(r['requiere_contexto'])}")
            if r.get('nota'):
                print(f"      📝 {r['nota']}")

    elif accion == 'agregar':
        if len(args) < 2:
            print("Uso: python3 gestionar_amibot.py router agregar \"<intent>\" \"<palabra1,palabra2,...>\"")
            print("  Opciones extra: --excluir \"exc1,exc2\" --contexto \"ctx1,ctx2\"")
            print("\nEjemplo:")
            print('  python3 gestionar_amibot.py router agregar "sala_computacion" "impresora 3d,sala computacion"')
            return

        intent = args[0]
        palabras = [p.strip() for p in args[1].split(',')]
        exclusiones = []
        contexto = []

        i = 2
        while i < len(args):
            if args[i] == '--excluir' and i + 1 < len(args):
                exclusiones = [e.strip() for e in args[i + 1].split(',')]
                i += 2
            elif args[i] == '--contexto' and i + 1 < len(args):
                contexto = [c.strip() for c in args[i + 1].split(',')]
                i += 2
            else:
                i += 1

        reglas = _leer_json(ARCHIVO)
        reglas.append({
            "intent": intent,
            "palabras": palabras,
            "exclusiones": exclusiones,
            "requiere_contexto": contexto
        })
        _escribir_json(ARCHIVO, reglas)
        print(f"✅ Regla agregada: [{intent}] con {len(palabras)} palabras clave")
        _recordar_reinicio()

    elif accion == 'eliminar':
        if len(args) < 1:
            print("Uso: python3 gestionar_amibot.py router eliminar <número>")
            print("  (Usa 'listar' primero para ver los números)")
            return

        try:
            idx = int(args[0]) - 1
        except ValueError:
            print("❌ Debes indicar el número de la regla (ej: 3)")
            return

        reglas = _leer_json(ARCHIVO)
        if idx < 0 or idx >= len(reglas):
            print(f"❌ El número debe estar entre 1 y {len(reglas)}")
            return

        eliminada = reglas.pop(idx)
        _escribir_json(ARCHIVO, reglas)
        print(f"✅ Regla eliminada: [{eliminada['intent']}] {', '.join(eliminada['palabras'][:3])}...")
        _recordar_reinicio()

    elif accion == 'palabra':
        if len(args) < 2:
            print("Uso: python3 gestionar_amibot.py router palabra <número_regla> \"nueva_palabra\"")
            return

        try:
            idx = int(args[0]) - 1
        except ValueError:
            print("❌ Debes indicar el número de la regla")
            return

        reglas = _leer_json(ARCHIVO)
        if idx < 0 or idx >= len(reglas):
            print(f"❌ El número debe estar entre 1 y {len(reglas)}")
            return

        nueva = args[1].strip().lower()
        if nueva in reglas[idx]['palabras']:
            print(f"ℹ️  La palabra '{nueva}' ya existe en esa regla.")
            return

        reglas[idx]['palabras'].append(nueva)
        _escribir_json(ARCHIVO, reglas)
        print(f"✅ Palabra '{nueva}' agregada a la regla [{reglas[idx]['intent']}]")
        _recordar_reinicio()

    else:
        print(f"❌ Acción '{accion}' no válida. Usa: listar, agregar, eliminar, palabra")


# ═══════════════════════════════════════════════
#  MÓDULO 2: CORRECCIONES (correcciones_ortograficas.json)
# ═══════════════════════════════════════════════

def gestionar_correcciones(accion, args):
    ARCHIVO = 'correcciones_ortograficas.json'

    if accion == 'listar':
        data = _leer_json(ARCHIVO)
        print(f"\n📋 Correcciones ortográficas ({len(data)} entradas):\n")
        for error, correccion in sorted(data.items()):
            print(f"  {error:20s} → {correccion}")

    elif accion == 'agregar':
        if len(args) < 2:
            print('Uso: python3 gestionar_amibot.py correcciones agregar "<error>" "<corrección>"')
            print('Ejemplo: python3 gestionar_amibot.py correcciones agregar "kompü" "computador"')
            return

        error = args[0].strip().lower()
        correccion = args[1].strip().lower()
        data = _leer_json(ARCHIVO)

        if error in data:
            print(f"ℹ️  '{error}' ya existe (→ {data[error]}). Se actualizará.")

        data[error] = correccion
        _escribir_json(ARCHIVO, data)
        print(f"✅ Corrección agregada: '{error}' → '{correccion}'")
        _recordar_reinicio()

    elif accion == 'eliminar':
        if len(args) < 1:
            print('Uso: python3 gestionar_amibot.py correcciones eliminar "<error>"')
            return

        error = args[0].strip().lower()
        data = _leer_json(ARCHIVO)

        if error not in data:
            print(f"❌ '{error}' no existe en las correcciones.")
            return

        del data[error]
        _escribir_json(ARCHIVO, data)
        print(f"✅ Corrección eliminada: '{error}'")
        _recordar_reinicio()

    else:
        print(f"❌ Acción '{accion}' no válida. Usa: listar, agregar, eliminar")


# ═══════════════════════════════════════════════
#  MÓDULO 3: INMUNIDAD (terminos_inmunes.txt)
# ═══════════════════════════════════════════════

def gestionar_inmunidad(accion, args):
    ARCHIVO = 'terminos_inmunes.txt'

    if accion == 'listar':
        terminos = _leer_txt(ARCHIVO)
        print(f"\n📋 Términos inmunes al corrector ({len(terminos)} términos):\n")
        for t in sorted(terminos):
            print(f"  • {t}")

    elif accion == 'agregar':
        if len(args) < 1:
            print('Uso: python3 gestionar_amibot.py inmunidad agregar "<término>"')
            print('Ejemplo: python3 gestionar_amibot.py inmunidad agregar "redalyc"')
            return

        nuevo = args[0].strip().lower()
        terminos = _leer_txt(ARCHIVO)

        if nuevo in terminos:
            print(f"ℹ️  '{nuevo}' ya está en la lista de inmunidad.")
            return

        terminos.append(nuevo)
        _escribir_txt(ARCHIVO, terminos, "# Términos inmunes al corrector ortográfico\n# (una palabra por línea, las líneas con # son comentarios)\n")
        print(f"✅ Término inmune agregado: '{nuevo}'")
        _recordar_reinicio()

    elif accion == 'eliminar':
        if len(args) < 1:
            print('Uso: python3 gestionar_amibot.py inmunidad eliminar "<término>"')
            return

        termino = args[0].strip().lower()
        terminos = _leer_txt(ARCHIVO)

        if termino not in terminos:
            print(f"❌ '{termino}' no está en la lista de inmunidad.")
            return

        terminos.remove(termino)
        _escribir_txt(ARCHIVO, terminos, "# Términos inmunes al corrector ortográfico\n# (una palabra por línea, las líneas con # son comentarios)\n")
        print(f"✅ Término eliminado: '{termino}'")
        _recordar_reinicio()

    else:
        print(f"❌ Acción '{accion}' no válida. Usa: listar, agregar, eliminar")


# ═══════════════════════════════════════════════
#  MÓDULO 4: EXPANSIONES (expansiones_intenciones.json)
# ═══════════════════════════════════════════════

def gestionar_expansiones(accion, args):
    ARCHIVO = 'expansiones_intenciones.json'

    if accion == 'listar':
        data = _leer_json(ARCHIVO)
        print(f"\n📋 Expansiones de intención ({len(data)} entradas):\n")
        for palabra, expansion in sorted(data.items()):
            print(f"  {palabra:20s} → agrega: \"{expansion}\"")

    elif accion == 'agregar':
        if len(args) < 2:
            print('Uso: python3 gestionar_amibot.py expansiones agregar "<sinónimo>" "<keywords de intención>"')
            print('Ejemplo: python3 gestionar_amibot.py expansiones agregar "retornar" "devolucion entrega"')
            return

        sinonimo = args[0].strip().lower()
        expansion = args[1].strip().lower()
        data = _leer_json(ARCHIVO)

        if sinonimo in data:
            print(f"ℹ️  '{sinonimo}' ya existe (→ {data[sinonimo]}). Se actualizará.")

        data[sinonimo] = expansion
        _escribir_json(ARCHIVO, data)
        print(f"✅ Expansión agregada: '{sinonimo}' → '{expansion}'")
        _recordar_reinicio()

    elif accion == 'eliminar':
        if len(args) < 1:
            print('Uso: python3 gestionar_amibot.py expansiones eliminar "<sinónimo>"')
            return

        sinonimo = args[0].strip().lower()
        data = _leer_json(ARCHIVO)

        if sinonimo not in data:
            print(f"❌ '{sinonimo}' no existe en las expansiones.")
            return

        del data[sinonimo]
        _escribir_json(ARCHIVO, data)
        print(f"✅ Expansión eliminada: '{sinonimo}'")
        _recordar_reinicio()

    else:
        print(f"❌ Acción '{accion}' no válida. Usa: listar, agregar, eliminar")


# ═══════════════════════════════════════════════
#  MÓDULO 5: GUARDRAILS (guardrails_dominio.json)
# ═══════════════════════════════════════════════

def gestionar_guardrails(accion, args):
    ARCHIVO = 'guardrails_dominio.json'

    if accion == 'listar':
        data = _leer_json(ARCHIVO)
        print(f"\n📋 Palabras bloqueadas (fuera de dominio):\n")
        for p in sorted(data.get('out_of_domain', [])):
            print(f"  🚫 {p}")
        print(f"\n📋 Palabras ambiguas (requieren más contexto):\n")
        for p in sorted(data.get('ambiguous_single_words', [])):
            print(f"  ❓ {p}")

    elif accion == 'bloquear':
        if len(args) < 1:
            print('Uso: python3 gestionar_amibot.py guardrails bloquear "<palabra>"')
            print('Ejemplo: python3 gestionar_amibot.py guardrails bloquear "certificado digital"')
            return

        palabra = args[0].strip().lower()
        data = _leer_json(ARCHIVO)

        if palabra in data.get('out_of_domain', []):
            print(f"ℹ️  '{palabra}' ya está bloqueada.")
            return

        data.setdefault('out_of_domain', []).append(palabra)
        _escribir_json(ARCHIVO, data)
        print(f"✅ Palabra bloqueada: '{palabra}' (el bot rechazará preguntas con esta palabra)")
        _recordar_reinicio()

    elif accion == 'desbloquear':
        if len(args) < 1:
            print('Uso: python3 gestionar_amibot.py guardrails desbloquear "<palabra>"')
            return

        palabra = args[0].strip().lower()
        data = _leer_json(ARCHIVO)

        if palabra not in data.get('out_of_domain', []):
            print(f"❌ '{palabra}' no está en la lista de bloqueadas.")
            return

        data['out_of_domain'].remove(palabra)
        _escribir_json(ARCHIVO, data)
        print(f"✅ Palabra desbloqueada: '{palabra}' (el bot ahora intentará responder)")
        _recordar_reinicio()

    elif accion == 'ambigua':
        if len(args) < 1:
            print('Uso: python3 gestionar_amibot.py guardrails ambigua "<palabra>"')
            return

        palabra = args[0].strip().lower()
        data = _leer_json(ARCHIVO)

        if palabra in data.get('ambiguous_single_words', []):
            print(f"ℹ️  '{palabra}' ya está en la lista de ambiguas.")
            return

        data.setdefault('ambiguous_single_words', []).append(palabra)
        _escribir_json(ARCHIVO, data)
        print(f"✅ Palabra ambigua agregada: '{palabra}'")
        _recordar_reinicio()

    else:
        print(f"❌ Acción '{accion}' no válida. Usa: listar, bloquear, desbloquear, ambigua")


# ═══════════════════════════════════════════════
#  MÓDULO 6: FAMILIAS (familias_categorias.json)
# ═══════════════════════════════════════════════

def gestionar_familias(accion, args):
    ARCHIVO = 'familias_categorias.json'

    if accion == 'listar':
        data = _leer_json(ARCHIVO)
        print(f"\n📋 Familias de categorías (agrupaciones para boost de intención):\n")
        for padre, hijos in sorted(data.items()):
            print(f"  📂 {padre}")
            for h in hijos:
                print(f"     └─ {h}")

    elif accion == 'agregar':
        if len(args) < 2:
            print('Uso: python3 gestionar_amibot.py familias agregar "<categoría_padre>" "<categoría_hija>"')
            print('Ejemplo: python3 gestionar_amibot.py familias agregar "tesis" "repositorio"')
            return

        padre = args[0].strip().lower()
        hijo = args[1].strip().lower()
        data = _leer_json(ARCHIVO)

        if hijo in data.get(padre, []):
            print(f"ℹ️  '{hijo}' ya está en la familia de '{padre}'.")
            return

        data.setdefault(padre, []).append(hijo)
        _escribir_json(ARCHIVO, data)
        print(f"✅ '{hijo}' ahora pertenece a la familia de '{padre}'")
        print(f"   (Las búsquedas de '{padre}' darán boost a respuestas de '{hijo}')")
        _recordar_reinicio()

    elif accion == 'eliminar':
        if len(args) < 2:
            print('Uso: python3 gestionar_amibot.py familias eliminar "<categoría_padre>" "<categoría_hija>"')
            return

        padre = args[0].strip().lower()
        hijo = args[1].strip().lower()
        data = _leer_json(ARCHIVO)

        if padre not in data or hijo not in data[padre]:
            print(f"❌ '{hijo}' no está en la familia de '{padre}'.")
            return

        data[padre].remove(hijo)
        if not data[padre]:
            del data[padre]
        _escribir_json(ARCHIVO, data)
        print(f"✅ '{hijo}' eliminada de la familia de '{padre}'")
        _recordar_reinicio()

    else:
        print(f"❌ Acción '{accion}' no válida. Usa: listar, agregar, eliminar")


# ═══════════════════════════════════════════════
#  MÓDULO 7: FILTRO (filtro_ruido.json)
# ═══════════════════════════════════════════════

def gestionar_filtro(accion, args):
    ARCHIVO = 'filtro_ruido.json'

    if accion == 'listar':
        data = _leer_json(ARCHIVO)
        print(f"\n📋 Filtro anti-ruido de catálogo:\n")
        print("  Palabras de castigo (si aparecen con 'libro', se filtra la respuesta):")
        for p in data.get('palabras_castigo', []):
            print(f"    🚫 {p}")
        print("\n  Palabras específicas (si el usuario las dice, NO se filtra):")
        for p in data.get('palabras_especificas', []):
            print(f"    ✅ {p}")
        print("\n  Excepciones (nunca se filtra si esta palabra está en la respuesta):")
        excep = data.get('excepciones', [])
        if excep:
            for p in excep:
                print(f"    ⭐ {p}")
        else:
            print("    (ninguna)")

    elif accion == 'excepcion':
        if len(args) < 1:
            print('Uso: python3 gestionar_amibot.py filtro excepcion "<palabra>"')
            print('Ejemplo: python3 gestionar_amibot.py filtro excepcion "interbibliotecario"')
            return

        palabra = args[0].strip().lower()
        data = _leer_json(ARCHIVO)

        if palabra in data.get('excepciones', []):
            print(f"ℹ️  '{palabra}' ya es una excepción.")
            return

        data.setdefault('excepciones', []).append(palabra)
        _escribir_json(ARCHIVO, data)
        print(f"✅ Excepción agregada: las respuestas con '{palabra}' ya no serán filtradas")
        _recordar_reinicio()

    elif accion == 'eliminar':
        if len(args) < 1:
            print('Uso: python3 gestionar_amibot.py filtro eliminar "<palabra>"')
            return

        palabra = args[0].strip().lower()
        data = _leer_json(ARCHIVO)

        eliminada = False
        for lista in ['excepciones', 'palabras_castigo', 'palabras_especificas']:
            if palabra in data.get(lista, []):
                data[lista].remove(palabra)
                eliminada = True
                print(f"✅ '{palabra}' eliminada de '{lista}'")

        if not eliminada:
            print(f"❌ '{palabra}' no se encontró en ninguna lista del filtro.")
            return

        _escribir_json(ARCHIVO, data)
        _recordar_reinicio()

    else:
        print(f"❌ Acción '{accion}' no válida. Usa: listar, excepcion, eliminar")


# ═══════════════════════════════════════════════
#  PUNTO DE ENTRADA PRINCIPAL
# ═══════════════════════════════════════════════

MODULOS = {
    "router": gestionar_router,
    "correcciones": gestionar_correcciones,
    "inmunidad": gestionar_inmunidad,
    "expansiones": gestionar_expansiones,
    "guardrails": gestionar_guardrails,
    "familias": gestionar_familias,
    "filtro": gestionar_filtro,
}


def mostrar_ayuda():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          GESTIONAR AMIBOT — Configuración Avanzada          ║
╚══════════════════════════════════════════════════════════════╝

Uso: python3 gestionar_amibot.py <módulo> <acción> [argumentos]

MÓDULOS DISPONIBLES:
  router          Reglas que deciden a qué categoría va cada pregunta
  correcciones    Errores de tipeo frecuentes (ej: "waifai" → "wifi")
  inmunidad       Palabras que el corrector ortográfico NO debe tocar
  expansiones     Sinónimos que ayudan a encontrar la respuesta correcta
  guardrails      Palabras que el bot debe rechazar (fuera de dominio)
  familias        Categorías relacionadas entre sí (para mejorar búsqueda)
  filtro          Control del filtro anti-ruido de catálogo

EJEMPLOS RÁPIDOS:
  python3 gestionar_amibot.py router listar
  python3 gestionar_amibot.py correcciones agregar "kompü" "computador"
  python3 gestionar_amibot.py inmunidad agregar "redalyc"
  python3 gestionar_amibot.py expansiones agregar "retornar" "devolucion entrega"
  python3 gestionar_amibot.py guardrails bloquear "certificado digital"
  python3 gestionar_amibot.py familias agregar "tesis" "repositorio"
  python3 gestionar_amibot.py filtro excepcion "interbibliotecario"

Para ver las acciones de cada módulo:
  python3 gestionar_amibot.py <módulo> ayuda
""")


# ═══════════════════════════════════════════════
#  MENÚ INTERACTIVO (WIZARD MODE)
# ═══════════════════════════════════════════════

def menu_router():
    while True:
        print("\n" + "─"*40)
        print("  [ROUTER] REGLAS DE ENRUTAMIENTO")
        print("─"*40)
        print("1. Listar reglas actuales")
        print("2. Agregar nueva regla")
        print("3. Eliminar regla existente")
        print("4. Agregar palabra a regla existente")
        print("5. Volver al menú principal")
        op = input("\nSelecciona una opción: ").strip()
        if op == '1':
            gestionar_router('listar', [])
        elif op == '2':
            intent = input("Nombre de la intención (ej: sala_computacion): ").strip()
            if not intent: continue
            palabras = input("Palabras clave (separadas por comas, ej: impresora 3d,sala de computacion): ").strip()
            excluir = input("Exclusiones (separadas por comas, opcional): ").strip()
            args = [intent, palabras]
            if excluir:
                args += ['--excluir', excluir]
            gestionar_router('agregar', args)
        elif op == '3':
            gestionar_router('listar', [])
            idx = input("\nIndica el número de la regla a eliminar: ").strip()
            if idx:
                gestionar_router('eliminar', [idx])
        elif op == '4':
            gestionar_router('listar', [])
            idx = input("\nIndica el número de la regla a modificar: ").strip()
            palabra = input("Nueva palabra a agregar a esta regla: ").strip()
            if idx and palabra:
                gestionar_router('palabra', [idx, palabra])
        elif op == '5':
            break

def menu_correcciones():
    while True:
        print("\n" + "─"*40)
        print("  [CORRECCIONES] ERRORES DE TIPEO FRECUENTES")
        print("─"*40)
        print("1. Listar correcciones actuales")
        print("2. Agregar nueva corrección")
        print("3. Eliminar corrección existente")
        print("4. Volver al menú principal")
        op = input("\nSelecciona una opción: ").strip()
        if op == '1':
            gestionar_correcciones('listar', [])
        elif op == '2':
            error = input("Palabra incorrecta (ej: kompü): ").strip().lower()
            correccion = input("Corrección correcta (ej: computador): ").strip().lower()
            if error and correccion:
                gestionar_correcciones('agregar', [error, correccion])
        elif op == '3':
            gestionar_correcciones('listar', [])
            error = input("\nPalabra incorrecta a eliminar: ").strip().lower()
            if error:
                gestionar_correcciones('eliminar', [error])
        elif op == '4':
            break

def menu_inmunidad():
    while True:
        print("\n" + "─"*40)
        print("  [INMUNIDAD] PROTEGER PALABRAS DEL CORRECTOR")
        print("─"*40)
        print("1. Listar palabras inmunes actuales")
        print("2. Agregar palabra inmune")
        print("3. Eliminar palabra inmune")
        print("4. Volver al menú principal")
        op = input("\nSelecciona una opción: ").strip()
        if op == '1':
            gestionar_inmunidad('listar', [])
        elif op == '2':
            palabra = input("Palabra a proteger (ej: redalyc): ").strip().lower()
            if palabra:
                gestionar_inmunidad('agregar', [palabra])
        elif op == '3':
            gestionar_inmunidad('listar', [])
            palabra = input("\nPalabra a eliminar de la lista: ").strip().lower()
            if palabra:
                gestionar_inmunidad('eliminar', [palabra])
        elif op == '4':
            break

def menu_expansiones():
    while True:
        print("\n" + "─"*40)
        print("  [EXPANSIONES] SINÓNIMOS DE INTENCIÓN")
        print("─"*40)
        print("1. Listar expansiones actuales")
        print("2. Agregar nueva expansión")
        print("3. Eliminar expansión")
        print("4. Volver al menú principal")
        op = input("\nSelecciona una opción: ").strip()
        if op == '1':
            gestionar_expansiones('listar', [])
        elif op == '2':
            sinonimo = input("Sinónimo a agregar (ej: retornar): ").strip().lower()
            expansion = input("Palabras clave de intención asociadas (ej: devolucion entrega): ").strip().lower()
            if sinonimo and expansion:
                gestionar_expansiones('agregar', [sinonimo, expansion])
        elif op == '3':
            gestionar_expansiones('listar', [])
            sinonimo = input("\nSinónimo a eliminar: ").strip().lower()
            if sinonimo:
                gestionar_expansiones('eliminar', [sinonimo])
        elif op == '4':
            break

def menu_guardrails():
    while True:
        print("\n" + "─"*40)
        print("  [GUARDRAILS] FILTRADO DE CONSULTAS")
        print("─"*40)
        print("1. Listar configuración de guardrails")
        print("2. Bloquear palabra (fuera de dominio)")
        print("3. Desbloquear palabra (permitir búsqueda)")
        print("4. Agregar palabra ambigua (requiere contexto)")
        print("5. Volver al menú principal")
        op = input("\nSelecciona una opción: ").strip()
        if op == '1':
            gestionar_guardrails('listar', [])
        elif op == '2':
            palabra = input("Palabra a bloquear (ej: certificado digital): ").strip().lower()
            if palabra:
                gestionar_guardrails('bloquear', [palabra])
        elif op == '3':
            gestionar_guardrails('listar', [])
            palabra = input("\nPalabra a desbloquear: ").strip().lower()
            if palabra:
                gestionar_guardrails('desbloquear', [palabra])
        elif op == '4':
            palabra = input("Palabra ambigua a agregar (ej: tesis): ").strip().lower()
            if palabra:
                gestionar_guardrails('ambigua', [palabra])
        elif op == '5':
            break

def menu_familias():
    while True:
        print("\n" + "─"*40)
        print("  [FAMILIAS] AGRUPACIONES PARA BOOST DE INTENCIÓN")
        print("─"*40)
        print("1. Listar familias actuales")
        print("2. Agregar categoría secundaria a categoría principal")
        print("3. Eliminar relación de familia")
        print("4. Volver al menú principal")
        op = input("\nSelecciona una opción: ").strip()
        if op == '1':
            gestionar_familias('listar', [])
        elif op == '2':
            padre = input("Categoría principal/padre (ej: tesis): ").strip().lower()
            hijo = input("Categoría secundaria/hija (ej: repositorio): ").strip().lower()
            if padre and hijo:
                gestionar_familias('agregar', [padre, hijo])
        elif op == '3':
            gestionar_familias('listar', [])
            padre = input("\nCategoría principal/padre: ").strip().lower()
            hijo = input("Categoría secundaria/hija a eliminar: ").strip().lower()
            if padre and hijo:
                gestionar_familias('eliminar', [padre, hijo])
        elif op == '4':
            break

def menu_filtro():
    while True:
        print("\n" + "─"*40)
        print("  [FILTRO] EVITAR FALSOS POSITIVOS DE CATÁLOGO")
        print("─"*40)
        print("1. Listar configuración del filtro")
        print("2. Agregar excepción (palabras permitidas en respuestas)")
        print("3. Eliminar palabra o excepción")
        print("4. Volver al menú principal")
        op = input("\nSelecciona una opción: ").strip()
        if op == '1':
            gestionar_filtro('listar', [])
        elif op == '2':
            palabra = input("Palabra de excepción (ej: interbibliotecario): ").strip().lower()
            if palabra:
                gestionar_filtro('excepcion', [palabra])
        elif op == '3':
            gestionar_filtro('listar', [])
            palabra = input("\nPalabra a eliminar del filtro: ").strip().lower()
            if palabra:
                gestionar_filtro('eliminar', [palabra])
        elif op == '4':
            break

def menu_agregar_conocimiento():
    print("\n" + "─"*40)
    print("  [CONOCIMIENTO] AGREGAR ENTRADA A LA BASE DE DATOS")
    print("─"*40)
    try:
        sys.path.append(BASE_DIR)
        from agregar_conocimiento import ARCHIVO_JSON, agregar_entrada
        path_json = os.path.join(BASE_DIR, ARCHIVO_JSON)
        
        with open(path_json, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        cats = sorted(list(set(d['categoria'] for d in datos if 'categoria' in d)))
        
        print("Categorías existentes en la base de conocimiento:")
        for c in cats:
            print(f"  - {c}")
            
        categoria = input("\nIntroduce la categoría (o escribe una nueva): ").strip()
        if not categoria:
            print("❌ Categoría requerida.")
            return
            
        pregunta = input("Introduce la pregunta o palabras clave del usuario: ").strip()
        if not pregunta:
            print("❌ Pregunta/palabras clave requeridas.")
            return
            
        respuesta = input("Introduce la respuesta oficial del bot: ").strip()
        if not respuesta:
            print("❌ Respuesta requerida.")
            return
            
        agregar_entrada(path_json, categoria, pregunta, respuesta, confirmar_nueva=True)
        print("\n⚠️  IMPORTANTE: Recuerda ejecutar ./deploy.sh (si estás en local) y reiniciar.sh en producción para re-indexar la base.")
    except Exception as e:
        print(f"❌ Error al agregar conocimiento: {e}")

def menu_diagnostico():
    while True:
        print("\n" + "─"*70)
        print("  🔍 ASISTENTE DE DIAGNÓSTICO — ¿QUÉ PROBLEMA DESEAS RESOLVER?")
        print("─"*70)
        print("1. El bot responde 'No tengo información' (Falta la respuesta en la base).")
        print("2. El bot da una respuesta incorrecta de otro tema (ej: confunde salas con casilleros).")
        print("3. El bot no entiende una palabra escrita con faltas graves (ej: 'kompu' en vez de 'computador').")
        print("4. El corrector altera un nombre propio o técnico (ej: el usuario escribe 'redalyc' y el bot entiende 'radical').")
        print("5. El bot no entiende un sinónimo (ej: el usuario dice 'retornar' pero el bot solo sabe 'devolver').")
        print("6. El bot responde a temas no permitidos o chistes, o bloquea temas válidos (guardrails).")
        print("7. Creé una categoría nueva y el bot no le da prioridad en las búsquedas relacionadas.")
        print("8. El bot no muestra una respuesta válida que menciona cobros, precios o multas (filtro anti-ruido).")
        print("9. Volver al menú principal")
        print("─"*70)
        
        op = input("\nSelecciona el síntoma (1-9): ").strip()
        if op == '1':
            print("\n💡 Diagnóstico: Falta esa respuesta en el archivo de conocimiento.")
            conf = input("   ¿Deseas ir al asistente para agregar esta respuesta ahora? (s/n): ").strip().lower()
            if conf == 's':
                menu_agregar_conocimiento()
                break
        elif op == '2':
            print("\n💡 Diagnóstico: El enrutador (router) necesita reglas para asociar esa palabra clave al tema correcto.")
            conf = input("   ¿Deseas ir al menú del Router para configurarlo ahora? (s/n): ").strip().lower()
            if conf == 's':
                menu_router()
                break
        elif op == '3':
            print("\n💡 Diagnóstico: Se requiere agregar una regla de corrección ortográfica manual para esa palabra específica.")
            conf = input("   ¿Deseas ir al menú de Correcciones ahora? (s/n): ").strip().lower()
            if conf == 's':
                menu_correcciones()
                break
        elif op == '4':
            print("\n💡 Diagnóstico: El corrector automático confunde la palabra técnica. Debes agregarla a la lista de 'inmunidad'.")
            conf = input("   ¿Deseas ir al menú de Inmunidad ahora? (s/n): ").strip().lower()
            if conf == 's':
                menu_inmunidad()
                break
        elif op == '5':
            print("\n💡 Diagnóstico: Se necesita configurar una expansión de intención para asociar ese sinónimo a la categoría correcta.")
            conf = input("   ¿Deseas ir al menú de Sinónimos/Expansiones ahora? (s/n): ").strip().lower()
            if conf == 's':
                menu_expansiones()
                break
        elif op == '6':
            print("\n💡 Diagnóstico: El bot está bloqueando (o permitiendo) términos indebidos. Ajusta los guardrails de dominio.")
            conf = input("   ¿Deseas ir al menú de Guardrails ahora? (s/n): ").strip().lower()
            if conf == 's':
                menu_guardrails()
                break
        elif op == '7':
            print("\n💡 Diagnóstico: Debes relacionar la categoría nueva con la categoría principal (crear una Familia de categorías).")
            conf = input("   ¿Deseas ir al menú de Familias ahora? (s/n): ").strip().lower()
            if conf == 's':
                menu_familias()
                break
        elif op == '8':
            print("\n💡 Diagnóstico: El bot tiene un filtro que oculta respuestas con números y precios (para evitar ruidos de catálogo).")
            print("   Debes agregar la palabra clave (ej: 'multa', 'pago') como excepción en el filtro anti-ruido.")
            conf = input("   ¿Deseas ir al menú del Filtro ahora? (s/n): ").strip().lower()
            if conf == 's':
                menu_filtro()
                break
        elif op == '9':
            break
        else:
            print("❌ Opción no válida.")

def menu_interactivo():
    while True:
        print("\n" + "═"*55)
        print("     GESTIONAR AMIBOT — MENÚ INTERACTIVO (WIZARD)")
        print("═"*55)
        print("  1. 🔍 Asistente de Diagnóstico (¿Qué problema deseas resolver?)")
        print("  2. Enrutamiento (router) — ¿Qué categoría responde a qué?")
        print("  3. Corrección de escritura — Errores frecuentes de alumnos")
        print("  4. Proteger palabras (inmunidad) — Nombres propios/técnicos")
        print("  5. Sinónimos (expansiones) — Sinónimos que amplían la intención")
        print("  6. Bloquear temas (guardrails) — Preguntas fuera de ámbito")
        print("  7. Relacionar categorías (familias) — Boost de prioridad")
        print("  8. Excepciones del filtro — Respuestas con precios/multas")
        print("  9. Agregar conocimiento — Pregunta/respuesta en la base JSON")
        print("  10. Salir")
        print("═"*55)
        
        opcion = input("\nSelecciona una opción (1-10): ").strip()
        if opcion == '1':
            menu_diagnostico()
        elif opcion == '2':
            menu_router()
        elif opcion == '3':
            menu_correcciones()
        elif opcion == '4':
            menu_inmunidad()
        elif opcion == '5':
            menu_expansiones()
        elif opcion == '6':
            menu_guardrails()
        elif opcion == '7':
            menu_familias()
        elif opcion == '8':
            menu_filtro()
        elif opcion == '9':
            menu_agregar_conocimiento()
        elif opcion == '10':
            print("¡Hasta luego!")
            break
        else:
            print("❌ Opción no válida. Por favor, introduce un número del 1 al 10.")


def main():
    if len(sys.argv) < 2:
        menu_interactivo()
        sys.exit(0)
    elif len(sys.argv) < 3:
        mostrar_ayuda()
        sys.exit(0)

    modulo = sys.argv[1].lower()
    accion = sys.argv[2].lower()
    args = sys.argv[3:]

    if modulo not in MODULOS:
        print(f"❌ Módulo '{modulo}' no existe.\n")
        print(f"Módulos válidos: {', '.join(MODULOS.keys())}")
        sys.exit(1)

    try:
        MODULOS[modulo](accion, args)
    except FileNotFoundError as e:
        print(f"❌ Archivo de configuración no encontrado: {e}")
        print(f"   Verifica que exista la carpeta: {CONFIG_DIR}")
    except json.JSONDecodeError as e:
        print(f"❌ Error de formato JSON: {e}")
        print(f"   Revisa que no haya comas o comillas mal puestas en el archivo.")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")


if __name__ == "__main__":
    main()
