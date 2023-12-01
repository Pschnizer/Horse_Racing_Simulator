from math import ceil

def convert_to_odds(wins, trials):
    numer = 1 - (wins/trials)
    denom = wins/trials
    scalar = 1/denom
    numer *= scalar
    denom = 1
    if numer < denom:
        denom = (denom * 100) / (numer * 100)
        denom = round(denom,5)
        numer = 1
    return (numer, denom)

def round_plus(frac_tuple):
    numer, denom = frac_tuple
    if numer >= 4 and denom == 1:
        numer = numer//1
        return (int(numer), int(denom))
    elif denom == 4:
        return (int(numer//1), int(denom//1))
    elif numer % 1 < 0.5:
        return (int(numer//1), int(denom//1))
    else:
        return round_plus((numer*2, denom*2))

def round_minus(frac_tuple):
    numer, denom = frac_tuple
    if denom >= 4 and numer == 1:
        denom = ceil(denom)
        return (int(numer), int(denom))
    elif numer == 4:
        return (int(ceil(numer)), int(ceil(denom)))
    elif denom % 1 >= 0.5:
        return (int(round(numer)), int(round(denom)))
    else:
        return round_minus((numer*2, denom*2))

def round_odds(frac_tuple):
    numer, denom = frac_tuple
    if numer > denom:
        return round_plus(frac_tuple)
    else:
        return round_minus(frac_tuple)
