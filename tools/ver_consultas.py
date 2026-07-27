#!/usr/bin/env python3
import sqlite3
import time
import os
import socket
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich import box

try:
    from config import DB_PATH
    DB = DB_PATH
except ImportError:
    DB = os.path.join(os.path.dirname(__file__), "consultas.db")


class TelemetryDB:
    """Capa de Datos: Se encarga exclusivamente de las consultas SQL optimizadas."""
    def __init__(self, db_path):
        self.db_path = db_path
        # Se abre UNA sola conexión y se mantiene viva. Thread-safety habilitado si se requiere.
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def obtener_metricas(self) -> dict:
        cursor = self.conn.cursor()
        hoy_str = datetime.now().strftime("%Y-%m-%d")
        
        # 1. MEGA-CONSULTA: Consolida 11 consultas individuales en 1 solo escaneo (Ahorro brutal de I/O)
        query_global = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN fecha LIKE ? THEN 1 ELSE 0 END) as hoy,
                SUM(CASE WHEN tiempo > 2.0 THEN 1 ELSE 0 END) as lentas,
                SUM(CASE WHEN feedback = 'like' THEN 1 ELSE 0 END) as likes,
                SUM(CASE WHEN feedback = 'dislike' THEN 1 ELSE 0 END) as dislikes,
                SUM(CASE WHEN estado LIKE '%escalado_humano%' OR estado = 'rechazo' THEN 1 ELSE 0 END) as fallos,
                SUM(CASE WHEN llm_usado = 1 THEN 1 ELSE 0 END) as llm_usados,
                SUM(CASE WHEN feedback_comentario IS NOT NULL AND feedback_comentario != '' THEN 1 ELSE 0 END) as con_comentario,
                SUM(CASE WHEN feedback IS NOT NULL THEN 1 ELSE 0 END) as con_feedback,
                COUNT(DISTINCT sesion_id) as usuarios_unicos_total,
                COUNT(DISTINCT CASE WHEN fecha LIKE ? AND sesion_id IS NOT NULL THEN sesion_id END) as usuarios_unicos_hoy
            FROM consultas
        """
        cursor.execute(query_global, (f"{hoy_str}%", f"{hoy_str}%"))
        row = cursor.fetchone()
        
        # Sanitización de datos por si la tabla está vacía
        metrics = {k: (v if v is not None else 0) for k, v in dict(row).items()}
        metrics['exitos'] = metrics['total'] - metrics['fallos']
        
        # 2. Tiempos (Promedio y P95)
        cursor.execute("SELECT tiempo FROM consultas WHERE tiempo IS NOT NULL")
        tiempos = [r['tiempo'] for r in cursor.fetchall()]
        if tiempos:
            tiempos.sort()
            metrics['tiempo_promedio'] = sum(tiempos) / len(tiempos)
            metrics['tiempo_p95'] = tiempos[int(len(tiempos) * 0.95)]
        else:
            metrics['tiempo_promedio'] = 0.0
            metrics['tiempo_p95'] = 0.0

        # 3. Distribución de Estados (Consolidado)
        query_estados = """
            SELECT 
                SUM(CASE WHEN estado='exito_textual' THEN 1 ELSE 0 END) as bypass,
                SUM(CASE WHEN estado='exito_rag' THEN 1 ELSE 0 END) as rag,
                SUM(CASE WHEN estado LIKE 'exito_%' AND estado NOT IN ('exito_textual', 'exito_rag') THEN 1 ELSE 0 END) as atajadas,
                SUM(CASE WHEN estado='escalado_humano' THEN 1 ELSE 0 END) as humano,
                SUM(CASE WHEN estado='consulta_humano' THEN 1 ELSE 0 END) as consulta_humano
            FROM consultas
        """
        cursor.execute(query_estados)
        row_estados = cursor.fetchone()
        metrics.update({k: (v if v is not None else 0) for k, v in dict(row_estados).items()})

        # 4. Tablas Top 10 (Estas consultas requieren GROUP BY, así que deben ir separadas)
        metrics['top10'] = cursor.execute("SELECT pregunta, COUNT(*) as n FROM consultas GROUP BY pregunta ORDER BY n DESC LIMIT 10").fetchall()
        metrics['fallidas'] = cursor.execute("SELECT pregunta, COUNT(*) as n FROM consultas WHERE estado LIKE '%escalado_humano%' GROUP BY pregunta ORDER BY n DESC LIMIT 10").fetchall()
        metrics['reportadas'] = cursor.execute("SELECT pregunta, COUNT(*) as n FROM consultas WHERE feedback='dislike' GROUP BY pregunta ORDER BY n DESC LIMIT 10").fetchall()
        metrics['intents'] = cursor.execute("SELECT intent, COUNT(*) as n FROM consultas WHERE intent IS NOT NULL GROUP BY intent ORDER BY n DESC LIMIT 10").fetchall()
        metrics['comentarios'] = cursor.execute("SELECT pregunta, feedback_comentario FROM consultas WHERE feedback_comentario IS NOT NULL AND feedback_comentario != '' ORDER BY id DESC LIMIT 8").fetchall()
        
        return metrics

    def cerrar(self):
        self.conn.close()


class DashboardUI:
    """Capa de Presentación: Exclusivamente dedicada a renderizar los datos usando la librería Rich."""
    @staticmethod
    def check_port(port: int) -> str:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            return "[bold green]ONLINE[/bold green]" if s.connect_ex(('127.0.0.1', port)) == 0 else "[bold red]OFFLINE[/bold red]"

    @staticmethod
    def construir_layout(metrics: dict) -> Layout:
        now = datetime.now().strftime("%H:%M:%S")
        total = metrics['total']
        
        pct_exito = (100 * metrics['exitos'] / total) if total > 0 else 0
        pct_fallo = (100 * metrics['fallos'] / total) if total > 0 else 0
        pct_feedback = (100 * metrics['con_feedback'] / total) if total > 0 else 0

        barra_exito = f"\n[green]{'█' * int(pct_exito / 2)}{'▒' * (50 - int(pct_exito / 2))}[/green] {pct_exito:.1f}%"
        barra_fallo = f"\n[red]{'█' * int(pct_fallo / 2)}{'▒' * (50 - int(pct_fallo / 2))}[/red] {pct_fallo:.1f}%"

        # --- PANEL 1: TABLA RESUMEN ---
        tabla = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True)
        tabla.add_column(style="cyan", width=28)
        tabla.add_column(style="white")
        tabla.add_row("Total consultas", str(total))
        tabla.add_row("Consultas de Hoy", f"[bold white]{metrics['hoy']}[/bold white]")
        tabla.add_row("Usuarios únicos (hoy)", f"[bold white]{metrics['usuarios_unicos_hoy']}[/bold white]")
        tabla.add_row("Usuarios únicos (total)", str(metrics['usuarios_unicos_total']))
        tabla.add_row("Consultas Lentas (> 2s)", f"[bold red]{metrics['lentas']}[/bold red]" if metrics['lentas'] > 0 else "[green]0[/green]")
        tabla.add_row("Latencia Promedio", f"[yellow]{metrics['tiempo_promedio']*1000:.0f} ms[/yellow]")
        tabla.add_row("Latencia P95 (Peor caso)", f"[bold red]{metrics['tiempo_p95']*1000:.0f} ms[/bold red]")
        tabla.add_row("Valoración Positiva 👍", f"[bold green]{metrics['likes']}[/bold green]")
        tabla.add_row("Valoración Negativa 👎", f"[bold red]{metrics['dislikes']}[/bold red]")
        tabla.add_row("Comentarios en dislikes", f"[yellow]{metrics['con_comentario']}[/yellow]")
        tabla.add_row("Tasa de feedback", f"[cyan]{pct_feedback:.1f}%[/cyan]")
        tabla.add_row("Consultas con LLM (Ollama)", f"[magenta]{metrics['llm_usados']}[/magenta]")

        # --- PANEL 2: DISTRIBUCIÓN ---
        distribucion = Table(box=box.SIMPLE_HEAVY, show_header=True, expand=True)
        distribucion.add_column("Estado", style="cyan")
        distribucion.add_column("Cantidad", style="white", justify="right")
        distribucion.add_column("Porcentaje", justify="right")
        
        estados_lista = [
            ("Bypass (CPU Ahorrada)", 'bypass', "green"),
            ("RAG (IA Usada)", 'rag', "yellow"),
            ("Fuera de ámbito (ChitChat)", 'atajadas', "magenta"),
            ("Escalado a humano", 'humano', "red"),
            ("Consulta humana", 'consulta_humano', "blue")
        ]
        
        for name, key, color in estados_lista:
            val = metrics[key]
            pct = f"[{color}]{100*val/total:.1f}%[/{color}]" if total else "-"
            distribucion.add_row(name, str(val), pct)

        # --- PANELES 3 y 4: TABLAS SIMPLES ---
        def crear_tabla_sencilla(titulo, color, datos, prop1, prop2="n"):
            t = Table(box=box.SIMPLE_HEAVY, show_header=True, expand=True)
            t.add_column(titulo, style=color)
            t.add_column("Veces" if prop2 == "n" else "Comentario", justify="center" if prop2 == "n" else "left")
            for r in datos:
                val1 = str(r[prop1])[:70] if r[prop1] else "-"
                val2 = str(r[prop2])[:60] if r[prop2] else "-"
                t.add_row(val1, val2)
            if not datos:
                t.add_row("[dim]Sin datos registrados[/dim]", "")
            return t

        tabla_top = crear_tabla_sencilla("Pregunta (Top 10 Histórico)", "cyan", metrics['top10'], "pregunta")
        tabla_fallos = crear_tabla_sencilla("Pregunta no respondida", "red", metrics['fallidas'], "pregunta")
        tabla_reportes = crear_tabla_sencilla("Respuestas con Dislike 👎", "yellow", metrics['reportadas'], "pregunta")
        tabla_comentarios = crear_tabla_sencilla("Comentarios de estudiantes (Dislikes)", "red", metrics['comentarios'], "pregunta", "feedback_comentario")

        # --- PANEL 6: INTENTS ---
        tabla_intents = Table(box=box.SIMPLE_HEAVY, show_header=True, expand=True)
        tabla_intents.add_column("Intent", style="cyan")
        tabla_intents.add_column("Cantidad", justify="center")
        tabla_intents.add_column("%", justify="right")
        for r in metrics['intents']:
            pct = (100 * r['n'] / total) if total > 0 else 0
            tabla_intents.add_row(str(r['intent']), str(r['n']), f"{pct:.1f}%")
        if not metrics['intents']:
            tabla_intents.add_row("[dim]Sin datos de intent[/dim]", "", "")

        # --- CONSTRUCCIÓN DEL LAYOUT (Cuadrícula) ---
        api_status = DashboardUI.check_port(8000)
        ollama_status = DashboardUI.check_port(11434)
        
        layout = Layout()
        layout.split_column(
            Layout(Panel(f"[bold cyan]CHATBOT BIBLIOTECA - MONITOR OPERACIONAL AVANZADO[/bold cyan]  [dim]{now}[/dim] | API: {api_status} | Ollama: {ollama_status}"), size=3),
            Layout(name="fila_superior", ratio=4),
            Layout(name="fila_media", ratio=5),
            Layout(name="fila_inferior", ratio=5)
        )
        
        layout["fila_superior"].split_row(
            Layout(Panel(tabla, title="Resumen General")),
            Layout(Panel(distribucion, title="Distribución Operacional")),
            Layout(Panel(barra_exito + "\n" + barra_fallo, title="Métricas de Efectividad"))
        )
        layout["fila_media"].split_row(
            Layout(Panel(tabla_intents, title="Distribución de Intenciones")),
            Layout(Panel(tabla_top, title="Top 10 Preguntas Frecuentes")),
            Layout(Panel(tabla_fallos, title="Brechas de Conocimiento (No respondidas)"))
        )
        layout["fila_inferior"].split_row(
            Layout(Panel(tabla_reportes, title="Control de Calidad (Dislikes)")),
            Layout(Panel(tabla_comentarios, title="Auditoría de Comentarios"))
        )
        
        return layout


class TelemetryApp:
    """Controlador Principal (App): Une el Modelo (DB) con la Vista (UI) y maneja el ciclo de vida."""
    def __init__(self):
        self.db = TelemetryDB(DB)
        self.console = Console()

    def run(self):
        try:
            # Refresh rate = 1 frame/s. El ciclo sleep dicta que consultamos DB cada 3 segundos.
            with Live(DashboardUI.construir_layout(self.db.obtener_metricas()), console=self.console, refresh_per_second=1, screen=True) as live:
                while True:
                    time.sleep(3)
                    # El refactor eliminó los cuellos de botella; ahora extraer métricas toma milisegundos.
                    metrics = self.db.obtener_metricas()
                    live.update(DashboardUI.construir_layout(metrics))
        
        except KeyboardInterrupt:
            self.console.clear()
            self.console.print("[bold green]Monitor cerrado correctamente. Conexiones a base de datos liberadas.[/bold green]\n")
        
        except sqlite3.Error as e:
            self.console.print(f"[bold red]Error Fatal de Base de Datos:[/bold red] {e}")
        
        finally:
            self.db.cerrar()


if __name__ == "__main__":
    app = TelemetryApp()
    app.run()
