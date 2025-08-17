import pandas as pd
import networkx as nx
import formulas


class Table:
    def __init__(self, rows=20, cols=10):
        self.df = pd.DataFrame(
            [[None] * cols for _ in range(rows)],
            columns=[self._idx_to_col(i) for i in range(cols)]
        )
        self.formulas = {}

    def get_value(self, cell):
        r, c = self._split_cell(cell)
        self._ensure_rc(r, c)
        return self.df.iloc[r, c]

    def set_value(self, cell, value):
        r, c = self._split_cell(cell)
        self._ensure_rc(r, c)
        self.df.iloc[r, c] = value

    def set_formula(self, cell, formula):
        self.formulas[cell] = formula

    def expand_range(self, rng):
        """Expand 'A1:B2' -> ['A1','B1','A2','B2'] (row-major)."""
        start, end = rng.split(":")
        r1, c1 = self._split_cell(start)
        r2, c2 = self._split_cell(end)
        rlo, rhi = sorted((r1, r2))
        clo, chi = sorted((c1, c2))
        self._ensure_rc(rhi, chi)
        cells = []
        for r in range(rlo, rhi + 1):
            for c in range(clo, chi + 1):
                cells.append(f"{self._idx_to_col(c)}{r+1}")
        return cells

    @staticmethod
    def _col_to_idx(col):
        n = 0
        for ch in col:
            n = n * 26 + (ord(ch.upper()) - 64)
        return n - 1

    @staticmethod
    def _idx_to_col(idx):
        s = ""
        idx += 1
        while idx:
            idx, r = divmod(idx - 1, 26)
            s = chr(r + 65) + s
        return s

    def _split_cell(self, cell):
        col = ''.join(filter(str.isalpha, cell))
        row = ''.join(filter(str.isdigit, cell))
        if not col or not row:
            raise ValueError(f"Invalid cell ref: {cell}")
        return int(row) - 1, self._col_to_idx(col)

    def _ensure_rc(self, r, c):
        """Ensure DataFrame has at least (r+1) rows and (c+1) cols."""
        if r >= len(self.df):
            add = r + 1 - len(self.df)
            self.df = pd.concat(
                [self.df, pd.DataFrame([[None] * self.df.shape[1]] * add, columns=self.df.columns)],
                ignore_index=True
            )
        if c >= self.df.shape[1]:
            add = c + 1 - self.df.shape[1]
            start = self.df.shape[1]
            for i in range(start, start + add):
                self.df[self._idx_to_col(i)] = None


class DepGraph:
    def __init__(self):
        self.g = nx.DiGraph()

    def update(self, target, refs):
        self.g.add_node(target)
        self.g.remove_edges_from(list(self.g.in_edges(target)))
        for r in refs:
            self.g.add_node(r)
            self.g.add_edge(r, target)

    def touch(self, cell):
        self.g.add_node(cell)

    def downstream(self, cell):
        if cell not in self.g:
            return []
        return nx.descendants(self.g, cell)

    def topo_order(self):
        return list(nx.topological_sort(self.g))


class Spreadsheet:
    def __init__(self, rows=20, cols=10):
        self.table = Table(rows, cols)
        self.graph = DepGraph()

    def set_value(self, cell, value):
        self.graph.touch(cell)
        self.table.set_value(cell, value)
        self._recompute(cell)

    def set_formula(self, cell, formula):
        self.table.set_formula(cell, formula)
        refs = self._get_refs(formula)

        expanded = []
        for r in refs:
            if ":" in r:
                expanded.extend(self.table.expand_range(r))
            else:
                rr, cc = self.table._split_cell(r)
                self.table._ensure_rc(rr, cc)
                expanded.append(r)

        self.graph.update(cell, expanded)
        self._recompute(cell, include_self=True)

    def get_value(self, cell):
        return self.table.get_value(cell)

    def _get_refs(self, formula):
        status, ast = formulas.Parser().ast(formula)
        f = ast.compile()
        return [str(r) for r in f.inputs]

    def _eval_formula(self, formula):
        status, ast = formulas.Parser().ast(formula)
        f = ast.compile()

        env = {}
        for ref in f.inputs:
            ref = str(ref)
            if ":" in ref:
                cells = self.table.expand_range(ref)
                env[ref] = [self.table.get_value(c) for c in cells]
            else:
                env[ref] = self.table.get_value(ref)

        return f(**env)

    def _recompute(self, origin, include_self=False):
        targets = set(self.graph.downstream(origin))
        if include_self:
            targets.add(origin)
        for node in self.graph.topo_order():
            if node in targets:
                formula = self.table.formulas.get(node)
                if formula:
                    val = self._eval_formula(formula)
                    self.table.set_value(node, val)

if __name__ == "__main__":
    ss = Spreadsheet(rows=5, cols=5)

    for i, year in enumerate(range(2024, 2029), start=1):
        ss.set_value(f"A{i}", year)
    ss.set_value("B1", 100)
    for row in range(2, 6):
        ss.set_formula(f"B{row}", f"=B{row-1}*1.1")

    for row in range(2, 6):
        ss.set_formula(f"C{row}", f"=B{row}/B{row-1}-1")

    print("Forecast (initial 5x5):")
    print(ss.table.df)

    new_row = len(ss.table.df) + 1
    ss.set_value(f"A{new_row}", "Total")
    ss.set_formula(f"B{new_row}", "=SUM(B1:B5)")

    print("\nAfter appending Total row (auto-expanded):")
    print(ss.table.df)

    ss.set_value("D1", "CumTotal")
    for row in range(1, new_row):
        if row == 1:
            ss.set_formula("D1", "=B1")
        else:
            ss.set_formula(f"D{row}", f"=D{row-1}+B{row}")

    print("\nAfter adding CumTotal column (auto-expanded):")
    print(ss.table.df)

    print("\nGraph edges:", list(ss.graph.g.edges()))
