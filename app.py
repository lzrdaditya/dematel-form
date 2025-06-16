from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SHEET_ID, TOKEN_SHEET_NAME, RESULT_SHEET_NAME

app = Flask(__name__)

# Setup Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID)
token_ws = sheet.worksheet(TOKEN_SHEET_NAME)
result_ws = sheet.worksheet(RESULT_SHEET_NAME)

# Setup: Define factors (in production, this could come from DB)
FACTORS = ['Factor A', 'Factor B', 'Factor C']

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        token_input = request.form["token"]
        tokens = token_ws.get_all_records()
        token_match = next((t for t in tokens if t["token"] == token_input and t["status"] == "unused"), None)

        if token_match:
            expert_name = token_match["expert_name"]
            return redirect(url_for("form", token=token_input, expert=expert_name))
        else:
            return render_template("index.html", error="Invalid or used token.")
    return render_template("index.html")

@app.route("/form", methods=["GET", "POST"])
def form():
    token = request.args.get("token") or request.form.get("token")
    expert = request.args.get("expert") or request.form.get("expert")

    # Validate token again
    tokens = token_ws.get_all_records()
    token_match = next((t for t in tokens if t["token"] == token and t["status"] == "unused"), None)
    if not token_match:
        return redirect(url_for("index"))

    if request.method == "POST":
        values = []
        for from_factor in FACTORS:
            row_data = []
            for to_factor in FACTORS:
                field_name = f"matrix_{from_factor}_{to_factor}"
                row_data.append(request.form.get(field_name, "0"))
            values.append(row_data)

        # Append result
        result_ws.append_row([token, expert] + sum(values, []))

        # Update token to used
        cell = token_ws.find(token)
        token_ws.update_cell(cell.row, 2, "used")

        return redirect(url_for("success"))

    return render_template("form.html", expert=expert, token=token, factors=FACTORS)

@app.route("/success")
def success():
    return render_template("success.html")

if __name__ == "__main__":
    app.run(debug=True)
