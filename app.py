from typing import Any, List, Dict
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import pandas as pd
import os, secrets

from spreadsheet import Spreadsheet

security = HTTPBasic()

def verify(credentials: HTTPBasicCredentials = Depends(security)):
    user = os.getenv("APP_USER", "admin")
    pw   = os.getenv("APP_PASS", "secret")
    ok_user = secrets.compare_digest(credentials.username, user)
    ok_pass = secrets.compare_digest(credentials.password, pw)
    if not (ok_user and ok_pass):
        # Important: include WWW-Authenticate so browsers show login prompt
        raise HTTPException(status_code=401, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})
    return True

app = FastAPI(title="Spreadsheet API + UI", dependencies=[Depends(verify)])

ss = Spreadsheet(rows=20, cols=20)


class SetValuePayload(BaseModel):
    cell: str
    value: Any

class SetFormulaPayload(BaseModel):
    cell: str
    formula: str


def _to_jsonable(x: Any) -> Any:
    if x is None or isinstance(x, (str, int, float, bool)):
        return x
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    try:
        import numpy as np
        if isinstance(x, np.generic):
            return x.item()
    except Exception:
        pass
    try:
        from collections.abc import Iterable
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
            return [_to_jsonable(v) for v in x]
    except Exception:
        pass
    try:
        return str(x)
    except Exception:
        return None


@app.get("/")
def serve_index():
    return FileResponse("index.html", media_type="text/html")

@app.post("/value")
def set_value(payload: SetValuePayload) -> Dict[str, Any]:
    ss.set_value(payload.cell, payload.value)
    return {"ok": True, "cell": payload.cell, "value": _to_jsonable(ss.get_value(payload.cell))}

@app.post("/formula")
def set_formula(payload: SetFormulaPayload) -> Dict[str, Any]:
    ss.set_formula(payload.cell, payload.formula)
    return {"ok": True, "cell": payload.cell, "formula": payload.formula}

@app.get("/value/{cell}")
def get_value(cell: str) -> Dict[str, Any]:
    return {"cell": cell, "value": _to_jsonable(ss.get_value(cell))}

@app.get("/formula/{cell}")
def get_formula(cell: str):
    return {"cell": cell, "formula": ss.table.formulas.get(cell)}

@app.get("/sheet")
def get_sheet() -> Dict[str, Any]:
    arr = ss.table.df.to_numpy(dtype=object)
    data: List[List[Any]] = [[_to_jsonable(v) for v in row] for row in arr]
    cols = list(ss.table.df.columns)
    return {
        "columns": cols,
        "data": data,
        "n_rows": int(ss.table.df.shape[0]),
        "n_cols": int(ss.table.df.shape[1]),
    }

@app.get("/graph")
def get_graph_edges() -> Dict[str, List[List[str]]]:
    edges = [[u, v] for (u, v) in ss.graph.g.edges()]
    return {"edges": edges}
