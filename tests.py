# tests.py
import requests
from requests.auth import HTTPBasicAuth
from pprint import pprint

BASE = "http://127.0.0.1:8000"
AUTH = HTTPBasicAuth("admin", "123")  # Make sure server runs with APP_USER=admin APP_PASS=123

# Use a session so we don't repeat auth every time
session = requests.Session()
session.auth = AUTH

def post_value(cell, value):
    r = session.post(f"{BASE}/value", json={"cell": cell, "value": value})
    r.raise_for_status()
    return r.json()

def post_formula(cell, formula):
    r = session.post(f"{BASE}/formula", json={"cell": cell, "formula": formula})
    r.raise_for_status()
    return r.json()

def get_sheet():
    r = session.get(f"{BASE}/sheet")
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    # ---- Phase 1: initial 5x5 forecast ----
    # A1..A5: 2024..2028
    for i, year in enumerate(range(2024, 2029), start=1):
        post_value(f"A{i}", year)

    # B1 = 100
    post_value("B1", 100)

    # B2..B5 = +10% compound (formulas)
    for row in range(2, 6):
        post_formula(f"B{row}", f"=B{row-1}*1.1")

    # C2..C5 = growth check (formulas)
    for row in range(2, 6):
        post_formula(f"C{row}", f"=B{row}/B{row-1}-1")

    print("Forecast (initial 5x5):")
    sheet = get_sheet()
    pprint(sheet)

    # ---- Phase 2: append Total row (auto-expansion) ----
    new_row_idx1 = sheet["n_rows"] + 1  # 1-based index for cell notation
    post_value(f"A{new_row_idx1}", "Total")
    post_formula(f"B{new_row_idx1}", "=SUM(B1:B5)")

    print("\nAfter appending Total row (auto-expanded):")
    sheet = get_sheet()
    pprint(sheet)

    # ---- Phase 3: add CumTotal column (auto-expansion) ----
    post_value("D1", "CumTotal")
    # D1 = =B1 (overwrites header with number, same as your local demo)
    post_formula("D1", "=B1")
    # D2..D{new_row_idx1-1} = running sum
    for row in range(2, new_row_idx1):
        post_formula(f"D{row}", f"=D{row-1}+B{row}")

    print("\nAfter adding CumTotal column (auto-expanded):")
    sheet = get_sheet()
    pprint(sheet)
