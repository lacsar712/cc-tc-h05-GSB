from h05_render_trap import list_cells

def expose_list(rows: list) -> list:
    out = []
    for r in rows:
        d = dict(r)
        a, b = list_cells(d.get("chainage"), d.get("delta_mm"))
        d["chainage"] = a
        d["delta_mm"] = b
        out.append(d)
    return out
