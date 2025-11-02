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

# ---------------- SETTINGS ----------------
st.set_page_config(page_title="Afyamama Health System", layout="wide")
db.init_db()
DB_PATH = Path(__file__).parent / "afyamama.db"

# ---------- AI assistant logic (improved) ----------
def offline_ai_response(text):
    t = (text or "").lower()
    # prioritized emergency/danger signs
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
    # fallback
    return ("This is informational. Encourage ANC visits, monitor BP & Hb, teach danger signs "
            "(bleeding, severe headache, visual changes, swelling, reduced fetal movement) and refer to facility for emergencies.")

# ---------- Sidebar navigation (session stable) ----------
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

# ---------- Helpers: fallback SQL functions ----------
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

def add_anc_visit_fallback(mid, visit_date, bp_systolic, bp_diastolic, hb, weight, urine_protein, fetal_hr, fundal_height, symptoms, notes):
    # store detailed items in notes JSON-like string to avoid schema changes
    combined_notes = ""
    if symptoms:
        combined_notes += f"Symptoms: {symptoms}\n"
    if urine_protein is not None:
        combined_notes += f"Urine protein: {urine_protein}\n"
    if fetal_hr is not None:
        combined_notes += f"Fetal HR: {fetal_hr}\n"
    if fundal_height is not None:
        combined_notes += f"Fundal height: {fundal_height}\n"
    if notes:
        combined_notes += f"Notes: {notes}\n"
    # fallback insertion into anc_visits table (table created in db.init_db)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # ensure hb and bp numeric where possible
    hb_val = float(hb) if hb not in (None, "") else None
    try:
        cur.execute("""INSERT INTO anc_visits (mother_id, visit_date, bp_systolic, bp_diastolic, hb, weight, notes, created_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (mid, visit_date, bp_systolic if bp_systolic else None, bp_diastolic if bp_diastolic else None,
                     hb_val, weight if weight else None, combined_notes, datetime.utcnow().isoformat()))
        conn.commit()
    except Exception as e:
        # attempt to create table and retry (defensive)
        cur.execute("""CREATE TABLE IF NOT EXISTS anc_visits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        mother_id TEXT,
                        visit_date TEXT,
                        bp_systolic INTEGER,
                        bp_diastolic INTEGER,
                        hb REAL,
                        weight REAL,
                        notes TEXT,
                        created_at TEXT
                       )""")
        conn.commit()
        cur.execute("""INSERT INTO anc_visits (mother_id, visit_date, bp_systolic, bp_diastolic, hb, weight, notes, created_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (mid, visit_date, bp_systolic if bp_systolic else None, bp_diastolic if bp_diastolic else None,
                     hb_val, weight if weight else None, combined_notes, datetime.utcnow().isoformat()))
        conn.commit()
    finally:
        conn.close()

# -------------------- PAGES --------------------

