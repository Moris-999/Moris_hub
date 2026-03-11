def predict_risk(sleep, stress, missed_med, alcohol):

    input_data = [[sleep, stress, missed_med, alcohol]]

    prediction = model.predict_proba(input_data)

    risk = prediction[0][1]

    return risk