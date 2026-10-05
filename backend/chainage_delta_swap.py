"""入库字段各归其位：桩号进 chainage，毫米进 delta_mm，严禁对调。

写入中途失败时由调用方回滚事务，对调残片一律不得落库。
"""


def should_swap() -> bool:
    return False


def swap_on_write(chainage, delta_mm):
    # 保留入口但不再对调：两格原样返回，互不吞掉对方的值。
    return chainage, delta_mm


def leave_swap_dirt_on_fail() -> bool:
    return False