# HOME (detailed English + Swahili)
if page == "Home":
    st.markdown("<h1 style='text-align:center; color:#006400;'>🌸 Afyamama Health System</h1>", unsafe_allow_html=True)
    st.subheader("Welcome | Karibu")
    st.write("""
**Afyamama** is a practical digital tool for maternal & child health. It is built to help CHVs (Community Health Volunteers),
nurses, and mothers to register pregnancies, monitor vitals, detect risk early, record ANC visits, and manage follow-ups & referrals.

**Key features**
- Register mothers and store essential clinical data (BP, Hb, BMI, parity, gestational age).  
- Run a local clinical risk check (rule-based) with clear reasons why a mother is flagged.  
- Record ANC visits with detailed clinical fields (BP, HB, urine protein, fetal heart rate, fundal height, symptoms).  
- Schedule and track follow-ups and referrals.  
- Simple offline AI assistant for quick guidance about danger signs and common symptoms.

**Benefits**
Early identification of hypertension, severe anemia, and danger signs enables timely referral and better maternal outcomes.

---

### 🇰🇪 Kiswahili (Uelezaji)
**Afyamama** ni zana rahisi ya kidijitali kwa afya ya uzazi na mtoto. Inasaidia CHVs, wauguzi na mama kusajili ujauzito, kufuatilia dalili muhimu, kutambua hatari mapema, kurekodi ziara za ANC, na kupanga rufaa/follow-up.

**Sifa kuu**
- Kusajili mama na data muhimu (BP, HB, BMI, parity, wiki za ujauzito).  
- Kuendesha tathmini ya hatari ya kiafya hapa eneo (rule-based) na kutoa sababu.  
- Kurekodi ziara za ANC (BP, Hb, protein, moyo wa mtoto, fundal height, dalili).  
- Kupanga follow-up na rufaa kwa haraka.

**Lengo:** Kutambua hatari mapema na kupeleka mama kwa huduma kwa wakati.

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
        notes = st.text_area("Notes (clinical notes, danger signs, etc.)")
        if st.form_submit_button("Register"):
            mother_id = "AFY-" + uuid.uuid4().hex[:8].upper()
            db.add_mother({
                'mother_id': mother_id,
                'name': name,
                'age': int(age),
                'phone': phone,
                'location': location,
                'gestational_age_weeks': int(gest),
                'parity': int(parity),
                'bp_systolic': int(bp_sys),
                'bp_diastolic': int(bp_dia),
                'hb': float(hb),
                'bmi': float(bmi),
                'notes': notes,
                'status': 'active'
            })
            st.success(f"✅ Registered ID: {mother_id}")

# MOTHER PROFILES (edit, delete with confirm, refer)
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

        # display cleanly
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Name:** {m['name']}")
            st.markdown(f"**ID:** {m['mother_id']}")
            st.markdown(f"**Age:** {m['age']} yrs")
            st.markdown(f"**Phone:** {m['phone']}")
            st.markdown(f"**Location:** {m['location']}")
        with col2:
            st.markdown(f"**Gestation:** {m['gestational_age_weeks']} wks")
            st.markdown(f"**Parity:** {m['parity']}")
            st.markdown(f"**BP:** {m['bp_systolic']}/{m['bp_diastolic']} mmHg")
            st.markdown(f"**HB:** {m['hb']} g/dL")
            st.markdown(f"**BMI:** {m['bmi']}")

        st.markdown("---")
        r = risk_model.predict_risk(m['age'], m['bp_systolic'], m['bp_diastolic'], m['hb'], m['bmi'], m['parity'], m.get('notes',''))
        st.subheader("Risk Assessment")
        st.success(f"**{r['risk']}** (score {r['score']})")
        if r['reasons']:
            st.write("**Reasons:**")
            for reason in r['reasons']:
                st.write(f"- {reason}")

        if m.get('notes'):
            st.markdown("---")
            st.subheader("Clinical Notes")
            st.write(m['notes'])

        # Edit form inside expander
        st.markdown("---")
        with st.expander("✏️ Edit details"):
            edit_name = st.text_input("Name", value=m.get('name',''))
            edit_age = st.number_input("Age", value=m.get('age',25))
            edit_phone = st.text_input("Phone", value=m.get('phone',''))
            edit_loc = st.text_input("Location", value=m.get('location',''))
            edit_gest = st.number_input("Gestational weeks", value=m.get('gestational_age_weeks',0))
            edit_parity = st.number_input("Parity", value=m.get('parity',0))
            edit_bp_s = st.number_input("BP systolic", value=m.get('bp_systolic',0))
            edit_bp_d = st.number_input("BP diastolic", value=m.get('bp_diastolic',0))
            edit_hb = st.number_input("HB", value=m.get('hb',0.0), format="%.1f")
            edit_bmi = st.number_input("BMI", value=m.get('bmi',0.0), format="%.1f")
            edit_notes = st.text_area("Notes", value=m.get('notes',''))
            if st.button("Save changes"):
                data = {
                    'name': edit_name, 'age': int(edit_age), 'phone': edit_phone, 'location': edit_loc,
                    'gestational_age_weeks': int(edit_gest), 'parity': int(edit_parity),
                    'bp_systolic': int(edit_bp_s), 'bp_diastolic': int(edit_bp_d),
                    'hb': float(edit_hb), 'bmi': float(edit_bmi), 'notes': edit_notes, 'status': m.get('status','active')
                }
                # db has edit_mother function named edit_mother per updated db.py
                if hasattr(db, "edit_mother"):
                    db.edit_mother(mid, data)
                else:
                    conn = sqlite3.connect(DB_PATH)
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE mothers SET name=?, age=?, phone=?, location=?, gestational_age_weeks=?, parity=?,
                                          bp_systolic=?, bp_diastolic=?, hb=?, bmi=?, notes=?, status=?
                        WHERE mother_id=?
                    """, (
                        data['name'], data['age'], data['phone'], data['location'], data['gestational_age_weeks'],
                        data['parity'], data['bp_systolic'], data['bp_diastolic'], data['hb'], data['bmi'],
                        data['notes'], data['status'], mid
                    ))
                    conn.commit()
                    conn.close()
                st.success("Details updated.")
                st.experimental_rerun()

        # Delete with confirm two-step
        if "confirm_delete" not in st.session_state:
            st.session_state.confirm_delete = None

        if st.button("🗑 Delete mother"):
            st.session_state.confirm_delete = mid

        if st.session_state.confirm_delete == mid:
            st.warning("Are you sure you want to permanently delete this mother? This action cannot be undone.")
            colc1, colc2 = st.columns([1,1])
            with colc1:
                if st.button("Confirm Delete"):
                    if hasattr(db, "delete_mother"):
                        db.delete_mother(mid)
                    else:
                        conn = sqlite3.connect(DB_PATH)
                        cur = conn.cursor()
                        cur.execute("DELETE FROM mothers WHERE mother_id=?", (mid,))
                        conn.commit()
                        conn.close()
                    st.success("Mother deleted.")
                    st.session_state.confirm_delete = None
                    st.experimental_rerun()
            with colc2:
                if st.button("Cancel"):
                    st.session_state.confirm_delete = None
                    st.success("Delete cancelled.")

        # Refer button
        st.markdown("---")
        if st.button("🚑 Refer to higher-level facility"):
            note = f"Referral: refer for urgent review (generated {datetime.utcnow().isoformat()})"
            if hasattr(db, "add_followup"):
                db.add_followup(mid, datetime.utcnow().isoformat(), note)
            else:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("INSERT INTO followups (mother_id, due_date, notes, created_at) VALUES (?,?,?,?)",
                            (mid, datetime.utcnow().isoformat(), note, datetime.utcnow().isoformat()))
                conn.commit()
                conn.close()
            st.error("Mother referred and follow-up created.")

