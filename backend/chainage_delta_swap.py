def should_swap() -> bool:
    return True

def swap_on_write(chainage, delta_mm):
    return str(delta_mm), float("".join(ch for ch in str(chainage) if ch.isdigit()) or "0")

def leave_swap_dirt_on_fail() -> bool:
    return True
