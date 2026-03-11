import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import sqlite3
import bcrypt
import pandas as pd
from datetime import datetime
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from sklearn.ensemble import RandomForestClassifier

DB_FILE = "epilepsy.db"

# -------------------- DATABASE --------------------
def connect():
    return sqlite3.connect(DB_FILE)

def initialize_db():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users(
                        id INTEGER PRIMARY KEY,
                        username TEXT UNIQUE,
                        password TEXT
                    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS medications(
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER,
                        name TEXT,
                        dose TEXT,
                        time TEXT
                    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS seizures(
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER,
                        date TEXT,
                        duration TEXT,
                        trigger TEXT,
                        notes TEXT
                    )""")
    conn.commit()
    conn.close()

# -------------------- AUTH --------------------
def register_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users(username,password) VALUES (?,?)",(username,hashed))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username, password):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id,password FROM users WHERE username=?",(username,))
    result = cursor.fetchone()
    conn.close()
    if result:
        user_id, hashed = result
        if bcrypt.checkpw(password.encode(), hashed):
            return user_id
    return None

# -------------------- ML MODEL --------------------
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
    return "High Risk" if pred[0]==1 else "Low Risk"

# -------------------- MEDICATION REMINDERS --------------------
def reminder_loop(user_id, stop_event):
    conn = connect()
    cursor = conn.cursor()
    while not stop_event.is_set():
        now = datetime.now().strftime("%H:%M")
        cursor.execute("SELECT name,time FROM medications WHERE user_id=?",(user_id,))
        meds = cursor.fetchall()
        for name, med_time in meds:
            if med_time == now:
                messagebox.showinfo("💊 Medication Reminder", f"Time to take: {name}")
        stop_event.wait(60)
    conn.close()

# -------------------- LOGIN WINDOW --------------------
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🧠 Epilepsy Manager")
        self.geometry("350x300")
        self.configure(bg="#dff6ff")

        tk.Label(self, text="🔐 Login or Register", font=("Arial",16,"bold"), bg="#dff6ff").pack(pady=10)
        tk.Label(self, text="Username", bg="#dff6ff").pack()
        self.username_entry = tk.Entry(self)
        self.username_entry.pack(pady=5)
        tk.Label(self, text="Password", bg="#dff6ff").pack()
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack(pady=5)

        tk.Button(self,text="Login",command=self.login,bg="#1d3557",fg="white",width=15).pack(pady=5)
        tk.Button(self,text="Register",command=self.register,bg="#1d3557",fg="white",width=15).pack(pady=5)

        self.error_label = tk.Label(self, text="", fg="red", bg="#dff6ff")
        self.error_label.pack(pady=5)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        user_id = authenticate_user(username,password)
        if user_id:
            self.destroy()
            Dashboard(user_id, username)
        else:
            self.error_label.config(text="❌ Invalid username or password")

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if username=="" or password=="":
            self.error_label.config(text="❌ Fill all fields")
            return
        if register_user(username,password):
            self.error_label.config(text="✅ Registered successfully!")
        else:
            self.error_label.config(text="❌ Username exists")

# -------------------- DASHBOARD --------------------
class Dashboard(tk.Tk):
    def __init__(self,user_id,username):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.title(f"🧠 Epilepsy Dashboard - {username}")
        self.geometry("900x600")
        self.configure(bg="white")

        # Start medication reminder thread
        self.stop_event = threading.Event()
        self.reminder_thread = threading.Thread(target=reminder_loop,args=(self.user_id,self.stop_event),daemon=True)
        self.reminder_thread.start()

        # Top bar
        top_frame = tk.Frame(self,bg="white")
        top_frame.pack(fill="x",pady=10)
        tk.Label(top_frame,text=f"Hello, {self.username} 👋",font=("Arial",16,"bold"),bg="white").pack(side="left", padx=10)
        tk.Button(top_frame,text="Logout",command=self.logout,bg="#FF3B30",fg="white").pack(side="right", padx=10)

        # Tabs
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(expand=1, fill="both")

        self.med_tab_frame = tk.Frame(self.tabs,bg="white")
        self.seizure_tab_frame = tk.Frame(self.tabs,bg="white")
        self.ml_tab_frame = tk.Frame(self.tabs,bg="white")
        self.trend_tab_frame = tk.Frame(self.tabs,bg="white")

        self.tabs.add(self.med_tab_frame, text="Medications")
        self.tabs.add(self.seizure_tab_frame, text="Seizures")
        self.tabs.add(self.ml_tab_frame, text="ML Predictor")
        self.tabs.add(self.trend_tab_frame, text="Seizure Trends")

        self.build_med_tab()
        self.build_seizure_tab()
        self.build_ml_tab()
        self.build_trend_tab()

        self.mainloop()

    # -------------------- MEDICATIONS --------------------
    def build_med_tab(self):
        self.med_tree = ttk.Treeview(self.med_tab_frame,columns=("Name","Dose","Time"),show="headings")
        for col in ["Name","Dose","Time"]:
            self.med_tree.heading(col,text=col)
        self.med_tree.pack(fill="both",expand=True,pady=10)
        self.load_meds()

        frame = tk.Frame(self.med_tab_frame,bg="white")
        frame.pack(pady=10)
        tk.Label(frame,text="Name:",bg="white").grid(row=0,column=0,padx=5)
        self.med_name = tk.Entry(frame)
        self.med_name.grid(row=0,column=1,padx=5)
        tk.Label(frame,text="Dose:",bg="white").grid(row=0,column=2,padx=5)
        self.med_dose = tk.Entry(frame)
        self.med_dose.grid(row=0,column=3,padx=5)
        tk.Label(frame,text="Time (HH:MM):",bg="white").grid(row=0,column=4,padx=5)
        self.med_time = tk.Entry(frame)
        self.med_time.grid(row=0,column=5,padx=5)
        tk.Button(frame,text="Add Medication",command=self.add_med,bg="#1d3557",fg="white").grid(row=0,column=6,padx=5)

    def load_meds(self):
        for i in self.med_tree.get_children():
            self.med_tree.delete(i)
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id,name,dose,time FROM medications WHERE user_id=?",(self.user_id,))
        rows = cursor.fetchall()
        conn.close()
        for r in rows:
            self.med_tree.insert("",tk.END,values=(r[1],r[2],r[3]),iid=r[0])

    def add_med(self):
        name = self.med_name.get()
        dose = self.med_dose.get()
        time_val = self.med_time.get()
        if not name or not dose or not time_val:
            messagebox.showerror("Error","Fill all fields")
            return
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO medications(user_id,name,dose,time) VALUES (?,?,?,?)",
                       (self.user_id,name,dose,time_val))
        conn.commit()
        conn.close()
        self.load_meds()

    # -------------------- SEIZURES --------------------
    def build_seizure_tab(self):
        self.seizure_tree = ttk.Treeview(self.seizure_tab_frame,columns=("Date","Duration","Trigger","Notes"),show="headings")
        for col in ["Date","Duration","Trigger","Notes"]:
            self.seizure_tree.heading(col,text=col)
        self.seizure_tree.pack(fill="both",expand=True,pady=10)
        self.load_seizures()

        frame = tk.Frame(self.seizure_tab_frame,bg="white")
        frame.pack(pady=10)
        tk.Label(frame,text="Duration:",bg="white").grid(row=0,column=0,padx=5)
        self.seizure_duration = tk.Entry(frame)
        self.seizure_duration.grid(row=0,column=1,padx=5)
        tk.Label(frame,text="Trigger:",bg="white").grid(row=0,column=2,padx=5)
        self.seizure_trigger = tk.Entry(frame)
        self.seizure_trigger.grid(row=0,column=3,padx=5)
        tk.Label(frame,text="Notes:",bg="white").grid(row=0,column=4,padx=5)
        self.seizure_notes = tk.Entry(frame)
        self.seizure_notes.grid(row=0,column=5,padx=5)
        tk.Button(frame,text="Add Seizure",command=self.add_seizure,bg="#1d3557",fg="white").grid(row=0,column=6,padx=5)
        tk.Button(frame,text="Export CSV",command=self.export_seizures,bg="orange",fg="white").grid(row=0,column=7,padx=5)

    def load_seizures(self):
        for i in self.seizure_tree.get_children():
            self.seizure_tree.delete(i)
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id,date,duration,trigger,notes FROM seizures WHERE user_id=?",(self.user_id,))
        rows = cursor.fetchall()
        conn.close()
        for r in rows:
            self.seizure_tree.insert("",tk.END,values=(r[1],r[2],r[3],r[4]),iid=r[0])

    def add_seizure(self):
        duration = self.seizure_duration.get()
        trigger = self.seizure_trigger.get()
        notes = self.seizure_notes.get()
        date_val = datetime.now().strftime("%Y-%m-%d %H:%M")
        if not duration:
            messagebox.showerror("Error","Enter duration")
            return
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO seizures(user_id,date,duration,trigger,notes) VALUES (?,?,?,?,?)",
                       (self.user_id,date_val,duration,trigger,notes))
        conn.commit()
        conn.close()
        self.load_seizures()
        self.update_trend_chart()

    def export_seizures(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if path:
            conn = connect()
            df = pd.read_sql_query(f"SELECT * FROM seizures WHERE user_id={self.user_id}",conn)
            df.to_csv(path,index=False)
            conn.close()
            messagebox.showinfo("Exported","Seizures exported!")

    # -------------------- ML PREDICTOR --------------------
    def build_ml_tab(self):
        frame = tk.Frame(self.ml_tab_frame,bg="white")
        frame.pack(pady=20)
        tk.Label(frame,text="Age:").grid(row=0,column=0,padx=5)
        self.age_entry = tk.Entry(frame)
        self.age_entry.grid(row=0,column=1,padx=5)
        tk.Label(frame,text="Stress Level (1-10):").grid(row=0,column=2,padx=5)
        self.stress_entry = tk.Entry(frame)
        self.stress_entry.grid(row=0,column=3,padx=5)
        tk.Label(frame,text="Sleep Hours:").grid(row=0,column=4,padx=5)
        self.sleep_entry = tk.Entry(frame)
        self.sleep_entry.grid(row=0,column=5,padx=5)
        tk.Button(frame,text="Predict Risk",command=self.predict_risk,bg="#1d3557",fg="white").grid(row=0,column=6,padx=5)
        self.pred_label = tk.Label(frame,text="Prediction: N/A",bg="white",font=("Arial",12,"bold"))
        self.pred_label.grid(row=1,column=0,columnspan=7,pady=10)

    def predict_risk(self):
        try:
            age = float(self.age_entry.get())
            stress = float(self.stress_entry.get())
            sleep = float(self.sleep_entry.get())
            result = predict_seizure({"age":age,"stress_level":stress,"sleep_hours":sleep})
            self.pred_label.config(text=f"Prediction: {result}",fg="red" if result=="High Risk" else "green")
            if result=="High Risk":
                messagebox.showwarning("⚠ High Seizure Risk","Your seizure risk is HIGH today. Take precautions!")
        except:
            messagebox.showerror("Error","Enter valid numbers")

    # -------------------- TREND CHART --------------------
    def build_trend_tab(self):
        self.figure = plt.Figure(figsize=(8,4))
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure,self.trend_tab_frame)
        self.canvas.get_tk_widget().pack(fill="both",expand=True)
        self.update_trend_chart()

    def update_trend_chart(self):
        conn = connect()
        df = pd.read_sql_query(f"SELECT date FROM seizures WHERE user_id={self.user_id}",conn)
        conn.close()
        self.ax.clear()
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            trend = df.groupby(df['date'].dt.date).size()
            self.ax.plot(trend.index, trend.values,marker='o',color='#007AFF')
            self.ax.set_title("Seizure Trend Over Time")
            self.ax.set_xlabel("Date")
            self.ax.set_ylabel("Count")
            self.ax.grid(True)
        self.canvas.draw()

    # -------------------- LOGOUT --------------------
    def logout(self):
        self.stop_event.set()
        self.destroy()
        LoginWindow().mainloop()

# -------------------- MAIN --------------------
if __name__=="__main__":
    initialize_db()
    LoginWindow().mainloop()