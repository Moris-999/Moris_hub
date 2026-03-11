import sys
import sqlite3
import bcrypt
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QMessageBox, QSpinBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from collections import Counter

DB_FILE = "database.db"

# ---------------- DATABASE ----------------
def connect():
    return sqlite3.connect(DB_FILE)

def initialize():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password BLOB
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medications(
        id INTEGER PRIMARY KEY,
        name TEXT,
        dose TEXT,
        time TEXT
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seizures(
        id INTEGER PRIMARY KEY,
        date TEXT,
        duration TEXT,
        trigger TEXT,
        notes TEXT
    )""")
    conn.commit()
    conn.close()

# ---------------- AUTH ----------------
def register_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users(username,password) VALUES (?,?)",
            (username, hashed)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username, password):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password FROM users WHERE username=?",
        (username,)
    )
    result = cursor.fetchone()
    conn.close()
    if result:
        return bcrypt.checkpw(password.encode(), result[0])
    return False

# ---------------- ML MODEL ----------------
try:
    data = pd.read_csv("seizure_data.csv")
    X = data.drop("seizure", axis=1)
    y = data["seizure"]
    model = RandomForestClassifier()
    model.fit(X, y)
except:
    model = None

def predict_seizure(features):
    if model is None:
        return "Model unavailable"
    df = pd.DataFrame([features])
    pred = model.predict(df)
    return "High Risk" if pred[0] == 1 else "Low Risk"

# ---------------- ANALYTICS CHART ----------------
class ChartCanvas(FigureCanvas):
    def __init__(self):
        self.figure = Figure(figsize=(5,4))
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)
    
    def seizure_frequency(self, dates):
        self.ax.clear()
        months = {}
        for d in dates:
            month = d[:7]
            months[month] = months.get(month,0)+1
        self.ax.bar(months.keys(), months.values(), color="red")
        self.ax.set_title("Seizures Per Month")
        self.draw()

    def trigger_chart(self, triggers):
        self.ax.clear()
        counts = Counter(triggers)
        self.ax.bar(counts.keys(), counts.values(), color="orange")
        self.ax.set_title("Trigger Frequency")
        self.draw()

    def trigger_pie_chart(self, triggers):
        self.ax.clear()
        counts = Counter(triggers)
        labels = counts.keys()
        sizes = counts.values()
        self.ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=plt.cm.tab20.colors)
        self.ax.set_title("Trigger Distribution")
        self.draw()

# ---------------- LOGIN WINDOW ----------------
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧠 Epilepsy Manager")
        self.setFixedSize(400,300)
        self.setStyleSheet("background-color:#f0f2f5;")
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("🧠 Epilepsy Manager")
        title.setFont(QFont("Arial",20,QFont.Bold))
        title.setAlignment(Qt.AlignCenter)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.username.setStyleSheet("padding:8px;border-radius:8px;border:1px solid #ccc;background:#fff;")
        
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setStyleSheet("padding:8px;border-radius:8px;border:1px solid #ccc;background:#fff;")

        login_btn = QPushButton("Login")
        login_btn.setStyleSheet("background-color:#007AFF;color:white;border-radius:10px;height:35px;")
        login_btn.clicked.connect(self.login)
        
        register_btn = QPushButton("Register")
        register_btn.setStyleSheet("background-color:#34C759;color:white;border-radius:10px;height:35px;")
        register_btn.clicked.connect(self.register)

        layout.addWidget(title)
        layout.addSpacing(15)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addSpacing(15)
        layout.addWidget(login_btn)
        layout.addWidget(register_btn)
        self.setLayout(layout)
    
    def login(self):
        if authenticate_user(self.username.text(), self.password.text()):
            self.dashboard = Dashboard(self.username.text())
            self.dashboard.show()
            self.close()
        else:
            QMessageBox.warning(self,"Error","Invalid credentials")
    
    def register(self):
        if register_user(self.username.text(), self.password.text()):
            QMessageBox.information(self,"Success","User registered!")
        else:
            QMessageBox.warning(self,"Error","Username exists")

# ---------------- DASHBOARD ----------------
class Dashboard(QWidget):
    def __init__(self, username):
        super().__init__()
        self.setWindowTitle("🧠 Dashboard")
        self.resize(950,650)
        self.setStyleSheet("background-color:#ffffff;")
        self.username = username

        main_layout = QVBoxLayout()
        title = QLabel(f"Hello, {self.username} 👋")
        title.setFont(QFont("Arial",16,QFont.Bold))
        main_layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.med_tab(),"Medications")
        self.tabs.addTab(self.seizure_tab(),"Seizures")
        self.tabs.addTab(self.ml_tab(),"ML Predictor")
        self.tabs.addTab(self.analytics_tab(),"Analytics")
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    # -------- MEDICATION TAB --------
    def med_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        self.med_table = QTableWidget()
        self.med_table.setColumnCount(4)
        self.med_table.setHorizontalHeaderLabels(["ID","Name","Dose","Time"])
        layout.addWidget(self.med_table)

        form = QHBoxLayout()
        self.med_name = QLineEdit(); self.med_name.setPlaceholderText("Name")
        self.med_dose = QLineEdit(); self.med_dose.setPlaceholderText("Dose")
        self.med_time = QLineEdit(); self.med_time.setPlaceholderText("Time")
        add_btn = QPushButton("Add"); add_btn.setStyleSheet("background-color:#34C759;color:white;border-radius:10px;"); add_btn.clicked.connect(self.add_med)
        form.addWidget(self.med_name); form.addWidget(self.med_dose); form.addWidget(self.med_time); form.addWidget(add_btn)
        layout.addLayout(form)
        tab.setLayout(layout)
        self.load_meds()
        return tab

    def load_meds(self):
        conn = connect(); cursor = conn.cursor()
        cursor.execute("SELECT * FROM medications"); rows = cursor.fetchall(); conn.close()
        self.med_table.setRowCount(0)
        for row_data in rows:
            row = self.med_table.rowCount(); self.med_table.insertRow(row)
            for col, data in enumerate(row_data):
                self.med_table.setItem(row,col,QTableWidgetItem(str(data)))

    def add_med(self):
        conn = connect(); cursor = conn.cursor()
        cursor.execute("INSERT INTO medications(name,dose,time) VALUES (?,?,?)",(self.med_name.text(),self.med_dose.text(),self.med_time.text()))
        conn.commit(); conn.close()
        self.load_meds()

    # -------- SEIZURE TAB --------
    def seizure_tab(self):
        tab = QWidget(); layout = QVBoxLayout()
        self.seizure_table = QTableWidget(); self.seizure_table.setColumnCount(5); self.seizure_table.setHorizontalHeaderLabels(["ID","Date","Duration","Trigger","Notes"])
        layout.addWidget(self.seizure_table)

        form = QHBoxLayout()
        self.date = QLineEdit(); self.date.setPlaceholderText("Date")
        self.duration = QLineEdit(); self.duration.setPlaceholderText("Duration")
        self.trigger = QLineEdit(); self.trigger.setPlaceholderText("Trigger")
        self.notes = QLineEdit(); self.notes.setPlaceholderText("Notes")
        add_btn = QPushButton("Add"); add_btn.setStyleSheet("background-color:#FF9500;color:white;border-radius:10px;"); add_btn.clicked.connect(self.add_seizure)
        form.addWidget(self.date); form.addWidget(self.duration); form.addWidget(self.trigger); form.addWidget(self.notes); form.addWidget(add_btn)
        layout.addLayout(form)
        tab.setLayout(layout)
        self.load_seizures()
        return tab

    def load_seizures(self):
        conn = connect(); cursor = conn.cursor()
        cursor.execute("SELECT * FROM seizures"); rows = cursor.fetchall(); conn.close()
        self.seizure_table.setRowCount(0)
        for row_data in rows:
            row = self.seizure_table.rowCount(); self.seizure_table.insertRow(row)
            for col,data in enumerate(row_data):
                self.seizure_table.setItem(row,col,QTableWidgetItem(str(data)))

    def add_seizure(self):
        conn = connect(); cursor = conn.cursor()
        cursor.execute("INSERT INTO seizures(date,duration,trigger,notes) VALUES (?,?,?,?)",(self.date.text(),self.duration.text(),self.trigger.text(),self.notes.text()))
        conn.commit(); conn.close()
        self.load_seizures(); self.load_analytics()

    # -------- ML PREDICTOR TAB --------
    def ml_tab(self):
        tab = QWidget(); layout = QVBoxLayout()
        self.age = QSpinBox(); self.age.setRange(0,120); self.age.setPrefix("Age: ")
        self.sleep = QSpinBox(); self.sleep.setRange(0,24); self.sleep.setPrefix("Sleep Hours: ")
        self.stress = QSpinBox(); self.stress.setRange(0,10); self.stress.setPrefix("Stress Level: ")
        self.result = QLabel("Prediction: N/A"); self.result.setFont(QFont("Arial",14,QFont.Bold))
        btn = QPushButton("Predict"); btn.setStyleSheet("background-color:#007AFF;color:white;border-radius:10px;"); btn.clicked.connect(self.predict)
        layout.addWidget(self.age); layout.addWidget(self.sleep); layout.addWidget(self.stress); layout.addWidget(btn); layout.addWidget(self.result)
        tab.setLayout(layout); return tab

    def predict(self):
        features = {"age":self.age.value(),"sleep_hours":self.sleep.value(),"stress_level":self.stress.value()}
        result = predict_seizure(features)
        self.result.setText(f"Prediction: {result}")

    # -------- ANALYTICS TAB --------
    def analytics_tab(self):
        tab = QWidget(); layout = QVBoxLayout()
        self.chart1 = ChartCanvas(); self.chart2 = ChartCanvas(); self.chart3 = ChartCanvas()
        layout.addWidget(QLabel("Seizure Frequency")); layout.addWidget(self.chart1)
        layout.addWidget(QLabel("Trigger Frequency")); layout.addWidget(self.chart2)
        layout.addWidget(QLabel("Trigger Distribution (Pie Chart)")); layout.addWidget(self.chart3)
        tab.setLayout(layout)
        self.load_analytics(); return tab

    def load_analytics(self):
        conn = connect(); cursor = conn.cursor()
        cursor.execute("SELECT date,trigger FROM seizures"); data = cursor.fetchall(); conn.close()
        if not data: return
        dates = [d[0] for d in data]; triggers = [d[1] for d in data if d[1]]
        self.chart1.seizure_frequency(dates); self.chart2.trigger_chart(triggers); self.chart3.trigger_pie_chart(triggers)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    initialize()
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())