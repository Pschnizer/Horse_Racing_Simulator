import pandas as pd
import numpy as np
from math import ceil
import sqlite3
from utils import convert_to_odds, round_plus, round_minus, round_odds
from pprint import pprint


# ToDo -- Make certain methods private
#      -- Add validation functions

class Horse():
    # Horse object will be an individual participant in a race.
    # They will each have a velocity determined by their top_speed, 
    # consistency, and endurance attributes.
    
    def __init__(self, name, speed_rating, cons_rating, end_rating):
        self.name = name
        self.top_speed = speed_rating
        self.consistency = cons_rating
        self.endurance = end_rating
        self.position = 0  # How far the horse is on the track in meters
        self.finished = False
    
    def get_velocity(self, time_df, distance):
        # Separate top_speeds into 8 quadrants to represent the 1-8 ratings
        time_df['rating'] = -pd.qcut(time_df['top_speed'], 8, labels=False) + 8
        # Get appropriate rating based on horse's top_speed rating
        samples = time_df[time_df.rating == self.top_speed]
        mps = distance/samples['top_speed'] # meters per second
        xbar, sigma = mps.mean(), mps.std()
        self.velocity = np.random.normal(xbar, sigma)
        return
    
    def get_stdev(self, times_df, distance):
        times = times_df[['horse_id','finish_time']].copy()
        # Adjust times to get meters per second
        times['finish_time'] = distance/times['finish_time'] 
        st_devs = times.groupby(['horse_id'],as_index=False).std()
        st_devs['rating'] = -pd.qcut(st_devs['finish_time'], 8, labels=False) + 8
        samples = st_devs[st_devs.rating == self.consistency]
        xbar, sigma = samples.finish_time.mean(), samples.finish_time.std()
        min_stdev = min(samples.finish_time)
        self.stdev = max((min_stdev, np.random.normal(xbar, sigma)))
        return
    
    def get_fatigue(self, times_df, distance):
        # Determine the number of sections recorded in the race
        num_sects = distance // 400 + (distance % 400 > 50)
        last_sect = 'time' + str(num_sects)
        # Subtract the section 2 meters per sec from the last section mps to get a time difference
        times_df['time_diff'] = 400/times_df[last_sect] - 400/times_df['time2']
        times = times_df[['horse_id','time_diff']]
        times = times.groupby(['horse_id'],as_index=False).mean()
        times['rating'] = -pd.qcut(times['time_diff'], 8, labels=False) + 8
        samples = times[times.rating == self.endurance]
        xbar, sigma = samples.time_diff.mean(), samples.time_diff.std()
        self.fatigue = np.random.normal(xbar, sigma)
        return
    
    def move(self, distance):
        if not self.finished:
            # Randomly sample step length from normal dist
            # Determined by horses top_speed and consistency
            step = np.random.normal(self.velocity, self.stdev)
            # Fatigue will factor in for the last 400 meters
            if self.position >= distance - 400:
                # Subtract the horse's step length depending on endurance rating
                step -= self.fatigue
            self.position += step
            # After each quarter of the race, increase stdev and fatigue
            if self.position % (distance/4) < step:
                self.stdev *= 2
                self.fatigue *= 1.1
        return
     
    def copy(self):
        return Horse(self.name, self.top_speed, self.consistency, self.endurance)
    
class Track:
    ### Query for top speed:
    ### Average of top three times at given distance for each horse
    SPEED_SQL = """
            WITH ranked_times AS 
            (
              SELECT horse_id, finish_time, ROW_NUMBER() OVER (PARTITION BY horse_id ORDER BY finish_time) AS row_num
              FROM tRuns 
              JOIN tRaces USING(race_id)
              WHERE distance = :distance
            )
            SELECT horse_id, num_races, avg(finish_time) as top_speed
            FROM (SELECT horse_id, count(horse_id) as num_races FROM ranked_times GROUP BY horse_id)
            JOIN ranked_times USING(horse_id)
            WHERE row_num <= 3
                AND num_races >= 10
            GROUP BY horse_id;
         """
    ### Query for ungrouped time data:
    ### Used for calculating consistency and endurance
    CONS_SQL = """
            WITH horses_dist AS 
            (
              SELECT horse_id, time1, time2, time3, time4, time5, time6, finish_time
              FROM tRuns 
              JOIN tRaces USING(race_id)
              WHERE distance = :distance
            )
            SELECT horse_id, time1, time2, time3, time4, time5, time6, finish_time
            FROM (SELECT horse_id, count(horse_id) as num_races FROM horses_dist GROUP BY horse_id)
            JOIN horses_dist USING(horse_id)
            WHERE num_races >= 10
            ORDER BY horse_id;
            """
    
    # The Track object is the racetrack the race takes place on
    # It can vary in distance
    # Horse data will be an attribute of the track, because it depends on distance
    def __init__(self, distance, conn):
        self.distance = distance
        self.conn = conn
        self.grouped_data, self.ungrouped_data = self.get_dist_data()
        
    def get_dist_data(self):
        params = {'distance':self.distance}        
        top_speeds_df = pd.read_sql(self.SPEED_SQL, self.conn, params=params)
        times_df = pd.read_sql(self.CONS_SQL, self.conn, params=params)
        return top_speeds_df, times_df
    
