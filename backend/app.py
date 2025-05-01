from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import os

app = Flask(__name__)

# Safely load the Excel file relative to this script
EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'exercises.xlsx')
df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1", header=2)

# Extract unique options for frontend dropdowns
def get_dropdown_options():
    values = df.drop(columns=['Unnamed: 0']).values.flatten()
    values = pd.Series(values).dropna().unique()
    focus_options = sorted(set([val.split('-')[0] for val in values if '-' in val]))
    subcat_options = sorted(set([val for val in values if '-' in val]))
    access_options = sorted(set([val for val in values if val in ['None', 'Low', 'Full']]))
    return {
        "focus": focus_options,
        "subcategory": subcat_options,
        "access": access_options
    }

@app.route('/get_workouts', methods=['GET'])
def get_workouts():
    focus = request.args.get('focus')
    subcategory = request.args.get('subcategory')
    access = request.args.get('access')
    days = int(request.args.get('days', 3))

    matching = df[df.apply(lambda row: all(
        tag in row.values for tag in [focus, subcategory, access]
    ), axis=1)]

    exercises = matching['Unnamed: 0'].dropna().tolist()
    plan = {f"Day {i+1}": [] for i in range(days)}
    for i, exercise in enumerate(exercises):
        plan[f"Day {(i % days) + 1}"].append(exercise)

    return jsonify(plan)

@app.route('/get_options', methods=['GET'])
def get_options():
    return jsonify(get_dropdown_options())

# Serve frontend files
@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

if __name__ == '__main__':
    app.run(debug=True)


