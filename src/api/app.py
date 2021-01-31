from flask_lambda import FlaskLambda
from flask import jsonify

app = FlaskLambda(__name__)


@app.route("/covid-data")
def daily_cases():
    # grab cleaned data from s3
    # format if needed
    # update to database if feeling motivated

    mock_data = [
        {
            "date": "2020-01-15",
            "newCases": 492,
            "cumulativeCases": 429834,
            "newFirstDoseVaccinated": 4234,
            "cumulativeFirstDoseVaccinated": 429384,
        },
        {
            "date": "2020-01-16",
            "newCases": 200,
            "cumulativeCases": 449834,
            "newFirstDoseVaccinated": 2423,
            "cumulativeFirstDoseVaccinated": 4669384,
        },
        {
            "date": "2020-01-17",
            "newCases": 184,
            "cumulativeCases": 459834,
            "newFirstDoseVaccinated": 5242,
            "cumulativeFirstDoseVaccinated": 519384,
        },
    ]
    return jsonify(mock_data)


# 7 Day moving average
# SELECT reporting_date,
#        AVG(positive_increase)
#             OVER(ORDER BY reporting_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS avg_positive_increase
# FROM cases;
