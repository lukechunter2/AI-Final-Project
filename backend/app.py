from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import os

app = Flask(__name__)

# Load exercise data
try:
    EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'exercises.xlsx')
    print(f"[INFO] Loading Excel from: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1", header=1)
    df = df.rename(columns={df.columns[0]: "Exercise"})
    df = df[df["Exercise"].str.lower() != "exercises"]
    df["Movement type"] = df["Movement type"].str.strip().str.lower()
    print(f"[INFO] Loaded {len(df)} exercises.")
except Exception as e:
    print(f"[ERROR] Failed to load exercise data: {e}")
    df = pd.DataFrame()

# Load rules (Sheet2 only)
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

    print("[INFO] Rules loaded.")
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
        return {"focus": [], "subcategory": [], "access": []}

# Plan generation
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
            return (
                any(v.startswith(focus) for v in values)
                and subcategory in values
                and access in values
            )

        matching = df[df.apply(row_matches, axis=1)]
        matching = matching.dropna(subset=["Exercise", "Movement type"])

        # Group by movement type
        push_pool = matching[matching["Movement type"] == "push"]["Exercise"].tolist()
        pull_pool = matching[matching["Movement type"] == "pull"]["Exercise"].tolist()
        legs_pool = matching[matching["Movement type"] == "legs"]["Exercise"].tolist()

        # Barbell filter (Full access only)
        barbell_pool = []
        if access.lower() == "full":
            barbell_pool = matching[matching["Exercise"].str.lower().str.contains("barbell|hexbar")]["Exercise"].tolist()

        # Determine daily structure
        sub = subcategory.lower()
        if "full" in sub:
            daily_target = {"push": 2, "pull": 2, "legs": 2}
            barbell_needed = 2
        elif "upper" in sub:
            daily_target = {"push": 2, "pull": 2}
            barbell_needed = 1
        elif "lower" in sub:
            daily_target = {"legs": 4}
            barbell_needed = 1
        else:
            daily_target = {}
            barbell_needed = 0

        focus_key = focus.strip().lower().replace("-", "_")
        rule = rules_by_focus.get(focus_key, {})
        plan = {}

        for i in range(days):
            selected = []

            # Pull from movement pools
            for group, count in daily_target.items():
                source = {
                    "push": push_pool,
                    "pull": pull_pool,
                    "legs": legs_pool
                }[group]
                if len(source) < count:
                    source *= (count // len(source)) + 1
                selected += source[i * count : i * count + count]

            # Barbell insertion (overwrite as needed)
            if access.lower() == "full" and barbell_pool:
                if len(barbell_pool) < barbell_needed:
                    barbell_pool *= (barbell_needed // len(barbell_pool)) + 1
                for b in barbell_pool[i * barbell_needed : (i + 1) * barbell_needed]:
                    if b not in selected:
                        selected[-1] = b  # replace last to guarantee barbell

            plan[f"Day {i+1}"] = [{
                "exercise": ex,
                "sets": rule.get("sets", "N/A"),
                "reps": rule.get("reps", "N/A"),
                "rest": rule.get("rest", "N/A")
            } for ex in selected]

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



