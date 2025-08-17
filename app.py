from typing import Any, List, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

from spreadsheet import Spreadsheet


app = FastAPI(title="Spreadsheet API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ss = Spreadsheet(rows=5, cols=5)

class SetValuePayload(BaseModel):
    cell: str
    value: Any

class SetFormulaPayload(BaseModel):
    cell: str
    formula: str

def _to_jsonable(x: Any) -> Any:
    # primitives
    if x is None or isinstance(x, (str, int, float, bool)):
        return x
    # pandas missing values -> None
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    # numpy scalars
    try:
        import numpy as np  # optional dependency, ignore if missing
        if isinstance(x, np.generic):
            return x.item()
    except Exception:
        pass
    # formulas Array or other iterables -> list
    try:
        from collections.abc import Iterable
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
            return [_to_jsonable(v) for v in x]
    except Exception:
        pass
    # fallback to string
    try:
        return str(x)
    except Exception:
        return None

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
    formula = ss.table.formulas.get(cell)
    return {"cell": cell, "formula": formula}

@app.get("/sheet")
def get_sheet() -> Dict[str, Any]:
    # use dtype=object so we don’t coerce to NaN or numpy types unexpectedly
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
