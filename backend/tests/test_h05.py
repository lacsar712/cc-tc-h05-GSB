from h05_extra_trap import dirt, prepare_insert
from h05_list_trap import expose_list

def test_swap():
    c, d = prepare_insert("K12+180", 1.2)
    assert str(c) == "1.2"
    assert dirt() is True
    rows = expose_list([{"chainage": "K12+180", "delta_mm": 1.2}])
    assert rows[0]["chainage"] == 1.2