# ANC VISITS (Detailed - option B)
elif page == "ANC Visits":
    st.header("📅 ANC Visit Tracker (Detailed)")

    mothers = db.get_mothers()
    if not mothers:
        st.info("Register mothers first.")
    else:
        df = pd.DataFrame(mothers)
        sel = st.selectbox("Select mother", df['mother_id'] + " — " + df['name'])
        mid = sel.split(" — ")[0]

        st.subheader("Add ANC Visit (detailed)")
        with st.form("anc_form"):
            visit_date = st.date_input("Visit date", value=datetime.utcnow().date())
            bp_sys = st.number_input("BP Systolic", 80, 250, 120)
            bp_dia = st.number_input("BP Diastolic", 40, 150, 80)
            hb = st.number_input("Haemoglobin (g/dL)", 5.0, 20.0, 11.0, format="%.1f")
            weight = st.number_input("Weight (kg)", 30.0, 200.0, 60.0, format="%.1f")
            urine_protein = st.selectbox("Urine Protein", ["None","Trace","+1","+2","+3","+4"])
            fetal_hr = st.number_input("Fetal heart rate (bpm)", 80, 220, 140)
            fundal_height = st.number_input("Fundal height (cm)", 10.0, 50.0, 24.0, format="%.1f")
            symptoms = st.text_area("Symptoms (comma-separated)")
            notes = st.text_area("Additional notes")
            if st.form_submit_button("Save ANC Visit"):
                # prefer db.add_anc_visit if implemented (we designed it to accept dict earlier)
                anc_data = {
                    'mother_id': mid,
                    'visit_date': visit_date.isoformat(),
                    'bp_systolic': int(bp_sys),
                    'bp_diastolic': int(bp_dia),
                    'hb': float(hb),
                    'weight': float(weight),
                    # extras stored in notes
                    'notes': f"Urine protein: {urine_protein}; FetalHR: {fetal_hr}; FundalHeight: {fundal_height}; Symptoms: {symptoms}; {notes}"
                }
                if hasattr(db, "add_anc_visit"):
                    try:
                        db.add_anc_visit(anc_data)
                    except TypeError:
                        # some versions expect separate params: fallback to our helper
                        add_anc_visit_fallback(mid, visit_date.isoformat(), bp_sys, bp_dia, hb, weight, urine_protein, fetal_hr, fundal_height, symptoms, notes)
                else:
                    add_anc_visit_fallback(mid, visit_date.isoformat(), bp_sys, bp_dia, hb, weight, urine_protein, fetal_hr, fundal_height, symptoms, notes)
                st.success("ANC visit saved.")

        # show visits and chart
        st.subheader("Past ANC Visits")
        visits = []
        if hasattr(db, "get_anc_visits"):
            visits = db.get_anc_visits(mid)
        else:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM anc_visits WHERE mother_id=? ORDER BY visit_date DESC", (mid,))
            rows = cur.fetchall()
            visits = [dict(r) for r in rows]
            conn.close()

        if visits:
            dfv = pd.DataFrame(visits)
            st.dataframe(dfv)
            # try to plot HB and fetal HR (if stored)
            # HB plot
            if 'hb' in dfv.columns:
                try:
                    dfv['hb'] = pd.to_numeric(dfv['hb'], errors='coerce')
                    display_hb = dfv.set_index(pd.to_datetime(dfv['visit_date']))['hb'].dropna()
                    if not display_hb.empty:
                        st.line_chart(display_hb)
                except Exception:
                    pass
            # fetal HR may be embedded in notes; try extract and plot if present
            try:
                # extract fetal HR from 'notes' if present with pattern "FetalHR: {num}"
                def extract_fhr(note):
                    if not note: return None
                    for part in str(note).split(';'):
                        part = part.strip()
                        if part.lower().startswith("fetalhr"):
                            try:
                                return float(part.split(':')[1].strip())
                            except:
                                return None
                    return None
                dfv['fhr'] = dfv['notes'].apply(extract_fhr)
                if dfv['fhr'].notna().any():
                    display_fhr = dfv.set_index(pd.to_datetime(dfv['visit_date']))['fhr'].dropna()
                    if not display_fhr.empty:
                        st.line_chart(display_fhr)
            except Exception:
                pass
        else:
            st.info("No ANC visits recorded for this mother yet.")

