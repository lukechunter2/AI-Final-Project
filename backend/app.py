from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import os

app = Flask(__name__)

# Load exercises from Sheet1
try:
    EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'exercises.xlsx')
    print(f"[INFO] Loading Excel from: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")
    df = df.rename(columns={df.columns[0]: "Exercise"})
    df = df[df["Exercise"].str.lower() != "exercises"]
    print(f"[INFO] Loaded {len(df)} exercises.")
except Exception as e:
    print(f"[ERROR] Failed to load Sheet1: {e}")
    df = pd.DataFrame()

# Load workout rules from Sheet2 and Sheet3
try:
    # Sheet2
    df2 = pd.read_excel(EXCEL_PATH, sheet_name="Sheet2", skiprows=1)
    df2 = df2.rename(columns={df2.columns[1]: "Rules"})
    df2 = df2.drop(columns=df2.columns[0])
    df2 = df2.set_index("Rules").T

    # Sheet3
    df3_raw = pd.read_excel(EXCEL_PATH, sheet_name="Sheet3", header=1)
    df3 = df3_raw.set_index("Rules").T

    # Merge and clean
    df_rules = pd.concat([df2, df3])
    df_rules.index = df_rules.index.str.strip().str.lower()
    df_rules.columns = df_rules.columns.str.strip()

    rules_by_focus = {}
    for focus in df_rules.index:
        row = df_rules.loc[focus]
        rules_by_focus[focus] = {
            "reps": row.get("Number of Reps", "N/A"),
            "rest": row.get("Rest Times", "N/A"),
            "sets": row.get("Number of sets", "N/A")
        }

    print("[INFO] Loaded rules for:", list(rules_by_focus.keys()))
except Exception as e:
    print(f"[ERROR] Failed to load rules: {e}")
    rules_by_focus = {}

# Dropdown menu data
def get_dropdown_options():
    try:
        values = df.drop(columns=["Exercise"]).values.flatten()
        values = pd.Series(values).dropna().unique()
        focus_options = sorted(set([
            val.split('-')[0] if '-' in val else val
            for val in values if isinstance(val, str) and val not in ['None', 'Low', 'Full']
        ]))
        subcat_options = sorted(set([val for val in values if '-' in val]))
        access_options = sorted(set([val for val in values if val in ['None', 'Low', 'Full']]))
        return {
            "focus": focus_options,
            "subcategory": subcat_options,
            "access": access_options
        }
    except Exception as e:
        print(f"[ERROR] Dropdown generation failed: {e}")
        return {"focus": [], "subcategory": [], "access": []}

# Plan generation route
@app.route('/get_workouts', methods=['GET'])
def get_workouts():
    focus = request.args.get('focus')
    subcategory = request.args.get('subcategory')
    access = request.args.get('access')
    days = int(request.args.get('days', 3))

    try:
        def row_matches(row):
            values = [str(v) for v in row.values if pd.notna(v)]
            return (
                any(v.startswith(focus) for v in values)
                and subcategory in values
                and access in values
            )

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
        print(f"[ERROR] Failed to generate workout plan: {e}")
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