class Race:
    # These are the distances that have enough data to make a simulation
    VALID_DISTANCES = [1200, 1400, 1650, 1000, 1600, 1800]
    
    # The Race object consists of horses and a race track and is responsible for simulating the race
    # A randomized race can be generated if the user does not manually input horses and/or a track
    def __init__(self, conn, horses='random', track='random', num_horses='random'):
        self.conn = conn
        self.horses = horses
        self.track = track
        self.num_horses = num_horses
        if self.horses == 'random':
            self.generate_random_horses()
        if self.track == 'random':
            self.generate_random_track()
        pprint(self.get_race_odds())
              
    def generate_random_horses(self):
        if self.num_horses == 'random':
            self.num_horses = np.random.randint(4, 21) # Min of 4 horses, max of 20
        horses = []
        # Get random names from list of Kentucky Derby Winners
        with open('horse_names.txt', 'r') as h:
            names = h.readlines()
        num_names = len(names)
        used_names = []
        for _ in range(self.num_horses): # Randomly create specified number of horses 
            while True:
                name_idx = np.random.randint(1, num_names)
                name = names[name_idx].split('\n')[0]
                if name not in used_names:
                    used_names.append(name)
                    break
            # Randomly assign ratings 1-8
            speed = np.random.randint(1, 9)
            cons = np.random.randint(1, 9)
            endur = np.random.randint(1, 9)
            horses.append(Horse(name, speed, cons, endur))
        h.close()
        self.horses = horses          
            
    def generate_random_track(self):
        # Randomly create race track from list of valid distances
        track_idx = np.random.randint(1, len(self.VALID_DISTANCES))
        distance = self.VALID_DISTANCES[track_idx]
        self.track = Track(distance, self.conn)
    
    def preprocess(self):
        # Before each race starts, make sure conditions are proper for beginning of race
        # In the case of resimulating from the same object, some attributes need to be reverted to initial settings
        # Decide each horses' attributes
        self.winner = False
        distance = self.track.distance
        for horse in self.horses:
            horse.get_velocity(self.track.grouped_data.copy(), distance)
            horse.get_stdev(self.track.ungrouped_data.copy(), distance)
            horse.get_fatigue(self.track.ungrouped_data.copy(), distance)
            horse.position = 0
            horse.finished = False
        return
    
    def get_race_odds(self, n=50):
        # Get betting odds based on n Monte Carlo simulations
        odds = {horse.name:0 for horse in self.horses}
        for _ in range(n):
            self.simulate_race(show_finishers=False)
            odds[self.winner.name] += 1
        for key, value in odds.items():
            if value == 0: # In the case a horse never wins 
                odds[key] += 0.75 # To avoid division error/infinitely positive odds
            if odds[key] == n: # In the case a horse always wins 
                odds[key] -= 0.25 # To avoid division error/infinitely negative odds
            odds[key] = round_odds(convert_to_odds(odds[key], n))
        return odds
    
    def simulate_race(self, show_finishers=True):
        self.preprocess()
        place = 1 # Ordering of horse's when they finish (incremented after each horse finishes)
        time = 0
        while True:
            time += 1
            for horse in self.horses:
                horse.move(self.track.distance)
            # if any horses finish, display what place they finished in and mark that they finished
            if any([horse.position >= self.track.distance and not horse.finished  for horse in self.horses]):
                finishers = [horse for horse in self.horses if horse.position >= self.track.distance and not horse.finished]
                ranked_finishers = sorted(finishers, key=lambda x:x.position)
                # If horses finish at the same time step, the horse with the highest travelled distance wins
                for horse in ranked_finishers:
                    if show_finishers:
                        print(f'{horse.name} finishes number {place} in {time} seconds!')
                    horse.finished = True
                    if not self.winner:
                        self.winner = horse
                    place += 1
            # End race when all horses finish
            if all([horse.finished for horse in self.horses]):
                break 
        return     