# RISK ASSESSMENT (manual)
elif page == "Risk Assessment":
    st.header("⚠️ Manual Risk Assessment")
    with st.form("riskform"):
        age = st.number_input("Age", 10, 60, 25)
        bp_sys = st.number_input("BP systolic", 0, 250, 120)
        bp_dia = st.number_input("BP diastolic", 0, 200, 80)
        hb = st.number_input("Haemoglobin (g/dL)", 0.0, 30.0, 12.0, format="%.1f")
        bmi = st.number_input("BMI", 0.0, 60.0, 24.0, format="%.1f")
        parity = st.number_input("Parity", 0, 20, 0)
        notes = st.text_area("Notes (optional)")
        if st.form_submit_button("Assess"):
            r = risk_model.predict_risk(age, bp_sys, bp_dia, hb, bmi, parity, notes)
            st.subheader("Result")
            st.success(f"Risk category: **{r['risk']}** (score {r['score']})")
            if r['reasons']:
                st.write("Reasons:")
                for rr in r['reasons']:
                    st.write(f"- {rr}")

# PREDICTIVE INSIGHTS (detailed)
elif page == "Predictive Insights":
    st.header("🔮 Predictive Insights (Clinical)")

    st.info("This is an estimation using rule-based clinical indicators — not a diagnosis.")

    age = st.number_input("Age", 10, 60, 28)
    bp_sys = st.number_input("BP systolic", 80, 250, 120)
    bp_dia = st.number_input("BP diastolic", 40, 150, 80)
    hb = st.number_input("Hemoglobin (g/dL)", 5.0, 18.0, 11.0)
    bmi = st.number_input("BMI", 10.0, 45.0, 23.0)
    parity = st.number_input("Parity", 0, 10, 1)
    notes = st.text_area("Notes / Symptoms (e.g., headache, vomiting, reduced movement)")

    if st.button("Run Prediction"):
        r = risk_model.predict_risk(age, bp_sys, bp_dia, hb, bmi, parity, notes)
        # heuristic probability scale
        prob = min(1.0, r['score'] / 8.0)
        st.metric("Estimated Risk (0-1)", f"{prob:.2f}")
        st.subheader("Clinical Interpretation")
        st.write(f"**Category:** {r['risk']}")
        if r['reasons']:
            st.write("**Contributing factors:**")
            for reason in r['reasons']:
                st.write(f"- {reason}")
        st.markdown("**Suggested actions:**")
        if r['risk'] == "High Risk":
            st.write("- Immediate referral and facility review; consider admission if unstable.")
        elif r['risk'] == "Moderate Risk":
            st.write("- Increase follow-up frequency, re-check BP/Hb within 1–2 weeks.")
        else:
            st.write("- Routine ANC and counseling on nutrition & danger signs.")
        # small illustrative chart vs BP
        try:
            bp_range = np.linspace(bp_sys-10, bp_sys+10, 11)
            scores = [risk_model.predict_risk(age, float(b), bp_dia, hb, bmi, parity, notes)['score'] for b in bp_range]
            st.line_chart(pd.DataFrame({"bp": bp_range, "score": scores}).set_index("bp"))
        except Exception:
            pass

