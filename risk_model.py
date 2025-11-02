# Simple rule-based risk predictor for maternal risk categories.
# Replace with an ML model later if you collect labelled data.

def predict_risk(age, bp_systolic, bp_diastolic, hb, bmi, parity, notes=''):
    score = 0
    reasons = []

    if age is not None and age >= 35:
        score += 2
        reasons.append('Advanced maternal age (>=35)')
    if bp_systolic is not None and bp_systolic >= 140:
        score += 3
        reasons.append('High systolic blood pressure (>=140)')
    if bp_diastolic is not None and bp_diastolic >= 90:
        score += 2
        reasons.append('High diastolic blood pressure (>=90)')
    if hb is not None and hb < 11:
        score += 2
        reasons.append('Low haemoglobin (<11 g/dL)')
    if bmi is not None and bmi >= 30:
        score += 1
        reasons.append('High BMI (>=30)')
    if parity is not None and parity >= 5:
        score += 1
        reasons.append('High parity (>=5)')
    if 'bleed' in (notes or '').lower():
        score += 4
        reasons.append('Reported bleeding')

    if score >= 6:
        risk = 'High Risk'
    elif score >= 3:
        risk = 'Moderate Risk'
    else:
        risk = 'Low Risk'

    return {
        'risk': risk,
        'score': score,
        'reasons': reasons
    }
