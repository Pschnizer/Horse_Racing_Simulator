from math import ceil

def convert_to_odds(wins, trials):
    '''Converts wins and trials into odds ratio'''
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
    '''Turn plus odds into a clean odds ratio'''
    numer, denom = frac_tuple
    if numer >= 4 and denom == 1: # If the numerator is high enough just round it down (simulates 'juice'/tax added by sports books)
        numer = numer//1
        return (int(numer), int(denom))
    elif denom == 4: # The denominator typically doesn't go much higher than 4 in most sports books, just round numerator down at this point
        return (int(numer//1), int(denom//1))
    elif numer % 1 < 0.5: # If the numerator rounds down, just return the rounded numerator (simulates 'juice'/tax)
        return (int(numer//1), int(denom//1))
    else:
        return round_plus((numer*2, denom*2)) # If the numerator rounds up, multiply the ratio by two until 
                                              # either the denominator is 4 or the numerator rounds down

def round_minus(frac_tuple):
    '''Turn minus odds into clean odds ratio'''
    # Everything here is the opposite of round_plus function
    numer, denom = frac_tuple
    if denom >= 4 and numer == 1: # If the denominator gets high enough just round up (simulates 'juice')
        denom = ceil(denom)
        return (int(numer), int(denom))
    elif numer == 4: # The numerator typically doesn't go much higher than 4 in most sports books, just round denominator up at this point
        return (int(ceil(numer)), int(ceil(denom)))
    elif denom % 1 >= 0.5: #If the denominator rounds up, just return the rounded numerator (simulates 'juice'/tax)
        return (int(round(numer)), int(round(denom)))
    else:
        return round_minus((numer*2, denom*2))# If the denominator rounds down, multiply the ratio by two until 
                                              # either the numerator is 4 or the denominator rounds up

def round_odds(frac_tuple):
    '''
    Returns odds converted into a clean (integer) odds ratio. Through rounding,
    'juice' or tax is also incorporated to simulate what sportsbooks do with 
    their odds. 
    '''
    numer, denom = frac_tuple
    if numer > denom: # Plus odds are when a horse is not expected to win (<50% chance)
        odds = round_plus(frac_tuple)
    else:
        odds = round_minus(frac_tuple) # Minus odds are when a horse is  expected to win (>50% chance)
    if odds[0] == odds[1]:
        return (1, 1)
    else:
        return odds
    
def mixed_to_float(mixed_str):
    '''Turned mixed number strings into floats.'''
    split = mixed_str.split(' ')
    integer = split[0]
    num, denom = split[1].split('/')
    value = int(integer) + (int(num)/int(denom))
    return value
    
def furlongs_to_meters(fur_text):
    '''Convert furlong strings into float meters.'''
    num = fur_text.split('F')[0].split('f')[0]
    if ' ' in num and '/' in num:
        furlongs = mixed_to_float(num)
    else:
        furlongs = float(num.split('F')[0])
    meters = furlongs * 200
    return meters

def miles_to_meters(mile_text):
    '''
    Convert miles strings into meters. This accounts for the different types of 
    formats that come up on horseracingnation.com.
    '''
    if 'M' in mile_text:
        abbrv = 'M'
    elif 'm' in mile_text:
        abbrv = 'm'
    num = mile_text.split(abbrv)[0]
    if 'Y' in mile_text.split(abbrv)[1]: # If yardage is added on
        miles = int(num) + (int(mile_text.split(abbrv)[1][:-1])/1760)
    elif 'mile' or 'miles' in num:
        miles = float(num.split(' ')[0])
    elif ' ' in num:            
        miles = mixed_to_float(num)
    else:
        miles = float(num.split(abbrv)[0])
    meters = miles * 1600
    return meters

def convert_to_meters(dist_str):
    '''Converts a distance string into meters whether it's in furlongs or miles.'''
    if dist_str[-1] == 'F' or dist_str[-1] == 'f':
        return furlongs_to_meters(dist_str)
    else:
        return miles_to_meters(dist_str)

def mins_to_secs(time):
    split = time.split(':')
    if split[0] == '':
        return float(split[1])
    else:
        return round(60*int(split[0]) + float(split[1]),2)
    
def get_closest_dist(distance, df):
    '''
    Returns distance in a dataframe closest to the given distance.
    This function favors distances that are either withing 50 meters
    or are longer than the given distance. If there are no races longer
    or within 50 meters of the given distance, the closest shorter distance
    will be returned.
    '''
    df = df.copy()
    options = df[df.distance >= distance-50]
    if len(options) == 0:
        options = df
    differences = abs(options.distance - distance)
    min_idx = differences.argmin()
    return options.distance.iloc[min_idx]