# CHILD PROFILES
elif page == "Child Profiles":
    st.header("👶 Child Profiles")
    st.info("Child module active. Add children from Mother Profiles or Register modules.")

# FOLLOW-UPS (schedule, list, mark done)
elif page == "Follow-ups":
    st.header("📅 Follow-ups & Referrals")
    mothers = db.get_mothers()
    if not mothers:
        st.info("No mothers registered.")
    else:
        df = pd.DataFrame(mothers)
        sel = st.selectbox("Select mother", df['mother_id'] + " — " + df['name'])
        mid = sel.split(" — ")[0]

        with st.form("follow_form"):
            due = st.date_input("Due date", value=datetime.utcnow().date() + timedelta(days=7))
            notes = st.text_area("Notes")
            if st.form_submit_button("Schedule Follow-up"):
                if hasattr(db, "add_followup"):
                    db.add_followup(mid, due.isoformat(), notes)
                else:
                    conn = sqlite3.connect(DB_PATH)
                    cur = conn.cursor()
                    cur.execute("INSERT INTO followups (mother_id, due_date, notes, created_at) VALUES (?,?,?,?)",
                                (mid, due.isoformat(), notes, datetime.utcnow().isoformat()))
                    conn.commit()
                    conn.close()
                st.success("Follow-up scheduled.")

        st.markdown("---")
        st.subheader("All follow-ups")
        followups = []
        if hasattr(db, "get_followups"):
            try:
                followups = db.get_followups()
            except Exception:
                followups = fetch_followups_from_db()
        else:
            followups = fetch_followups_from_db()

        if followups:
            df_f = pd.DataFrame(followups)
            st.dataframe(df_f)
            for fu in followups:
                if not fu.get('done', 0):
                    if st.button(f"Mark done #{fu.get('id')} ({fu.get('mother_id')})"):
                        if hasattr(db, "mark_followup_done"):
                            db.mark_followup_done(fu.get('id'))
                        else:
                            mark_followup_done_db(fu.get('id'))
                        st.success("Marked done.")
                        st.experimental_rerun()
        else:
            st.info("No follow-ups scheduled.")

# AI ASSISTANT (improved; keeps chat in session_state)
elif page == "AI Assistant":
    st.header("🤖 Afyamama AI Assistant (Offline)")
    if "chat" not in st.session_state:
        st.session_state.chat = []
    for c in st.session_state.chat:
        st.markdown(f"**You:** {c['q']}")
        st.markdown(f"**Afyamama:** {c['a']}")
    q = st.text_input("Describe the symptom(s) or ask a question (e.g., 'severe headache and blurred vision'):")
    if st.button("Send"):
        a = offline_ai_response(q)
        st.session_state.chat.append({"q": q, "a": a})
        try:
            db.add_chat_log(None, q, a)
        except Exception:
            pass
        st.experimental_rerun()

# REPORTS
elif page == "Reports":
    st.header("📁 Reports & Exports")
    mothers = db.get_mothers()
    if mothers:
        df = pd.DataFrame(mothers)
        st.dataframe(df)
        st.download_button("Download CSV", df.to_csv(index=False).encode(), "mothers.csv")
    else:
        st.info("No data yet.")

# FOOTER
st.markdown("---")
st.caption("Afyamama — Empowering mothers, saving lives.")

# ✅ Hide "Made with Streamlit"
hide_footer = """
<style>
footer {visibility: hidden !important;}
</style>
"""
st.markdown(hide_footer, unsafe_allow_html=True)

