# Rule-based AI assistant with English + Swahili responses.
import random

FAQ_RULES = [
    (['pregnant','pregnancy','antenatal','anc'], "Pregnancy requires routine antenatal care. Try to attend at least 4 ANC visits; eat iron-rich foods and rest."),
    (['bp','blood pressure','hypertension','pressure'], "High blood pressure in pregnancy can be dangerous. If you have severe headache, visual changes, or swelling, seek urgent care."),
    (['bleeding','bleed'], "Any bleeding during pregnancy is a danger sign. Go to the nearest health facility immediately."),
    (['vomit','vomiting','nausea'], "Mild nausea is common. Sip fluids, eat small frequent meals. If you cannot keep fluids down, visit a clinic."),
    (['nutrition','food','eat'], "Eat a balanced diet: sukuma wiki, beans, eggs, fruits; take iron and folic acid as advised."),
    (['baby','child','infant','immunization','vaccine'], "Ensure your child's immunizations are up to date and monitor growth. Visit the clinic for routine immunizations."),
    (['fever','temperature'], "Fever in a pregnant mother or baby can be serious. Measure temperature; if >38°C or if the mother is unwell, visit a clinic."),
    (['swahili','kiswahili','kiswahili?'], "Habari mama! Unaweza kuniuliza kwa Kiswahili pia. Ninaweza kusema kuhusu lishe, dalili hatari, na chanjo."),
]

FALLBACKS = [
    "I'm sorry, I don't have a confident answer for that. It's safest to visit your nearest health facility.",
    "Nisamehe, sijui jibu kamili. Tafadhali tembelea kituo cha afya kwa ushauri wa kliniki."
]

def ai_response(query, mother_id=None):
    q = (query or '').lower()
    # exact keyword matching
    for keywords, reply in FAQ_RULES:
        for kw in keywords:
            if kw in q:
                # small chance to include empathy and local touch
                prefix = random.choice(["", "⚠️ ", "😊 "])
                return prefix + reply
    # fallback
    return random.choice(FALLBACKS)
