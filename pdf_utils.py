from fpdf import FPDF
from datetime import datetime
import matplotlib
matplotlib.use('Agg') # Non-interactive backend
import matplotlib.pyplot as plt
import io
import tempfile
import os

class PDFReport(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        # Brand Colors - Caja de Abogados (Bright Blue)
        self.set_fill_color(0, 119, 190)  # Bright Blue
        self.rect(0, 0, 210, 40, 'F')
        
        # Title
        self.set_font('Arial', 'B', 24)
        self.set_text_color(255, 255, 255)
        self.set_y(15)
        self.cell(0, 10, 'Gestor de Tareas Federal', 0, 1, 'C')
        
        self.set_font('Arial', '', 12)
        self.cell(0, 10, 'Reporte de Tareas', 0, 1, 'C')
        
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}} - Generado el {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 0, 'C')

def generate_charts_for_pdf(data):
    paths = {}
    
    # 1. User Progress (Stacked Bar)
    try:
        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        
        user_stats = data['user_stats']
        names = [u['name'] for u in user_stats]
        completed = [u['completed'] for u in user_stats]
        pending = [u['pending'] for u in user_stats]
        
        plt.figure(figsize=(10, 6))
        plt.bar(names, completed, label='Completadas', color='#10b981')
        plt.bar(names, pending, bottom=completed, label='Pendientes', color='#f59e0b')
        plt.xlabel('Usuarios')
        plt.ylabel('Cantidad de Tareas')
        plt.title('Progreso por Usuario')
        plt.legend()
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(path, format='png', dpi=100)
        plt.close()
        paths['user'] = path
    except Exception as e:
        print(f"Error generating user chart: {e}")
        if os.path.exists(path): os.remove(path)

    # 2. Status Distribution (Doughnut)
    try:
        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        
        global_stats = data['global_stats']
        labels = ['Completadas', 'Pendientes']
        sizes = [global_stats['completed'], global_stats['pending']]
        colors = ['#10b981', '#f59e0b']
        
        plt.figure(figsize=(6, 6))
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, pctdistance=0.85)
        # Draw circle for doughnut
        centre_circle = plt.Circle((0,0),0.70,fc='white')
        fig = plt.gcf()
        fig.gca().add_artist(centre_circle)
        plt.title('Estado Global')
        plt.tight_layout()
        plt.savefig(path, format='png', dpi=100)
        plt.close()
        paths['status'] = path
    except Exception as e:
        print(f"Error generating status chart: {e}")
        if os.path.exists(path): os.remove(path)

    # 3. Trend (Line)
    try:
        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        
        trend = data['trend']
        dates = [datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m') for d in trend['dates']]
        counts = trend['completed_counts']
        
        plt.figure(figsize=(10, 6))
        plt.plot(dates, counts, marker='o', linestyle='-', color='#3b82f6', linewidth=2)
        plt.fill_between(dates, counts, color='#3b82f6', alpha=0.1)
        plt.xlabel('Fecha')
        plt.ylabel('Tareas Completadas')
        plt.title('Tendencia de Finalización (Global)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(path, format='png', dpi=100)
        plt.close()
        paths['trend'] = path
    except Exception as e:
        print(f"Error generating trend chart: {e}")
        if os.path.exists(path): os.remove(path)

    # 4. Employee Trend (Multi-Line)
    try:
        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        
        emp_trends = data.get('employee_trend', [])
        dates = [datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m') for d in data['trend']['dates']]
        
        plt.figure(figsize=(10, 6))
        for emp in emp_trends:
            plt.plot(dates, emp['data'], marker='.', linestyle='-', label=emp['label'])
            
        plt.xlabel('Fecha')
        plt.ylabel('Tareas Completadas')
        plt.title('Evolución por Empleado')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(path, format='png', dpi=100)
        plt.close()
        paths['employee_trend'] = path
    except Exception as e:
        print(f"Error generating employee trend chart: {e}")
        if os.path.exists(path): os.remove(path)

    # 5. Tag Trend (Multi-Line)
    try:
        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        
        tag_trends = data.get('tag_trend', [])
        dates = [datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m') for d in data['trend']['dates']]
        
        plt.figure(figsize=(10, 6))
        for tag in tag_trends:
            plt.plot(dates, tag['data'], marker='.', linestyle='-', label=tag['label'], color=tag['color'])
            
        plt.xlabel('Fecha')
        plt.ylabel('Tareas Completadas')
        plt.title('Evolución por Etiqueta')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(path, format='png', dpi=100)
        plt.close()
        paths['tag_trend'] = path
    except Exception as e:
        print(f"Error generating tag trend chart: {e}")
        if os.path.exists(path): os.remove(path)
        
    return paths

def generate_report_pdf(data):
    pdf = PDFReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- Report Header Info ---
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 10, 'Reporte Avanzado de Progreso', 0, 1)
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"Periodo: {data['start_date']} al {data['end_date']}", 0, 1)
    
    # Users
    users_str = ', '.join(data['filters']['users'][:5]) + ("..." if len(data['filters']['users']) > 5 else "")
    pdf.cell(0, 6, f"Usuarios: {users_str}", 0, 1)
    
    # Tags
    tags_str = ', '.join(data['filters']['tags'][:5]) + ("..." if len(data['filters']['tags']) > 5 else "")
    pdf.cell(0, 6, f"Etiquetas: {tags_str}", 0, 1)
    
    # Status
    status_trans = "Completada" if data['filters']['status'] == 'Completed' else ("Pendiente" if data['filters']['status'] == 'Pending' else "Todos")
    pdf.cell(0, 6, f"Estado: {status_trans}", 0, 1)
    
    pdf.ln(5)
    
    # --- Charts Section ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Tablero de Control', 0, 1)
    
    chart_paths = generate_charts_for_pdf(data)
    
    # --- KPIs Section (Optional) ---
    if 'kpis' in data:
        kpis = data['kpis']
        
        # Draw 4 cards
        y_start = pdf.get_y()
        card_width = 45
        spacing = 4
        x_start = 10
        card_width = 35  # Narrower to fit 5 cards
        
        # Card 1: Total
        pdf.set_fill_color(243, 244, 246) # Gray 100
        pdf.rect(x_start, y_start, card_width, 25, 'F')
        pdf.set_xy(x_start, y_start + 5)
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(0, 119, 190) # Brand Blue
        pdf.cell(card_width, 6, str(kpis['total']), 0, 2, 'C')
        pdf.set_font('Arial', '', 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(card_width, 6, 'Total Tareas', 0, 0, 'C')
        
        # Card 2: Completion Rate
        x_pos = x_start + card_width + spacing
        pdf.set_fill_color(209, 250, 229) # Emerald 100
        pdf.rect(x_pos, y_start, card_width, 25, 'F')
        pdf.set_xy(x_pos, y_start + 5)
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(4, 120, 87) # Emerald 700
        pdf.cell(card_width, 6, f"{kpis['completion_rate']}%", 0, 2, 'C')
        pdf.set_font('Arial', '', 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(card_width, 6, 'Tasa Finalización', 0, 0, 'C')
        
        # Card 3: Overdue
        x_pos += card_width + spacing
        pdf.set_fill_color(254, 226, 226) # Red 100
        pdf.rect(x_pos, y_start, card_width, 25, 'F')
        pdf.set_xy(x_pos, y_start + 5)
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(185, 28, 28) # Red 700
        pdf.cell(card_width, 6, str(kpis['overdue']), 0, 2, 'C')
        pdf.set_font('Arial', '', 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(card_width, 6, 'Vencidas', 0, 0, 'C')
        
        # Card 4: Avg Time
        x_pos += card_width + spacing
        pdf.set_fill_color(219, 234, 254) # Blue 100
        pdf.rect(x_pos, y_start, card_width, 25, 'F')
        pdf.set_xy(x_pos, y_start + 5)
        pdf.set_font('Arial', 'B', 10) # Smaller font for text
        pdf.set_text_color(29, 78, 216) # Blue 700
        pdf.cell(card_width, 6, str(kpis['avg_time']), 0, 2, 'C')
        pdf.set_font('Arial', '', 7)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(card_width, 6, 'Tiempo Promedio', 0, 0, 'C')
        
        # Card 5: Total Time
        x_pos += card_width + spacing
        pdf.set_fill_color(237, 233, 254) # Violet 100
        pdf.rect(x_pos, y_start, card_width, 25, 'F')
        pdf.set_xy(x_pos, y_start + 5)
        pdf.set_font('Arial', 'B', 9)
        pdf.set_text_color(109, 40, 217) # Violet 700
        pdf.cell(card_width, 6, str(kpis.get('total_time', '0 min')), 0, 2, 'C')
        pdf.set_font('Arial', '', 7)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(card_width, 6, 'Tiempo Total', 0, 0, 'C')
        
        pdf.ln(35) # Move down past cards

    # --- Difference Calculator Section ---
    if 'diff_calc' in data:
        diff = data['diff_calc']
        
        # Check if we have space, else add page
        if pdf.get_y() > 250:
             pdf.add_page()

        pdf.set_fill_color(248, 250, 252) # Slate 50
        # Draw background box for this section
        y_start = pdf.get_y()
        pdf.rect(10, y_start, 190, 35, 'F')
        
        pdf.set_xy(10, y_start + 5)
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 8, 'Diferencia de Horas', 0, 1, 'C') # Centered title
        
        pdf.set_font('Arial', '', 11)
        # Construct the string: "TagA, TagB: time  -  TagC: time"
        # We'll split this into two lines if needed or use multi_cell centered.
        
        # Format:
        # Group A: [Names] ([Time])
        # Group B: [Names] ([Time])
        
        info_a = f"{diff['tag_a']['name']} ({diff['tag_a']['time']})"
        info_b = f"{diff['tag_b']['name']} ({diff['tag_b']['time']})"
        
        pdf.set_x(15)
        pdf.multi_cell(180, 6, f"{info_a}  -  {info_b}", 0, 'C')
        
        pdf.set_font('Arial', 'B', 14)
        if diff['result'].startswith('-'):
             pdf.set_text_color(220, 38, 38) # Red 600
        else:
             pdf.set_text_color(5, 150, 105) # Emerald 600
             
        pdf.cell(0, 10, f"Diferencia: {diff['result']}", 0, 1, 'C')
        
        pdf.set_text_color(0, 0, 0) # Reset
        pdf.set_y(pdf.get_y() + 5) # Ensure spacing

    y_charts = pdf.get_y()
    
    if 'status' in chart_paths:
        pdf.image(chart_paths['status'], x=10, y=y_charts, w=70)
        os.remove(chart_paths['status'])
        
    if 'trend' in chart_paths:
        pdf.image(chart_paths['trend'], x=85, y=y_charts, w=115)
        os.remove(chart_paths['trend'])
        
    pdf.ln(75) # Move down past row 1
    
    # Row 2: User Progress (Full Width)
    if 'user' in chart_paths:
        pdf.image(chart_paths['user'], x=10, w=190, h=80)
        os.remove(chart_paths['user'])
        
    pdf.ln(85)

    # --- Detailed Trends Page ---
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Análisis de Tendencias Detallado', 0, 1)
    
    y_charts = pdf.get_y()
    
    # Employee Trend
    if 'employee_trend' in chart_paths:
        pdf.image(chart_paths['employee_trend'], x=10, y=y_charts, w=190, h=100)
        os.remove(chart_paths['employee_trend'])
        pdf.ln(110)
    else:
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 10, 'No hay datos suficientes para generar el gráfico de evolución por empleado.', 0, 1)
        pdf.ln(10)
    
    # Tag Trend
    y_charts = pdf.get_y()
    if 'tag_trend' in chart_paths:
        pdf.image(chart_paths['tag_trend'], x=10, y=y_charts, w=190, h=100)
        os.remove(chart_paths['tag_trend'])
        pdf.ln(10)
    else:
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 10, 'No hay datos suficientes para generar el gráfico de evolución por etiqueta.', 0, 1)
        pdf.ln(10)
    
    # --- Detailed Stats Table ---
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Estadísticas por Usuario', 0, 1)
    
    # Table Header
    pdf.set_fill_color(243, 244, 246)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(80, 10, 'Usuario', 1, 0, 'L', True)
    pdf.cell(35, 10, 'Completadas', 1, 0, 'C', True)
    pdf.cell(35, 10, 'Pendientes', 1, 0, 'C', True)
    pdf.cell(40, 10, 'Total', 1, 1, 'C', True)
    
    # Table Body
    pdf.set_font('Arial', '', 10)
    for stat in data['user_stats']:
        pdf.cell(80, 10, stat['name'], 1, 0, 'L')
        pdf.cell(35, 10, str(stat['completed']), 1, 0, 'C')
        pdf.cell(35, 10, str(stat['pending']), 1, 0, 'C')
        pdf.cell(40, 10, str(stat['completed'] + stat['pending']), 1, 1, 'C')
        
    pdf.ln(10)
    
    # --- Detailed Task List (Reusing layout from generate_task_pdf) ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Detalle de Tareas', 0, 1)
    
    # Table Header
    pdf.set_fill_color(0, 119, 190) # Bright Blue
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 8)
    
    # Column widths (Total: 190)
    w_title = 35
    w_creator = 22
    w_assigned = 22
    w_status = 18
    w_priority = 18
    w_time = 15
    w_date = 25
    w_completed = 35
    
    pdf.cell(w_title, 10, 'Título', 0, 0, 'L', True)
    pdf.cell(w_creator, 10, 'Creado por', 0, 0, 'L', True)
    pdf.cell(w_assigned, 10, 'Asignado a', 0, 0, 'L', True)
    pdf.cell(w_status, 10, 'Estado', 0, 0, 'C', True)
    pdf.cell(w_priority, 10, 'Prioridad', 0, 0, 'C', True)
    pdf.cell(w_time, 10, 'Tiempo', 0, 0, 'C', True)
    pdf.cell(w_date, 10, 'Vencimiento', 0, 0, 'C', True)
    pdf.cell(w_completed, 10, 'Completado por', 0, 1, 'C', True)
    
    # Table Content
    pdf.set_font('Arial', '', 8)
    pdf.set_text_color(0, 0, 0)
    
    fill = False
    for task in data['tasks']:
        # Zebra striping
        if fill:
            pdf.set_fill_color(243, 244, 246)
        else:
            pdf.set_fill_color(255, 255, 255)
            
        # Truncate title
        title = task.title[:25] + '...' if len(task.title) > 25 else task.title
        
        # Creator
        creator = task.creator.full_name[:15] + '..' if len(task.creator.full_name) > 15 else task.creator.full_name

        # Assignees
        assignees_list = [u.full_name.split()[0] for u in task.assignees]
        assignees_str = ", ".join(assignees_list)
        assignees_str = assignees_str[:15] + '..' if len(assignees_str) > 15 else assignees_str
        
        # Status
        status_text = "Completada" if task.status == 'Completed' else "Pendiente"
        
        # Completed by
        if task.completed_by:
            completed_info = f"{task.completed_by.full_name}\n{task.completed_at.strftime('%d/%m/%Y')}"
        else:
            completed_info = "-"
        
        # Save current Y position
        y_start = pdf.get_y()
        x_start = pdf.get_x()
        
        # Check page break
        if y_start > 270:
            pdf.add_page()
            y_start = pdf.get_y()
            # Re-print header? Optional, but good for readability. Skipping for brevity.
        
        # Draw cells
        pdf.cell(w_title, 10, title, 0, 0, 'L', fill)
        pdf.cell(w_creator, 10, creator, 0, 0, 'L', fill)
        pdf.cell(w_assigned, 10, assignees_str, 0, 0, 'L', fill)
        
        # Status Color
        if task.status == 'Completed':
            pdf.set_text_color(4, 120, 87)
        else:
            pdf.set_text_color(193, 39, 45)
            
        pdf.cell(w_status, 10, status_text, 0, 0, 'C', fill)
        
        # Reset color
        pdf.set_text_color(0, 0, 0)
        
        pdf.cell(w_priority, 10, task.priority, 0, 0, 'C', fill)
        
        # Time spent formatted
        if task.time_spent and task.time_spent > 0:
            if task.time_spent >= 60:
                time_str = f"{round(task.time_spent / 60, 1)}h"
            else:
                time_str = f"{task.time_spent}m"
        else:
            time_str = "-"
        pdf.cell(w_time, 10, time_str, 0, 0, 'C', fill)
        
        pdf.cell(w_date, 10, task.due_date.strftime('%d/%m/%Y'), 0, 0, 'C', fill)
        
        # Completed by (Multi-cell)
        x_current = pdf.get_x()
        
        pdf.set_font('Arial', '', 7)
        pdf.multi_cell(w_completed, 5, completed_info, 0, 'C', fill)
        pdf.set_font('Arial', '', 8)
        
        # Move to next line
        pdf.set_xy(x_start, y_start + 10)
        
        fill = not fill

    return pdf

def generate_task_pdf(tasks, filters):
    pdf = PDFReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- Summary Section ---
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == 'Completed')
    pending_tasks = total_tasks - completed_tasks
    
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 10, 'Resumen Ejecutivo', 0, 1)
    
    # Summary Cards (simulated with cells)
    pdf.set_font('Arial', '', 10)
    
    # Draw 3 boxes
    y_start = pdf.get_y()
    
    # Box 1: Total
    pdf.set_fill_color(243, 244, 246) # Gray 100
    pdf.rect(10, y_start, 60, 25, 'F')
    pdf.set_xy(10, y_start + 5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(60, 6, str(total_tasks), 0, 2, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.cell(60, 6, 'Total Tareas', 0, 0, 'C')
    
    # Box 2: Pending
    pdf.set_fill_color(254, 243, 199) # Amber 100
    pdf.rect(75, y_start, 60, 25, 'F')
    pdf.set_xy(75, y_start + 5)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(180, 83, 9) # Amber 700
    pdf.cell(60, 6, str(pending_tasks), 0, 2, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.cell(60, 6, 'Pendientes', 0, 0, 'C')
    
    # Box 3: Completed
    pdf.set_fill_color(209, 250, 229) # Emerald 100
    pdf.rect(140, y_start, 60, 25, 'F')
    pdf.set_xy(140, y_start + 5)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(4, 120, 87) # Emerald 700
    pdf.cell(60, 6, str(completed_tasks), 0, 2, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.cell(60, 6, 'Completadas', 0, 0, 'C')
    
    pdf.set_text_color(0, 0, 0) # Reset color
    pdf.set_y(y_start + 35)

    # --- Filters Info ---
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'Filtros Aplicados:', 0, 1)
    pdf.set_font('Arial', '', 10)
    
    filter_text = []
    if filters.get('creator'):
        filter_text.append(f"Usuario: {filters['creator_name']}")
    if filters.get('status'):
        status_trans = "Completada" if filters['status'] == 'Completed' else "Pendiente"
        filter_text.append(f"Estado: {status_trans}")
    if filters.get('date_range'):
        filter_text.append(f"Fecha: {filters['date_range']}")
    if filters.get('tag'):
        filter_text.append(f"Etiqueta: {filters['tag']}")
        
    if not filter_text:
        pdf.cell(0, 6, "Ninguno (Mostrando todas las tareas)", 0, 1)
    else:
        for ft in filter_text:
            pdf.cell(0, 6, f"- {ft}", 0, 1)
            
    pdf.ln(5)
    
    # --- Table Header ---
    pdf.set_fill_color(0, 119, 190) # Bright Blue - Brand Color
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 8)
    
    # Column widths (Total: 190)
    w_title = 40
    w_creator = 25
    w_assigned = 25
    w_status = 20
    w_priority = 20
    w_date = 25
    w_completed = 35
    
    pdf.cell(w_title, 10, 'Título', 0, 0, 'L', True)
    pdf.cell(w_creator, 10, 'Creado por', 0, 0, 'L', True)
    pdf.cell(w_assigned, 10, 'Asignado a', 0, 0, 'L', True)
    pdf.cell(w_status, 10, 'Estado', 0, 0, 'C', True)
    pdf.cell(w_priority, 10, 'Prioridad', 0, 0, 'C', True)
    pdf.cell(w_date, 10, 'Vencimiento', 0, 0, 'C', True)
    pdf.cell(w_completed, 10, 'Completado por', 0, 1, 'C', True)
    
    # --- Table Content ---
    pdf.set_font('Arial', '', 8)
    pdf.set_text_color(0, 0, 0)
    
    fill = False
    for task in tasks:
        # Zebra striping
        if fill:
            pdf.set_fill_color(243, 244, 246) # Gray 100
        else:
            pdf.set_fill_color(255, 255, 255)
            
        # Truncate title if needed
        title = task.title[:25] + '...' if len(task.title) > 25 else task.title
        
        # Creator name truncated
        creator = task.creator.full_name[:15] + '..' if len(task.creator.full_name) > 15 else task.creator.full_name

        # Assignees
        assignees_list = [u.full_name.split()[0] for u in task.assignees] # First names only to save space
        assignees_str = ", ".join(assignees_list)
        assignees_str = assignees_str[:15] + '..' if len(assignees_str) > 15 else assignees_str
        
        # Status Translation & Color
        status_text = "Completada" if task.status == 'Completed' else "Pendiente"
        
        # Completed by info
        if task.completed_by:
            completed_info = f"{task.completed_by.full_name}\n{task.completed_at.strftime('%d/%m/%Y')}"
        else:
            completed_info = "-"
        
        # Save current Y position
        y_start = pdf.get_y()
        x_start = pdf.get_x()
        
        # Draw cells
        pdf.cell(w_title, 10, title, 0, 0, 'L', fill)
        pdf.cell(w_creator, 10, creator, 0, 0, 'L', fill)
        pdf.cell(w_assigned, 10, assignees_str, 0, 0, 'L', fill)
        
        # Status Color
        if task.status == 'Completed':
            pdf.set_text_color(4, 120, 87) # Green
        else:
            pdf.set_text_color(193, 39, 45) # Vivid Red - Brand Color
            
        pdf.cell(w_status, 10, status_text, 0, 0, 'C', fill)
        
        # Reset color
        pdf.set_text_color(0, 0, 0)
        
        pdf.cell(w_priority, 10, task.priority, 0, 0, 'C', fill)
        pdf.cell(w_date, 10, task.due_date.strftime('%d/%m/%Y'), 0, 0, 'C', fill)
        
        # Completed by (Multi-cell needs special handling to not break flow)
        # We use x,y positioning
        x_current = pdf.get_x()
        y_current = pdf.get_y()
        
        pdf.set_font('Arial', '', 7)
        pdf.multi_cell(w_completed, 5, completed_info, 0, 'C', fill)
        pdf.set_font('Arial', '', 8)
        
        # Move to next line based on max height (which is 10)
        pdf.set_xy(x_start, y_start + 10)
        
        fill = not fill
        
    return pdf
