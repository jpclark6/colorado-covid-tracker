from flask_lambda import FlaskLambda
from flask import jsonify

app = FlaskLambda(__name__)

@app.route('/cases/daily')
def daily_cases():
    mock_data = {
        'validThrough': '2020-01-28',
        'data': [
            {'date': '2020-01-25', 'newCases': 500},
            {'date': '2020-01-26', 'newCases': 600},
            {'date': '2020-01-27', 'newCases': 700},
            {'date': '2020-01-28', 'newCases': 800},
        ]
    }
    return jsonify(mock_data)
