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
    df["Movement type"] = df["Movement type"].astype(str).str.strip().str.lower()
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
        values = df.drop(columns=["Exercise", "Movement type"]).values.flatten()
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
            "focus": [], "subcategory": [], "access": []
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

        # Separate by movement type
        push_exs = matching[matching["Movement type"] == "push"]["Exercise"].tolist()
        pull_exs = matching[matching["Movement type"] == "pull"]["Exercise"].tolist()
        leg_exs = matching[matching["Movement type"] == "legs"]["Exercise"].tolist()

        # Barbell filtering (for Full access)
        barbell_exs = [ex for ex in matching["Exercise"] if "barbell" in ex.lower() or "hexbar" in ex.lower()]

        plan = {}
        is_fullbody = "full" in subcategory.lower()
        focus_key = focus.strip().lower().replace("-", "_")
        rule = rules_by_focus.get(focus_key, {})

        for day in range(days):
            day_exs = []

            if is_fullbody:
                needed = {"push": 2, "pull": 2, "legs": 2}
            elif "upper" in subcategory.lower():
                needed = {"push": 2, "pull": 2}
            elif "lower" in subcategory.lower():
                needed = {"legs": 4}
            else:
                needed = {}

            # Pull from each group with repeats allowed
            for mtype, count in needed.items():
                pool = {"push": push_exs, "pull": pull_exs, "legs": leg_exs}.get(mtype, [])
                if len(pool) < count:
                    pool *= (count // max(len(pool), 1)) + 1
                start = (day * count) % len(pool)
                day_exs.extend(pool[start : start + count])

            # Add barbell exercises if full access
            if access.lower() == "full":
                barbell_needed = 2 if is_fullbody else 1
                if len(barbell_exs) < barbell_needed:
                    barbell_exs *= (barbell_needed // max(len(barbell_exs), 1)) + 1
                start = (day * barbell_needed) % len(barbell_exs)
                inserts = barbell_exs[start : start + barbell_needed]
                for b in inserts:
                    if b not in day_exs:
                        day_exs[-1] = b  # replace final one to force inclusion

            plan[f"Day {day+1}"] = [{
                "exercise": ex,
                "sets": rule.get("sets", "N/A"),
                "reps": rule.get("reps", "N/A"),
                "rest": rule.get("rest", "N/A")
            } for ex in day_exs]

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




