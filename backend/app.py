from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import os

app = Flask(__name__)

# Load exercise data
try:
    EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'exercises.xlsx')
    print(f"[INFO] Loading Excel from: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")
    df = df.rename(columns={df.columns[0]: "Exercise"})
    df = df[df["Exercise"].str.lower() != "exercises"]
    print(f"[INFO] Loaded {len(df)} rows of exercise data.")
except Exception as e:
    print(f"[ERROR] Failed to load exercise data: {e}")
    df = pd.DataFrame()

# Load rules from Sheet2 (endurance removed)
try:
    df_rules2 = pd.read_excel(EXCEL_PATH, sheet_name="Sheet2", skiprows=1)
    df_rules2 = df_rules2.rename(columns={df_rules2.columns[1]: "Rules"})
    df_rules2 = df_rules2.drop(columns=df_rules2.columns[0])
    df_rules2 = df_rules2.set_index("Rules").T
    df_rules2.index = df_rules2.index.str.strip().str.lower()

    rules_by_focus = {}
    for focus in df_rules2.index:
        if "endurance" in focus:
            continue
        row = df_rules2.loc[focus]
        rules_by_focus[focus] = {
            "reps": row.get("Number of Reps", "N/A"),
            "rest": row.get("Rest Times", "N/A"),
            "sets": row.get("Number of sets", "N/A")
        }

    print("[INFO] Loaded rules for:", list(rules_by_focus.keys()))
except Exception as e:
    print(f"[ERROR] Failed to load rules: {e}")
    rules_by_focus = {}

# Dropdown options
def get_dropdown_options():
    try:
        values = df.drop(columns=["Exercise"]).values.flatten()
        values = pd.Series(values).dropna().unique()
        focus_options = sorted(set([
            val.split('-')[0] if '-' in val else val
            for val in values
            if isinstance(val, str)
            and val not in ['None', 'Low', 'Full']
            and "endurance" not in val.lower()
        ]))
        subcat_options = sorted(set([
            val for val in values
            if '-' in val and "endurance" not in val.lower()
        ]))
        access_options = sorted(set([
            val for val in values if val in ['None', 'Low', 'Full']
        ]))
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

# Generate plan
@app.route('/get_workouts', methods=['GET'])
def get_workouts():
    focus = request.args.get('focus')
    subcategory = request.args.get('subcategory')
    access = request.args.get('access')
    days = int(request.args.get('days', 3))

    try:
        if "endurance" in focus.lower():
            return jsonify({f"Day {i+1}": [] for i in range(days)})

        def row_matches(row):
            values = [str(v) for v in row.values if pd.notna(v)]
            has_focus = any(v.startswith(focus) for v in values)
            has_subcategory = subcategory in values
            has_access = access in values
            return has_focus and has_subcategory and has_access

        matching = df[df.apply(row_matches, axis=1)]
        all_exercises = matching["Exercise"].dropna().tolist()

        # Decide exercises/day
        is_fullbody = "full" in subcategory.lower()
        ex_per_day = 6 if is_fullbody else 4
        total_needed = ex_per_day * days

        # Barbell filter
        barbell_exs = [ex for ex in all_exercises if "barbell" in ex.lower() or "hexbar" in ex.lower()]
        other_exs = [ex for ex in all_exercises if ex not in barbell_exs]

        # Allow repeats
        if access.lower() == "full":
            required_per_day = 2 if is_fullbody else 1
            barbell_pool = (barbell_exs * ((required_per_day * days) // len(barbell_exs) + 1))[:required_per_day * days]
            other_needed = total_needed - (required_per_day * days)
            other_pool = (other_exs * ((other_needed // len(other_exs)) + 1))[:other_needed]
        else:
            # No barbell requirements
            barbell_pool = []
            other_pool = (all_exercises * ((total_needed // len(all_exercises)) + 1))[:total_needed]

        # Merge pools
        combined = []
        for i in range(days):
            day_exs = []
            if access.lower() == "full":
                day_exs.extend(barbell_pool[i * required_per_day : (i + 1) * required_per_day])
            day_exs.extend(other_pool[i * (ex_per_day - len(day_exs)) : (i + 1) * (ex_per_day - len(day_exs))])
            combined.extend(day_exs)

        # Build plan
        plan = {}
        focus_key = focus.strip().lower().replace("-", "_")
        rule = rules_by_focus.get(focus_key, {})

        for i in range(days):
            day_exercises = combined[i * ex_per_day : (i + 1) * ex_per_day]
            plan[f"Day {i+1}"] = [{
                "exercise": ex,
                "sets": rule.get("sets", "N/A"),
                "reps": rule.get("reps", "N/A"),
                "rest": rule.get("rest", "N/A")
            } for ex in day_exercises]

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
    app.run(debug=True


