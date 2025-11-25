from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime

def generate_task_excel(tasks, filters):
    """
    Generate an Excel report for tasks with professional formatting.
    
    Args:
        tasks: List of Task objects to include in the report
        filters: Dictionary of applied filters
        
    Returns:
        Workbook object ready to be saved
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte de Tareas"
    
    # Brand Colors - Caja de Abogados
    brand_blue = "0077BE"  # RGB(0, 119, 190)
    brand_red = "C1272D"   # RGB(193, 39, 45)
    
    # --- Header Section ---
    ws.merge_cells('A1:H1')
    header_cell = ws['A1']
    header_cell.value = "Gestor Federal - Reporte de Tareas"
    header_cell.font = Font(name='Arial', size=18, bold=True, color="FFFFFF")
    header_cell.fill = PatternFill(start_color=brand_blue, end_color=brand_blue, fill_type="solid")
    header_cell.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 30
    
    # --- Date and Time ---
    ws.merge_cells('A2:H2')
    date_cell = ws['A2']
    date_cell.value = f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    date_cell.font = Font(name='Arial', size=10, italic=True)
    date_cell.alignment = Alignment(horizontal='center')
    
    # --- Summary Section ---
    row = 4
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == 'Completed')
    pending_tasks = total_tasks - completed_tasks
    
    ws.merge_cells(f'A{row}:H{row}')
    summary_cell = ws[f'A{row}']
    summary_cell.value = "Resumen Ejecutivo"
    summary_cell.font = Font(name='Arial', size=14, bold=True)
    summary_cell.alignment = Alignment(horizontal='left')
    row += 1
    
    # Summary stats
    summary_data = [
        ('Total de Tareas:', total_tasks),
        ('Pendientes:', pending_tasks),
        ('Completadas:', completed_tasks)
    ]
    
    for label, value in summary_data:
        ws[f'A{row}'] = label
        ws[f'A{row}'].font = Font(name='Arial', size=11, bold=True)
        ws[f'B{row}'] = value
        ws[f'B{row}'].font = Font(name='Arial', size=11)
        row += 1
    
    row += 1
    
    # --- Filters Info ---
    ws.merge_cells(f'A{row}:H{row}')
    filters_cell = ws[f'A{row}']
    filters_cell.value = "Filtros Aplicados:"
    filters_cell.font = Font(name='Arial', size=12, bold=True)
    filters_cell.alignment = Alignment(horizontal='left')
    row += 1
    
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
        ws[f'A{row}'] = "Ninguno (Mostrando todas las tareas)"
        ws[f'A{row}'].font = Font(name='Arial', size=10, italic=True)
        row += 1
    else:
        for ft in filter_text:
            ws[f'A{row}'] = ft
            ws[f'A{row}'].font = Font(name='Arial', size=10)
            row += 1
    
    row += 2
    
    # --- Table Headers ---
    headers = ['Título', 'Descripción', 'Estado', 'Prioridad', 'Vencimiento', 'Creado por', 'Asignados', 'Completado por', 'Fecha Completado']
    header_row = row
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_num)
        cell.value = header
        cell.font = Font(name='Arial', size=11, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=brand_blue, end_color=brand_blue, fill_type="solid")
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
    
    ws.row_dimensions[header_row].height = 30
    row += 1
    
    # --- Table Data ---
    for task in tasks:
        # Assignees
        assignees_list = ', '.join([a.full_name for a in task.assignees])
        
        # Completed by
        completed_by_name = task.completed_by.full_name if task.completed_by else '-'
        
        # Completed at
        completed_at_str = task.completed_at.strftime('%d/%m/%Y %H:%M') if task.completed_at else '-'
        
        # Status translation
        status_text = "Completada" if task.status == 'Completed' else "Pendiente"
        
        row_data = [
            task.title,
            task.description or '-',
            status_text,
            task.priority,
            task.due_date.strftime('%d/%m/%Y'),
            task.creator.full_name,
            assignees_list,
            completed_by_name,
            completed_at_str
        ]
        
        for col_num, value in enumerate(row_data, 1):
            cell = ws.cell(row=row, column=col_num)
            cell.value = value
            cell.font = Font(name='Arial', size=10)
            cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            cell.border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # Special formatting for status
            if col_num == 3:  # Status column
                if task.status == 'Completed':
                    cell.font = Font(name='Arial', size=10, bold=True, color="047857")  # Green
                    cell.fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
                else:
                    cell.font = Font(name='Arial', size=10, bold=True, color=brand_red)
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
            
            # Zebra striping
            elif row % 2 == 0:
                cell.fill = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid")
        
        ws.row_dimensions[row].height = 40
        row += 1
    
    # --- Adjust column widths ---
    column_widths = [30, 40, 15, 12, 15, 25, 20, 18]
    for col_num, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(col_num)].width = width
    
    return wb
