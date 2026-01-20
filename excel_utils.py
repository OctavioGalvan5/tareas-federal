from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
import pytz

# Buenos Aires timezone for displaying dates
BUENOS_AIRES_TZ = pytz.timezone('America/Argentina/Buenos_Aires')

def to_buenos_aires(dt):
    """Convert a datetime to Buenos Aires timezone for display."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(BUENOS_AIRES_TZ)

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
    date_cell.value = f"Generado el {to_buenos_aires(datetime.utcnow()).strftime('%d/%m/%Y %H:%M')}"
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
    headers = ['Título', 'Descripción', 'Estado', 'Prioridad', 'Vencimiento', 'Tiempo', 'Creado por', 'Asignados', 'Completado por', 'Fecha Completado']
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
        completed_at_str = to_buenos_aires(task.completed_at).strftime('%d/%m/%Y %H:%M') if task.completed_at else '-'
        
        # Status translation
        status_text = "Completada" if task.status == 'Completed' else "Pendiente"
        
        # Time spent formatted
        if task.time_spent and task.time_spent > 0:
            if task.time_spent >= 60:
                time_str = f"{round(task.time_spent / 60, 1)} hs"
            else:
                time_str = f"{task.time_spent} min"
        else:
            time_str = '-'
        
        row_data = [
            task.title,
            task.description or '-',
            status_text,
            task.priority,
            to_buenos_aires(task.due_date).strftime('%d/%m/%Y'),
            time_str,
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
    column_widths = [30, 40, 15, 12, 15, 12, 25, 20, 18, 18]
    for col_num, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(col_num)].width = width
    
    return wb


def generate_import_template():
    """
    Generates an empty Excel template for importing tasks.
    Includes headers and comments/instructions.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Plantilla Importación"
    
    # Headers
    headers = [
        'Título (Requerido)', 
        'Descripción', 
        'Prioridad (Normal, Media, Urgente)', 
        'Fecha Inicio (DD/MM/YYYY)',
        'Fecha Vencimiento (Requerido, DD/MM/YYYY)', 
        'Asignados (Usuarios separados por coma)', 
        'Etiquetas (Separadas por coma)',
        'ID Proceso (Opcional)',
        'Estado (Pendiente, En Proceso, Completado)',
        'Completado Por (Usuario, si Estado=Completado)',
        'Fecha Completado (DD/MM/YYYY, si Estado=Completado)'
    ]
    
    # Header Style
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.font = Font(name='Arial', size=11, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="0077BE", end_color="0077BE", fill_type="solid")
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = Border(bottom=Side(style='thin'))
        
        # Set column width
        ws.column_dimensions[get_column_letter(col_num)].width = 25

    # Add example row (optional, maybe as a comment)
    # ws.merge_cells('A2:H2')
    # ws['A2'] = "Ejemplo: Revisar Contrato | Revisar cláusulas | Alta | 20/01/2026 | juan.perez, maria.gomez | Legales, Urgente | 123"
    
    return wb


