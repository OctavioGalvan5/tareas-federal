import sys, os
from datetime import datetime, timedelta
sys.path.append(os.getcwd())
from app import app, db
from models import User, Task

def get_week_of_month(dt):
    first_day = dt.replace(day=1)
    adjusted_dom = dt.day + first_day.weekday()
    return int(max(0, (adjusted_dom - 1) / 7)) + 1

with app.app_context():
    rojas = User.query.filter(User.full_name.ilike('%rojas%')).first()
    if not rojas:
        print('User Jose Rojas not found.')
        sys.exit(0)
    
    # We will filter by created_at or due_date? Usually it means due_date or completed_at in that period
    # Let's get all tasks assigned to him that were either due in that period or created in that period or completed in that period
    start_date = datetime(2026, 2, 13)
    end_date = datetime(2026, 2, 27, 23, 59, 59)
    
    # Let's just get all tasks where he is assignee, then filter.
    tasks = [t for t in Task.query.all() if rojas in t.assignees]
    
    # Filter tasks relevant to the period (created, due, or completed within)
    # Actually, "from 13 feb to 27 feb" usually refers to tasks due or completed in that date. I'll use due_date and completed_at.
    # Let's just grab tasks that either have due_date in period, or completed_at in period, or created_at in period.
    period_tasks = []
    for t in tasks:
        in_period = False
        if t.due_date and start_date <= t.due_date <= end_date:
            in_period = True
        elif t.completed_at and start_date <= t.completed_at <= end_date:
            in_period = True
        elif t.created_at and start_date <= t.created_at <= end_date:
            in_period = True
            
        if in_period:
            period_tasks.append(t)
            
    print(f"### Reporte de José Rojas (13 de Febrero al 27 de Febrero)")
    print(f"**Total Tareas Asignadas en el periodo:** {len(period_tasks)}")
    
    completed = [t for t in period_tasks if t.status == 'Completed']
    pending = [t for t in period_tasks if t.status != 'Completed' and t.status != 'Anulado']
    
    print(f"**Tareas Realizadas:** {len(completed)}")
    print(f"**Tareas Pendientes:** {len(pending)}")
    print("")
    print("### Desglose por Día (Tareas Realizadas)")
    
    # Group completed by day
    by_day = {}
    for d in range(15):
        day = start_date + timedelta(days=d)
        by_day[day.strftime('%Y-%m-%d')] = 0
        
    for t in completed:
        if t.completed_at and start_date <= t.completed_at <= end_date:
            d_str = t.completed_at.strftime('%Y-%m-%d')
            if d_str in by_day:
                by_day[d_str] += 1
            else:
                by_day[d_str] = 1
                
    for d_str, count in sorted(by_day.items()):
        print(f"- {d_str}: {count} tarea(s)")
        
    print("")
    print("### Desglose por Semanas (Tareas Realizadas)")
    by_week = {'Semana 3 de Febrero (13-15)': 0, 'Semana 4 de Febrero (16-22)': 0, 'Semana 5 de Febrero (23-27)': 0}
    for t in completed:
        if t.completed_at and start_date <= t.completed_at <= end_date:
            day = t.completed_at.day
            if 13 <= day <= 15:
                by_week['Semana 3 de Febrero (13-15)'] += 1
            elif 16 <= day <= 22:
                by_week['Semana 4 de Febrero (16-22)'] += 1
            elif 23 <= day <= 27:
                by_week['Semana 5 de Febrero (23-27)'] += 1
                
    for w_str, count in by_week.items():
        print(f"- {w_str}: {count} tarea(s)")

