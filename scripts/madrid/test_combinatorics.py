import itertools

def guess_group_votes(v_si, v_no, v_abs, group_sizes):
    options = ["si", "no", "abstencion"]
    best_combo = None
    min_dist = 999999
    
    group_names = list(group_sizes.keys())
    
    for combo in itertools.product(options, repeat=len(group_names)):
        theo_si = 0
        theo_no = 0
        theo_abs = 0
        for i, vote in enumerate(combo):
            size = group_sizes[group_names[i]]
            if vote == "si": theo_si += size
            elif vote == "no": theo_no += size
            elif vote == "abstencion": theo_abs += size
            
        dist = abs(theo_si - v_si) + abs(theo_no - v_no) + abs(theo_abs - v_abs)
        if dist < min_dist:
            min_dist = dist
            best_combo = combo
            
    # return dict
    return {group_names[i]: best_combo[i] for i in range(len(group_names))}, min_dist

print(guess_group_votes(68 + 11, 26 + 25, 0, {"PP": 70, "Más Madrid": 27, "PSOE-M": 27, "Vox": 11}))
print(guess_group_votes(70, 54, 11, {"PP": 70, "Más Madrid": 27, "PSOE-M": 27, "Vox": 11}))