def process_excel_import(file_stream, current_user):
    """
    Parses an uploaded Excel file and creates tasks.
    
    Returns:
        tuple: (success_count, error_list)
    """
    from openpyxl import load_workbook
    from models import Task, User, Tag, Process
    from extensions import db
    
    try:
        wb = load_workbook(file_stream)
        ws = wb.active
    except Exception as e:
        return 0, [f"Error al leer el archivo Excel: {str(e)}"]
    
    success_count = 0
    errors = []
    
    # Cache users and tags to avoid repeats
    all_users = {u.username.lower(): u for u in User.query.all()}
    # Also map full names just in case
    # Use list() to create a copy of values to avoid Runtime Error when modifying dict
    for u in list(all_users.values()):
        all_users[u.full_name.lower()] = u
        
    all_tags = {t.name.lower(): t for t in Tag.query.all()}
    
    # Iterate rows (skip header)
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        # Unpack row (handle potentially missing columns if user used old template - though we encourage new one)
        # We assume strict adherence to new template for now or robust fetch
        if not row or not any(row):  # Skip empty rows
            continue
            
        try:
            # Safe get by index
            def get_col(idx):
                return row[idx] if idx < len(row) else None
            
            title = get_col(0)
            description = get_col(1)
            priority = get_col(2)
            start_date_raw = get_col(3)
            due_date_raw = get_col(4)
            assignees_raw = get_col(5)
            tags_raw = get_col(6)
            process_id_raw = get_col(7)
            status_raw = get_col(8)
            completed_by_raw = get_col(9)
            completed_at_raw = get_col(10)
            
            # Validation: Title
            if not title:
                errors.append(f"Fila {row_idx}: Falta el Título (Requerido).")
                continue
                
            # Validation: Due Date
            if not due_date_raw:
                errors.append(f"Fila {row_idx}: Falta Fecha Vencimiento (Requerido).")
                continue
            
            # Parse Dates
            due_date = None
            if isinstance(due_date_raw, datetime):
                due_date = due_date_raw
            else:
                try:
                    due_date = datetime.strptime(str(due_date_raw).strip(), '%d/%m/%Y')
                except ValueError:
                    errors.append(f"Fila {row_idx}: Formato de Fecha Vencimiento inválido (use DD/MM/YYYY).")
                    continue

            start_date = None
            if start_date_raw:
                if isinstance(start_date_raw, datetime):
                    start_date = start_date_raw
                else:
                    try:
                        start_date = datetime.strptime(str(start_date_raw).strip(), '%d/%m/%Y')
                    except ValueError:
                        # Optional, so we log error but maybe proceed? No, strict dates usually better
                         errors.append(f"Fila {row_idx}: Formato de Fecha Inicio inválido (use DD/MM/YYYY).")
                         continue
            
            # Priority
            valid_priorities = ['Normal', 'Media', 'Urgente']
            if priority and priority.capitalize() in valid_priorities:
                priority = priority.capitalize()
            else:
                priority = 'Normal'
            
            # Create Task
            new_task = Task(
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
                planned_start_date=start_date,
                creator_id=current_user.id,
                status='Pending', # Default, overridden below
                area_id=current_user.areas[0].id if current_user.areas else None # Default to first area of user
            )
            
            # Process ID
            if process_id_raw:
                try:
                    pid = int(process_id_raw)
                    process = Process.query.get(pid)
                    if process:
                        new_task.process_id = process.id
                        # Inherit area from process if possible
                        new_task.area_id = process.area_id
                    else:
                        errors.append(f"Fila {row_idx}: Proceso ID {pid} no encontrado. Se creó sin proceso.")
                except ValueError:
                    errors.append(f"Fila {row_idx}: ID de Proceso inválido.")
            
            # Assignees
            if assignees_raw:
                names = [n.strip().lower() for n in str(assignees_raw).split(',')]
                for name in names:
                    if name in all_users:
                        new_task.assignees.append(all_users[name])
                    # Silent ignore if not found? Or warning?
            
            # Tags
            if tags_raw:
                tag_names = [t.strip().lower() for t in str(tags_raw).split(',')]
                for t_name in tag_names:
                    if t_name in all_tags:
                        new_task.tags.append(all_tags[t_name])
                    # If tag doesn't exist, we skip it for now (or could create it)
            
            # Status & Completion
            if status_raw:
                status_clean = str(status_raw).strip()
                # Map common variations
                status_map = {
                    'pendiente': 'Pending',
                    'pending': 'Pending',
                    'en proceso': 'In Progress',
                    'in progress': 'In Progress',
                    'completado': 'Completed',
                    'completed': 'Completed',
                    'completada': 'Completed'
                }
                
                final_status = status_map.get(status_clean.lower(), 'Pending')
                new_task.status = final_status
                
                if final_status == 'Completed':
                    # Handle completion details
                    new_task.completed_at = datetime.utcnow() # Default
                    new_task.completed_by_id = current_user.id # Default
                    
                    if completed_at_raw:
                        if isinstance(completed_at_raw, datetime):
                            new_task.completed_at = completed_at_raw
                        else:
                            try:
                                new_task.completed_at = datetime.strptime(str(completed_at_raw).strip(), '%d/%m/%Y')
                            except:
                                pass # Keep default
                    
                    if completed_by_raw:
                        c_name = str(completed_by_raw).strip().lower()
                        if c_name in all_users:
                            new_task.completed_by_id = all_users[c_name].id
            
            db.session.add(new_task)
            success_count += 1
            
        except Exception as e:
            errors.append(f"Fila {row_idx}: Error inesperado - {str(e)}")
            continue
            
    try:
        if success_count > 0:
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        return 0, [f"Error de base de datos al guardar: {str(e)}"]
        
    return success_count, errors
