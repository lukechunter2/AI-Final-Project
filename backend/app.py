from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import os

app = Flask(__name__)

# Load exercise data
try:
    EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'exercises.xlsx')
    print(f"[INFO] Loading Excel from: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")
    first_col_name = df.columns[0]
    df = df.rename(columns={first_col_name: "Exercise"})
    df = df[df["Exercise"].str.lower() != "exercises"]
    print(f"[INFO] Loaded {len(df)} rows of exercise data.")
except Exception as e:
    print(f"[ERROR] Failed to load exercise data: {e}")
    df = pd.DataFrame()

# Load workout rules from Sheet2 and Sheet3
try:
    # Sheet2
    df_rules2 = pd.read_excel(EXCEL_PATH, sheet_name="Sheet2", skiprows=1)
    df_rules2 = df_rules2.rename(columns={df_rules2.columns[1]: "Rules"})
    df_rules2 = df_rules2.drop(columns=df_rules2.columns[0])
    df_rules2 = df_rules2.set_index("Rules").T

    # Sheet3 (manually set column headers)
    df_rules3_raw = pd.read_excel(EXCEL_PATH, sheet_name="Sheet3", header=None)
    df_rules3_raw.columns = ["Blank1", "Blank2", "Rules", "Endurance_Anaerobic", "Endurance_Aerobic"]
    df_rules3 = df_rules3_raw[["Rules", "Endurance_Anaerobic", "Endurance_Aerobic"]].dropna()
    df_rules3 = df_rules3.set_index("Rules").T

    # Combine rules
    df_rules = pd.concat([df_rules2, df_rules3])
    df_rules.index = df_rules.index.str.strip().str.lower()

    # Unified rule logic for all categories
    rules_by_focus = {}
    for focus in df_rules.index:
        row = df_rules.loc[focus]
        rules_by_focus[focus] = {
            "reps": row.get("Number of Reps", "N/A"),
            "rest": row.get("Rest Times", "N/A"),
            "sets": row.get("Number of sets", "N/A")
        }

    print("[INFO] Workout rules fully loaded and validated.")
except Exception as e:
    print(f"[ERROR] Failed to load workout rules: {e}")
    rules_by_focus = {}

# Dropdown population
def get_dropdown_options():
    try:
        values = df.drop(columns=["Exercise"]).values.flatten()
        values = pd.Series(values).dropna().unique()
        focus_options = sorted(set([
            val.split('-')[0] if '-' in val else val
            for val in values
            if isinstance(val, str) and val not in ['None', 'Low', 'Full']
        ]))
        subcat_options = sorted(set([val for val in values if '-' in val]))
        access_options = sorted(set([val for val in values if val in ['None', 'Low', 'Full']]))
        return {
            "focus": focus_options,
            "subcategory": subcat_options,
            "access": access_options
        }
    except Exception as e:
        print(f"[ERROR] Failed to extract dropdown options: {e}")
        return {
            "focus": [],
            "subcategory": [],
            "access": []
        }

# Workout generation
@app.route('/get_workouts', methods=['GET'])
def get_workouts():
    focus = request.args.get('focus')
    subcategory = request.args.get('subcategory')
    access = request.args.get('access')
    days = int(request.args.get('days', 3))

    try:
        def row_matches(row):
            values = [str(v) for v in row.values if pd.notna(v)]
            has_focus = any(v.startswith(focus) for v in values)
            has_subcategory = subcategory in values
            has_access = access in values
            return has_focus and has_subcategory and has_access

        matching = df[df.apply(row_matches, axis=1)]
        exercises = matching["Exercise"].dropna().tolist()
        plan = {f"Day {i+1}": [] for i in range(days)}

        focus_key = focus.strip().lower().replace("-", "_")
        rule = rules_by_focus.get(focus_key, {})

        for i, exercise in enumerate(exercises):
            plan[f"Day {(i % days) + 1}"].append({
                "exercise": exercise,
                "sets": rule.get("sets", "N/A"),
                "reps": rule.get("reps", "N/A"),
                "rest": rule.get("rest", "N/A")
            })

        return jsonify(plan)
    except Exception as e:
        print(f"[ERROR] Failed to generate plan: {e}")
        return jsonify({f"Day {i+1}": [] for i in range(days)})

@app.route('/get_options', methods=['GET'])
def get_options():
    return jsonify(get_dropdown_options())

# Serve frontend
@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

if __name__ == '__main__':
    app.run(debug=True)




