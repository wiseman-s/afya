# frontend/app.py
import streamlit as st
import sys, os
import uuid
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

import db, risk_model

# ✅ Barcode support
try:
    from barcode import Code128
    from barcode.writer import ImageWriter
    BARCODE_ENABLED = True
except Exception:
    BARCODE_ENABLED = False

def generate_barcode(mother_id):
    """Generate barcode PNG file and return file path"""
    if not BARCODE_ENABLED:
        return None
    filename = f"barcode_{mother_id}.png"
    try:
        Code128(mother_id, writer=ImageWriter()).save(filename)
        return filename
    except:
        return None

# ---------------- SETTINGS ----------------
st.set_page_config(page_title="Afyamama Health System", layout="wide")
db.init_db()
DB_PATH = Path(__file__).parent / "afyamama.db"

# ---------- AI assistant logic (improved) ----------
def offline_ai_response(text):
    t = (text or "").lower()
    if any(k in t for k in ["bleed", "bleeding", "vaginal bleeding"]):
        return "Bleeding in pregnancy is an emergency. Advise immediate referral to the nearest health facility."
    if any(k in t for k in ["convuls", "seizure", "fit"]):
        return "Convulsions are a medical emergency (eclampsia). Call emergency services and refer immediately."
    if any(k in t for k in ["headache", "severe headache"]) and any(k in t for k in ["vision", "blurred", "blur"]):
        return "Severe headache with visual changes may indicate preeclampsia. Check BP and refer urgently."
    if "reduced movement" in t or "reduced fetal movement" in t or "no movement" in t:
        return "Reduced fetal movement is concerning. Advise urgent facility review."
    if any(k in t for k in ["vomit", "vomiting", "persistent vomiting"]):
        return "Persistent vomiting risks dehydration and poor nutrition. Encourage oral rehydration and refer if unable to retain fluids."
    if any(k in t for k in ["fever", "high temperature"]):
        return "Fever may indicate infection—advise facility evaluation and appropriate tests/antibiotics if indicated."
    if any(k in t for k in ["swelling", "swollen face", "swollen hands"]):
        return "Swelling (face/hands) with other symptoms may suggest preeclampsia. Check BP and refer as needed."
    if "anemia" in t or "hb" in t:
        return "Anemia: give iron + folate, counsel on iron-rich foods; check Hb and refer if severe."
    if "bp" in t or "pressure" in t or "hypertension" in t:
        return "Monitor BP regularly. If BP >=140/90 or symptoms (headache/vision changes), arrange prompt review for preeclampsia."
    if "nutrition" in t or "lishe" in t:
        return "Advice: balanced diet, iron/folate supplements, protein, fruits & vegetables, hydration. Avoid alcohol and raw foods."
    return ("This is informational. Encourage ANC visits, monitor BP & Hb, teach danger signs "
            "(bleeding, severe headache, visual changes, swelling, reduced fetal movement) and refer to facility for emergencies.")

# ---------- Sidebar navigation ----------
st.sidebar.title("Afyamama Navigation 🩺")
PAGES = [
    "Home", "Dashboard", "Register Mother", "Mother Profiles",
    "Risk Assessment", "Predictive Insights", "ANC Visits",
    "Child Profiles", "Follow-ups", "AI Assistant", "Reports"
]
if "page" not in st.session_state:
    st.session_state.page = "Home"
page = st.sidebar.radio("Select page:", PAGES, index=PAGES.index(st.session_state.page))
st.session_state.page = page

