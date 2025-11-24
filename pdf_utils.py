from fpdf import FPDF
from datetime import datetime

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
        self.cell(0, 10, 'Gestor Federal', 0, 1, 'C')
        
        self.set_font('Arial', '', 12)
        self.cell(0, 10, 'Reporte de Tareas', 0, 1, 'C')
        
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}} - Generado el {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 0, 'C')

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
        
    if not filter_text:
        pdf.cell(0, 6, "Ninguno (Mostrando todas las tareas)", 0, 1)
    else:
        for ft in filter_text:
            pdf.cell(0, 6, f"- {ft}", 0, 1)
            
    pdf.ln(5)
    
    # --- Table Header ---
    pdf.set_fill_color(0, 119, 190) # Bright Blue - Brand Color
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 10)
    
    # Column widths
    w_title = 80
    w_status = 30
    w_priority = 30
    w_date = 50
    
    pdf.cell(w_title, 10, 'Título', 0, 0, 'L', True)
    pdf.cell(w_status, 10, 'Estado', 0, 0, 'C', True)
    pdf.cell(w_priority, 10, 'Prioridad', 0, 0, 'C', True)
    pdf.cell(w_date, 10, 'Vencimiento', 0, 1, 'C', True)
    
    # --- Table Content ---
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(0, 0, 0)
    
    fill = False
    for task in tasks:
        # Zebra striping
        if fill:
            pdf.set_fill_color(243, 244, 246) # Gray 100
        else:
            pdf.set_fill_color(255, 255, 255)
            
        # Truncate title if needed
        title = task.title[:45] + '...' if len(task.title) > 45 else task.title
        
        # Status Translation & Color
        status_text = "Completada" if task.status == 'Completed' else "Pendiente"
        
        # Save Y position to handle heights if we wanted multi-cell, 
        # but for now single cell is safer for alignment
        
        pdf.cell(w_title, 10, title, 0, 0, 'L', fill)
        
        # Status Color
        if task.status == 'Completed':
            pdf.set_text_color(4, 120, 87) # Green
        else:
            pdf.set_text_color(193, 39, 45) # Vivid Red - Brand Color
            
        pdf.cell(w_status, 10, status_text, 0, 0, 'C', fill)
        
        # Reset color
        pdf.set_text_color(0, 0, 0)
        
        pdf.cell(w_priority, 10, task.priority, 0, 0, 'C', fill)
        pdf.cell(w_date, 10, task.due_date.strftime('%d/%m/%Y'), 0, 1, 'C', fill)
        
        fill = not fill
        
    return pdf
