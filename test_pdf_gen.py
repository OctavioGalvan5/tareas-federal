from pdf_utils import generate_task_pdf
from datetime import date, datetime

class MockUser:
    def __init__(self, full_name):
        self.full_name = full_name

class MockTask:
    def __init__(self, id, title, description, priority, status, due_date, creator, assignees):
        self.id = id
        self.title = title
        self.description = description
        self.priority = priority
        self.status = status
        self.due_date = due_date
        self.creator = creator
        self.assignees = assignees
        self.created_at = datetime.now()

def test_pdf():
    creator = MockUser("Test Creator")
    assignee = MockUser("Test Assignee")
    
    tasks = [
        MockTask(1, "Task 1", "Desc 1", "Alta", "Pending", datetime.now(), creator, [assignee]),
        MockTask(2, "Task 2", "Desc 2", "Media", "Completed", datetime.now(), creator, [assignee])
    ]
    
    filters = {
        'creator_name': 'Test Creator',
        'status': 'Pending',
        'date_range': 'Hoy'
    }
    
    try:
        pdf = generate_task_pdf(tasks, filters)
        # Try to save directly to file to see if it works
        output_filename = "test_report.pdf"
        pdf.output(output_filename)
        print(f"Successfully created {output_filename}")
        
        # Also test the string output method used in routes.py
        pdf_string = pdf.output(dest='S').encode('latin-1')
        with open("test_report_from_string.pdf", "wb") as f:
            f.write(pdf_string)
        print(f"Successfully created test_report_from_string.pdf")
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf()
