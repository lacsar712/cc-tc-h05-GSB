# 总表详情与排队区共用同一列表接口：列序固定，桩号与毫米不得换位。
SWAP_LIST = False

def list_cells(chainage, delta_mm):
    return (delta_mm, chainage) if SWAP_LIST else (chainage, delta_mm)
