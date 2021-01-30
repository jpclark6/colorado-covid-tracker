from flask_lambda import FlaskLambda
from flask import jsonify

app = FlaskLambda(__name__)

@app.route('/covid-data') # need better route. Pass in daily as a param?
def daily_cases():
    mock_data = [
        {
            "date": "2020-01-15",
            "newCases": 492,
            "cumulativeCases": 429834,
            "newFirstDoseVaccinated": 4234,
            "cumulativeFirstDoseVaccinated": 429384
        },
        {
            "date": "2020-01-16",
            "newCases": 200,
            "cumulativeCases": 449834,
            "newFirstDoseVaccinated": 2423,
            "cumulativeFirstDoseVaccinated": 4669384
        },
        {
            "date": "2020-01-17",
            "newCases": 184,
            "cumulativeCases": 459834,
            "newFirstDoseVaccinated": 5242,
            "cumulativeFirstDoseVaccinated": 519384
        }
    ]
    return jsonify(mock_data)
