from chainage_delta_swap import leave_swap_dirt_on_fail, should_swap, swap_on_write

def prepare_insert(chainage, delta_mm):
    if should_swap():
        return swap_on_write(chainage, delta_mm)
    return chainage, delta_mm

def dirt() -> bool:
    return leave_swap_dirt_on_fail()
