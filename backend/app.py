from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import os

app = Flask(__name__)

# Hardcoded movement types
movement_type_map = {
    "Barbell Bench Press": "push", "Barbell Squat": "legs", "Barbell Front Squat": "legs",
    "Barbell Deadlift": "legs", "Barbell Overhead Shoulder Press": "push", "Barbell Incline Bench": "push",
    "Barbell Romanian Deadlift": "legs", "Barbell Row": "pull", "Hexbar Deadlift": "legs",
    "Dumbell Bench Press": "push", "Dumbell Overhead Shoulder Press": "push", "Dumbell Incline Bench": "push",
    "Dumbell Romanian Deadlift": "legs", "Dumbell Row": "pull", "Single Arm Dumbell Row": "pull",
    "Dumbell Goblet Squat": "legs", "Pushup": "push", "Pullup": "pull", "Dip": "push", "Chin-up": "pull",
    "Pistol Squat": "legs", "Dumbell Bicep curls": "pull", "Barbell Bicep Curls": "pull",
    "Overhead Tricep extensions": "push", "Dumbbell Single Leg Romanian Deadlifts": "legs",
    "Hang Cleans": "legs", "Power Cleans": "legs", "Seated Box Jumps": "legs", "Barbell Seated Box Jumps": "legs",
    "Dumbell Seated Box Jumps": "legs", "Bulgarian Split Squat": "legs", "Bulgarian Split Squat w/ Jumps": "legs",
    "Depth Jumps": "legs", "Skater Jumps": "legs", "Single leg landings": "legs",
    "Double leg landings with weight": "legs", "Nordic Curl": "legs", "Burpees": "push",
    "Burpee to box jump": "N/A", "Thruster": "push", "Box Jumps": "legs", "Weighted Lunges": "legs",
    "Lunges": "legs", "Squats": "legs"
}

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

# Load rules
try:
    df_rules2 = pd.read_excel(EXCEL_PATH, sheet_name="Sheet2", skiprows=1)
    df_rules2 = df_rules2.rename(columns={df_rules2.columns[1]: "Rules"})
    df_rules2 = df_rules2.drop(columns=df_rules2.columns[0])
    df_rules2 = df_rules2.set_index("Rules").T
    df_rules2.index = df_rules2.index.str.strip().str.lower()

    rules_by_focus = {}
    for focus in df_rules2.index:
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
        return {"focus": [], "subcategory": [], "access": []}

# Generate plan
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
                any(v.startswith(focus) for v in values) and
                subcategory in values and
                access in values
            )

        matching = df[df.apply(row_matches, axis=1)]
        all_exs = matching["Exercise"].dropna().tolist()

        # Organize by type
        push_exs = [e for e in all_exs if movement_type_map.get(e, "N/A") == "push"]
        pull_exs = [e for e in all_exs if movement_type_map.get(e, "N/A") == "pull"]
        leg_exs  = [e for e in all_exs if movement_type_map.get(e, "N/A") == "legs"]
        barbell_exs = [e for e in all_exs if "barbell" in e.lower() or "hexbar" in e.lower()]

        plan = {}
        for day in range(days):
            chosen = []

            if "full" in subcategory.lower():
                needed = {"push": 2, "pull": 2, "legs": 2}
                barbell_count = 2 if access.lower() == "full" else 0
            elif "upper" in subcategory.lower():
                needed = {"push": 2, "pull": 2}
                barbell_count = 1 if access.lower() == "full" else 0
            elif "lower" in subcategory.lower():
                needed = {"legs": 4}
                barbell_count = 1 if access.lower() == "full" else 0
            else:
                needed, barbell_count = {}, 0

            for t, n in needed.items():
                pool = {"push": push_exs, "pull": pull_exs, "legs": leg_exs}[t]
                if len(pool) < n:
                    pool *= (n // max(1, len(pool)) + 1)
                chosen.extend(pool[:n])

            if barbell_count > 0:
                if len(barbell_exs) < barbell_count:
                    barbell_exs *= (barbell_count // max(1, len(barbell_exs)) + 1)
                for b in barbell_exs[:barbell_count]:
                    if b not in chosen:
                        chosen[-1] = b

            focus_key = focus.strip().lower().replace("-", "_")
            rule = rules_by_focus.get(focus_key, {})
            plan[f"Day {day+1}"] = [{
                "exercise": e,
                "sets": rule.get("sets", "N/A"),
                "reps": rule.get("reps", "N/A"),
                "rest": rule.get("rest", "N/A")
            } for e in chosen]

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


