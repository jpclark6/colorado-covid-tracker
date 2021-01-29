from flask_lambda import FlaskLambda
from flask import jsonify

app = FlaskLambda(__name__)

@app.route('/hello', methods=['GET'])
def foo():
    
    return (
        json.dumps(data, indent=4, sort_keys=True),
        200,
        {'Content-Type': 'application/json'}
    )


if __name__ == '__main__':
    app.run(debug=True)