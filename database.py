import sqlite3

def connect():
    return sqlite3.connect("database.db")

def initialize():

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medications(
        id INTEGER PRIMARY KEY,
        name TEXT,
        dose TEXT,
        time TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seizures(
        id INTEGER PRIMARY KEY,
        date TEXT,
        duration TEXT,
        trigger TEXT,
        notes TEXT
    )
    """)

    conn.commit()
    conn.close()