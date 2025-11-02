import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "afyamama.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Mothers table
    cur.execute("""CREATE TABLE IF NOT EXISTS mothers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mother_id TEXT UNIQUE,
        name TEXT,
        age INTEGER,
        phone TEXT,
        location TEXT,
        gestational_age_weeks INTEGER,
        parity INTEGER,
        bp_systolic INTEGER,
        bp_diastolic INTEGER,
        hb REAL,
        bmi REAL,
        notes TEXT,
        status TEXT,
        created_at TEXT
    )""")

    # Children table
    cur.execute("""CREATE TABLE IF NOT EXISTS children (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mother_id TEXT,
        child_name TEXT,
        dob TEXT,
        birth_weight REAL,
        delivery_type TEXT,
        notes TEXT,
        created_at TEXT
    )""")

    # Chat logs
    cur.execute("""CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mother_id TEXT,
        user_input TEXT,
        assistant_response TEXT,
        created_at TEXT
    )""")

    # Followups
    cur.execute("""CREATE TABLE IF NOT EXISTS followups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mother_id TEXT,
        due_date TEXT,
        done INTEGER DEFAULT 0,
        notes TEXT,
        created_at TEXT
    )""")

    # ✅ ANC Visits table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS anc_visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mother_id TEXT,
        visit_date TEXT,
        bp_systolic INTEGER,
        bp_diastolic INTEGER,
        hb REAL,
        weight REAL,
        notes TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

# ------------------ Mother CRUD ------------------ #

def add_mother(data: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""INSERT OR IGNORE INTO mothers
    (mother_id, name, age, phone, location, gestational_age_weeks, parity, bp_systolic, bp_diastolic, hb, bmi, notes, status, created_at)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data.get('mother_id'),
        data.get('name'),
        data.get('age'),
        data.get('phone'),
        data.get('location'),
        data.get('gestational_age_weeks'),
        data.get('parity'),
        data.get('bp_systolic'),
        data.get('bp_diastolic'),
        data.get('hb'),
        data.get('bmi'),
        data.get('notes'),
        data.get('status','active'),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

def edit_mother(mother_id, data: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE mothers SET
        name=?, age=?, phone=?, location=?, gestational_age_weeks=?, parity=?,
        bp_systolic=?, bp_diastolic=?, hb=?, bmi=?, notes=?, status=?
        WHERE mother_id=?
    """, (
        data.get('name'),
        data.get('age'),
        data.get('phone'),
        data.get('location'),
        data.get('gestational_age_weeks'),
        data.get('parity'),
        data.get('bp_systolic'),
        data.get('bp_diastolic'),
        data.get('hb'),
        data.get('bmi'),
        data.get('notes'),
        data.get('status', 'active'),
        mother_id
    ))
    conn.commit()
    conn.close()

def delete_mother(mother_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM mothers WHERE mother_id=?", (mother_id,))
    conn.commit()
    conn.close()

def get_mothers():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM mothers ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_mother_by_id(mother_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM mothers WHERE mother_id = ?", (mother_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

# ------------------ Children ------------------ #

def add_child(data: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""INSERT INTO children
    (mother_id, child_name, dob, birth_weight, delivery_type, notes, created_at)
    VALUES (?,?,?,?,?,?,?)
    """, (
        data.get('mother_id'),
        data.get('child_name'),
        data.get('dob'),
        data.get('birth_weight'),
        data.get('delivery_type'),
        data.get('notes'),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

# ------------------ Chat Logs ------------------ #

def add_chat_log(mother_id, user_input, assistant_response):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO chat_logs (mother_id, user_input, assistant_response, created_at) VALUES (?,?,?,?)",
                (mother_id, user_input, assistant_response, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

# ------------------ Follow-ups ------------------ #

def add_followup(mother_id, due_date, notes=''):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO followups (mother_id, due_date, notes, created_at) VALUES (?,?,?,?)",
                (mother_id, due_date, notes, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

# ------------------ ANC Visits ------------------ #

def add_anc_visit(data: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO anc_visits
        (mother_id, visit_date, bp_systolic, bp_diastolic, hb, weight, notes, created_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        data.get('mother_id'),
        data.get('visit_date'),
        data.get('bp_systolic'),
        data.get('bp_diastolic'),
        data.get('hb'),
        data.get('weight'),
        data.get('notes'),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

def get_anc_visits(mother_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM anc_visits WHERE mother_id=? ORDER BY visit_date DESC", (mother_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
