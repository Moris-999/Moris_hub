from reportlab.pdfgen import canvas
from database import connect

def generate_report():

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM seizures")
    seizures = cursor.fetchall()

    pdf = canvas.Canvas("neurologist_report.pdf")

    pdf.drawString(200, 800, "Epilepsy Patient Report")

    y = 760

    for s in seizures:

        line = f"Date: {s[1]} Duration: {s[2]} Trigger: {s[3]}"
        pdf.drawString(50, y, line)

        y -= 20

    pdf.save()