# ---------- Fallback DB helpers ----------
def fetch_followups_from_db(mother_id=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if mother_id:
            cur.execute("SELECT * FROM followups WHERE mother_id=? ORDER BY created_at DESC", (mother_id,))
        else:
            cur.execute("SELECT * FROM followups ORDER BY created_at DESC")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def mark_followup_done_db(followup_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE followups SET done = 1 WHERE id = ?", (followup_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

# -------------- PAGES --------------

# HOME
if page == "Home":
    st.markdown("<h1 style='text-align:center; color:#006400;'>🌸 Afyamama Health System</h1>", unsafe_allow_html=True)
    st.subheader("Welcome | Karibu")
    st.write("""
Afyamama helps CHVs, nurses & mothers manage maternal health, ANC visits, early risk detection, follow-ups, & emergency referral.

🇰🇪 **Kiswahili Maelezo**
Afyamama inasaidia kufuatilia ujauzito, kutambua hatari mapema, na kusaidia rufaa haraka.
""")

# DASHBOARD
elif page == "Dashboard":
    st.header("📊 Dashboard Overview")
    mothers = db.get_mothers()
    st.metric("Registered Mothers", len(mothers))
    risks = {'Low Risk': 0, 'Moderate Risk': 0, 'High Risk': 0, 'Unknown': 0}
    for m in mothers:
        try:
            r = risk_model.predict_risk(m['age'], m['bp_systolic'], m['bp_diastolic'], m['hb'], m['bmi'], m['parity'], m.get('notes',''))
            risks[r['risk']] += 1
        except Exception:
            risks['Unknown'] += 1
    st.bar_chart(pd.DataFrame(list(risks.values()), index=list(risks.keys())))

# REGISTER MOTHER
elif page == "Register Mother":
    st.header("📝 Register a Mother")
    with st.form("register"):
        name = st.text_input("Full name")
        age = st.number_input("Age", 10, 60, 25)
        phone = st.text_input("Phone")
        location = st.text_input("Location")
        gest = st.number_input("Gestational age (weeks)", 0, 45, 12)
        parity = st.number_input("Parity", 0, 20, 0)
        bp_sys = st.number_input("BP systolic", 0, 250, 120)
        bp_dia = st.number_input("BP diastolic", 0, 200, 80)
        hb = st.number_input("Haemoglobin (g/dL)", 0.0, 30.0, 12.0, format="%.1f")
        bmi = st.number_input("BMI", 0.0, 60.0, 24.0, format="%.1f")
        notes = st.text_area("Notes")
        if st.form_submit_button("Register"):
            mother_id = "AFY-" + uuid.uuid4().hex[:8].upper()
            db.add_mother({
                'mother_id': mother_id,
                'name': name, 'age': int(age), 'phone': phone, 'location': location,
                'gestational_age_weeks': int(gest), 'parity': int(parity),
                'bp_systolic': int(bp_sys), 'bp_diastolic': int(bp_dia),
                'hb': float(hb), 'bmi': float(bmi), 'notes': notes, 'status': 'active'
            })
            st.success(f"✅ Registered ID: {mother_id}")

            # ✅ Generate & show barcode
            barcode_file = generate_barcode(mother_id)
            if barcode_file:
                st.image(barcode_file, caption="Mother ID Barcode")
            else:
                st.warning("Barcode module missing — showing ID text only:")
                st.code(mother_id)

# MOTHER PROFILES
elif page == "Mother Profiles":
    st.header("👩 Mother Profiles")
    mothers = db.get_mothers()
    if not mothers:
        st.info("No mothers yet.")
    else:
        df = pd.DataFrame(mothers)
        sel = st.selectbox("Select mother", df['mother_id'] + " — " + df['name'])
        mid = sel.split(" — ")[0]
        m = db.get_mother_by_id(mid)

        # ✅ Show barcode
        st.subheader("Mother ID Badge")
        barcode_file = generate_barcode(mid)
        if barcode_file:
            st.image(barcode_file, width=250, caption=f"ID: {mid}")
        else:
            st.code(mid)

        # (rest of your Mother Profile page unchanged — kept fully same)  
        ...  # ✅ replace this line with the remaining code EXACTLY as in your file

# (ALL OTHER PAGES REMAIN EXACTLY SAME — no change)

# FOOTER
st.markdown("---")
st.caption("Afyamama — Empowering mothers, saving lives.")

# ✅ Hide Streamlit "Made with Streamlit"
hide_footer = """
<style>
footer {visibility: hidden !important;}
</style>
"""
st.markdown(hide_footer, unsafe_allow_html=True)
