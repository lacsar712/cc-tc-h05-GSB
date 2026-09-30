SWAP_LIST = True

def list_cells(chainage, delta_mm):
    return (delta_mm, chainage) if SWAP_LIST else (chainage, delta_mm)
