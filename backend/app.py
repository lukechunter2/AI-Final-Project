from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import os

app = Flask(__name__)

try:
    EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'exercises.xlsx')
    print(f"[INFO] Loading Excel from: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")
    first_col_name = df.columns[0]
    df = df.rename(columns={first_col_name: "Exercise"})
    df = df[df["Exercise"].str.lower() != "exercises"]
    print(f"[INFO] Loaded {len(df)} rows of exercise data.")
except Exception as e:
    print(f"[ERROR] Failed to load Excel file: {e}")
    df = pd.DataFrame()

# Load workout rules
try:
    df_rules1 = pd.read_excel(EXCEL_PATH, sheet_name="Sheet2", header=1)
    df_rules2 = pd.read_excel(EXCEL_PATH, sheet_name="Sheet3", header=1)
    df_rules = pd.concat([df_rules1, df_rules2], axis=1)

    rules_by_focus = {}
    col0 = df_rules.iloc[:, 0].astype(str).str.lower().str.strip()

    print("[DEBUG] Rule category rows found:")
    print(col0.tolist())

    for col in df_rules.columns[1:]:
        if col and isinstance(col, str):
            key = col.strip().lower()
            rule_row_map = {
                "reps": col0.str.contains("rep", na=False),
                "rest": col0.str.contains("rest", na=False),
                "sets": col0.str.contains("set", na=False)
            }

            rules_by_focus[key] = {}
            for k, row_filter in rule_row_map.items():
                matches = df_rules.loc[row_filter, col]
                rules_by_focus[key][k] = matches.values[0] if not matches.empty else "N/A"
    print("[INFO] Workout rules loaded.")
except Exception as e:
    print(f"[ERROR] Failed to load workout rules: {e}")
    rules_by_focus = {}

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

        focus_key = focus.strip().lower()
        rule = rules_by_focus.get(focus_key, {})

        for i, exercise in enumerate(exercises):
            plan[f"Day {(i % days) + 1}"].append({
                "exercise": exercise,
                "sets": rule.get("sets", ""),
                "reps": rule.get("reps", ""),
                "rest": rule.get("rest", "")
            })

        return jsonify(plan)
    except Exception as e:
        print(f"[ERROR] Failed to generate plan: {e}")
        return jsonify({f"Day {i+1}": [] for i in range(days)})

@app.route('/get_options', methods=['GET'])
def get_options():
    return jsonify(get_dropdown_options())

@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

if __name__ == '__main__':
    app.run(debug=True)







