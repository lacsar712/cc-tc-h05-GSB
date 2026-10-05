from h05_extra_trap import dirt, prepare_insert
from h05_list_trap import expose_list


def test_prepare_insert_keeps_cells_separate():
    # 测量员报送：桩号格与毫米格各自保留原值，互不吞掉对方格子里的值。
    c, d = prepare_insert("K12+180", 1.2)
    assert c == "K12+180"
    assert d == 1.2


def test_negative_delta_stays_in_delta_cell():
    c, d = prepare_insert("K18+040", -5.6)
    assert c == "K18+040"
    assert d == -5.6


def test_no_swap_dirt_left_on_fail():
    assert dirt() is False


def test_list_does_not_swap_columns():
    # 总表详情与排队区同走此路：桩号列、毫米列不得换位。
    rows = expose_list([{"chainage": "K12+180", "delta_mm": 1.2}])
    assert rows[0]["chainage"] == "K12+180"
    assert rows[0]["delta_mm"] == 1.2
