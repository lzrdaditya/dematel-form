from flask import Flask, render_template, request, redirect, url_for, flash, session
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SHEET_ID, TOKEN_SHEET_NAME, RESULT_SHEET_NAME, RESPONSES_SHEET_NAME, ADMIN_TOKEN

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Setup Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID)
token_ws = sheet.worksheet(TOKEN_SHEET_NAME)
result_ws = sheet.worksheet(RESULT_SHEET_NAME)
responses_ws = sheet.worksheet(RESPONSES_SHEET_NAME)
form_config_ws = sheet.worksheet("form_config")  # New worksheet for storing form config

def get_latest_factors():
    records = form_config_ws.get_all_records()
    # Work backwards to find the most recent valid config
    for row in reversed(records):
        try:
            factor_count = int(row.get("num_factors", 0))
            if factor_count <= 0:
                continue
            # Build the factor name list dynamically
            factors = [row.get(f"factor_{i+1}", "").strip() for i in range(factor_count)]
            # Only return if all factor names are present and not blank
            if all(factors) and all(f.strip() for f in factors):
                return factors
        except Exception:
            continue
    # Fallback default
    return ['Factor A', 'Factor B', 'Factor C']

def save_factors(factors):
    # factors is a list of names, e.g. ['A', 'B', ...]
    row = [len(factors)] + factors
    # Pad the row to match the header length (if needed)
    max_factors = 48  # or however many columns you want
    while len(row) <= max_factors:
        row.append('')
    form_config_ws.append_row(row)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        token_input = request.form["token"].strip()
        if token_input == ADMIN_TOKEN:
            session['role'] = 'admin'
            return redirect(url_for("admin_form_config"))
        tokens = token_ws.get_all_records()
        token_match = next(
            (t for t in tokens
             if t.get("token", "").strip().lower() == token_input.lower()
             and t.get("status", "").strip().lower() == "unused"),
            None
        )
        if token_match:
            session['role'] = 'expert'
            session['token'] = token_input
            session['expert'] = token_match.get("expert_name", "")
            return redirect(url_for("form"))
        else:
            return render_template("index.html", error="Invalid or used token.")
    return render_template("index.html")

@app.route("/admin/form-config", methods=["GET", "POST"])
def admin_form_config():
    if session.get('role') != 'admin':
        return redirect(url_for("index"))
    latest_factors = get_latest_factors()
    if request.method == "POST":
        try:
            num_factors = int(request.form["num_factors"])
            factor_names = []
            for i in range(num_factors):
                name = request.form.get(f"factor_name_{i}", "").strip()
                if not name:
                    flash("All factor names must be filled.", "danger")
                    return render_template("admin_form_config.html", factor_names=latest_factors)
                factor_names.append(name)
            save_factors(factor_names)
            flash("Form configuration updated!", "success")
            return redirect(url_for("admin_form_config"))
        except Exception as e:
            flash("Error in factor configuration: " + str(e), "danger")
    return render_template("admin_form_config.html", factor_names=latest_factors)

@app.route("/form", methods=["GET", "POST"])
def form():
    if session.get('role') != 'expert' or 'token' not in session:
        return redirect(url_for("index"))
    token = session['token']
    expert = session.get('expert', '')
    FACTORS = get_latest_factors()
    print("DEBUG: Latest factors used for form:", FACTORS)

    # Validate token on every load
    try:
        tokens = token_ws.get_all_records()
    except Exception as e:
        return "Error connecting to Google Sheets", 500

    token_match = next(
        (t for t in tokens
         if t.get("token", "").strip().lower() == token.lower()
         and t.get("status", "").strip().lower() == "unused"),
        None
    )

    if not token_match:
        return render_template("index.html", error="Invalid or used token. Please enter a valid token.")

    if request.method == "POST" and request.form.get("matrix_submitted") == "yes":
        # Re-validate token before accepting POST
        tokens = token_ws.get_all_records()
        token_match = next(
            (t for t in tokens
             if t.get("token", "").strip().lower() == token.lower()
             and t.get("status", "").strip().lower() == "unused"),
            None
        )
        if not token_match:
            return render_template("index.html", error="Invalid or used token. Please enter a valid token.")

        # Gather matrix values
        values = []
        for i, from_factor in enumerate(FACTORS):
            row_data = []
            for j, to_factor in enumerate(FACTORS):
                field_name = f"matrix_{i}_{j}"
                row_data.append(request.form.get(field_name, "0"))
            values.append(row_data)

        # Save to responses_ws as a matrix block (one row per matrix row)
        try:
            for i, from_factor in enumerate(FACTORS):
                row = [token, expert, from_factor] + FACTORS + values[i]
                responses_ws.append_row(row)
        except Exception as e:
            print("Failed to append to responses worksheet:", e)
            flash("Failed to save to responses worksheet.", "danger")

        # Save to result_ws (optional/legacy, still flat row)
        try:
            flat_matrix = [item for row in values for item in row]
            result_ws.append_row([token, expert] + FACTORS + flat_matrix)
        except Exception as e:
            print("Failed to append result:", e)
            flash("Failed to save to main results worksheet.", "danger")

        # Mark token as used
        try:
            cell = token_ws.find(token)
            token_ws.update_cell(cell.row, 2, "used")
        except Exception as e:
            print("Failed to update token status:", e)

        session.clear()
        return redirect(url_for("success"))

    return render_template("form.html", token=token, factors=FACTORS, expert=expert)
@app.route("/success")
def success():
    return render_template("success.html")

if __name__ == "__main__":
    app.run(debug=True)