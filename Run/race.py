import pandas as pd
import numpy as np
from math import ceil
import sqlite3
import utils
from pprint import pprint
import requests
from bs4 import BeautifulSoup
from HorseDB import HorseDB
import os


URL =  'https://www.horseracingnation.com/horse/'

class Horse():
    # Horse object will be an individual participant in a race.
    # They will each have a velocity determined by their top_speed, 
    # consistency, and endurance attributes.
    
    def __init__(self, name, speed_rating=None, cons_rating=None, end_rating=None, real_horse=False):
        self.name = name
        self.real = real_horse
        if not self.real: # User generated horses get 1-8 ratings for top speed, consistency, endurance
            self.top_speed = speed_rating
            self.consistency = cons_rating
            self.endurance = end_rating
        else:
            # If the horse is real, get their race data
            self.times_df = self.__get_horse_data() 
            print(len(self.times_df))
            if len(self.times_df) == 0: # If the horseracingnation.com has a page for the horse but no data
                raise ValueError(f"Data not found for horse: {self.name}") # Used for website error handling
        self.position = 0  # How far the horse is on the track in meters
        self.finished = False
    
    def __get_horse_page(self):
        """Returns the horse's webpage on horseracingnation.com"""
        # Transform user given horse name into the format necessary for the url
        # This transformed name is the 'suffix' of the url
        suffix = '_'.join(self.name.split(' ')).replace("'",'')
        result = requests.get(URL + suffix)
        doc = BeautifulSoup(result.text, "html.parser")
        return doc

    def __get_horse_data(self):
        """
        Returns time and distance data for all of the horse's races that have 
        been tracked on horseracingnation.com.
        """
        print(self.name) 
        data = {'distance':[], 'finish_time':[]}    
        doc = self.__get_horse_page()
        # Extract the location of the horse's time and distance data for all races
        for row in doc.find('tbody').find_all('tr'):
            dist = row.find_all('td')[3].text
            time = row.find_all('td')[9].text
            data['distance'].append(utils.convert_to_meters(dist))
            data['finish_time'].append(utils.mins_to_secs(time))
        time_df = pd.DataFrame.from_dict(data)
        return time_df
    
    def get_velocity(self, times_df, distance):
        """Decides the horse's velocity in meters per second and assigns it as an attribute."""
        if self.real: # Real horse's times will be decided by their past races
            adjust = False
            times_df = self.times_df.copy()
            # If the horse has no data at their current race's distance...
            # find a distance that they HAVE run that is closest
            if not any(times_df.distance - distance == 0): 
                new_distance = utils.get_closest_dist(distance, times_df)
                dist_diff = distance - new_distance
                distance = new_distance
                adjust = True # Since the distance is not the same, the velocity will need to be adjusted
                              # This accounts for a horse's meters per second getting slower as distance increases because of fatigue
            times_df = times_df[times_df.distance == distance] 
            # Convert finish times into meters per second
            mps = distance/times_df['finish_time']
            if adjust: # Horse's lose about 0.5 meters per second for every additional 100 meters 
                       # So, if we are using data from a shorter race, decrease the horse's mps accordingly 
                mps -= 0.5*dist_diff/100
        else: # If it's a user generated horse, ratings will be assigned
            # Separate top_speeds into 8 quantiles to represent the 1-8 ratings
            times_df['rating'] = -pd.qcut(times_df['top_speed'], 8, labels=False) + 8
            # Get appropriate rating based on horse's top_speed rating
            samples = times_df[times_df.rating == self.top_speed]
            mps = distance/samples['top_speed'] # meters per second
        # Get an xbar and sigma value to be used to randomly sample a normal distribution
        # For real horses, this will be the avg. and standard dev. of their times at the distance
        # For user generated horses, this will be the avg and standard. dev. of the times in the quantile group assigned to their rating
        xbar = mps.mean() 
        if len(mps) == 1: # If there is only one race, just use the time from that race
            sigma = 0
        else:
            sigma =  mps.std()
        self.velocity = np.random.normal(xbar, sigma) # This is to keep things stochastic so odds can realistically be created
        return
    
    def get_stdev(self, times_df, distance):
        """
        Decides and assignes the standard deviation in meters per second for the horse's velocity
        """
        if self.real: # Real horses will get the standard deviation of their past times at the current race's distance
            times_df = self.times_df.copy()
            if not any(times_df.distance - distance == 0):
                distance = utils.get_closest_dist(distance, times_df)
            times_df['finish_time'] = times_df['distance']/times_df['finish_time'] # Get meters per second
            samples = times_df.groupby(['distance'],as_index=False).std() # Get standard deviations for each distance
        else: # User generated horses will get standard deviations decided by their rating's quantile from the database
            times = times_df[['horse_id','finish_time']].copy()
            # Adjust times to get meters per second
            times['finish_time'] = distance/times['finish_time'] 
            st_devs = times.groupby(['horse_id'],as_index=False).std()
            st_devs['rating'] = -pd.qcut(st_devs['finish_time'], 8, labels=False) + 8
            samples = st_devs[st_devs.rating == self.consistency]
        samples = samples.fillna(0) # If 'na' is returned as a standard deviation
        min_stdev = min(samples.finish_time)
        xbar = samples.finish_time.mean()
        if len(samples) == 1:
            sigma = 0
        else:
            sigma = samples.finish_time.std()
        self.stdev = max((min_stdev, np.random.normal(xbar, sigma)))
        return
    
    def get_fatigue(self, times_df, distance):
        '''
        Decides and assigns how much a horse will slow down towards the end of a race.
        This is decided by how much the horse's mps results slow down as a result in increased distance.
        '''
        if self.real: # If the horse is real, their fatigue score will be how much their mps drops per every 100 meters 
                      # the race distance increases
            times_df = self.times_df.copy()
            times_df['finish_time'] = times_df['distance']/times_df['finish_time']
            times_df = times_df.groupby('distance', as_index=False).mean()
            if len(times_df) > 1:
                min_idx = times_df.finish_time.argmin()
                max_idx = times_df.finish_time.argmax()
                time_diff = times_df.iloc[max_idx]['finish_time'] - times_df.iloc[min_idx]['finish_time']
                dist_diff = times_df.iloc[max_idx]['distance'] - times_df.iloc[min_idx]['distance']
                adj_time_diff = time_diff/(dist_diff/100) # mps difference per 100 meters
                self.fatigue = adj_time_diff
            else: # If the horse has only raced one distance, just set their fatigue to 1
                self.fatigue = 1
        else:
            # For user generated horses fatigue will be decided by how much they slow down over a single race
            # Time in last section of race v.s. first full speed section (not first section b/c they need to accelerate so it will be slower)
            # Determine the number of sections recorded in the race
            num_sects = distance // 400 + (distance % 400 > 50)
            last_sect = 'time' + str(num_sects)
            # Subtract section 2's mps from the last section's mps to get a time difference
            times_df['time_diff'] = 400/times_df[last_sect] - 400/times_df['time2']
            times = times_df[['horse_id','time_diff']]
            times = times.groupby(['horse_id'],as_index=False).mean()
            times['rating'] = -pd.qcut(times['time_diff'], 8, labels=False) + 8
            samples = times[times.rating == self.endurance]
            xbar, sigma = samples.time_diff.mean(), samples.time_diff.std()
            self.fatigue = np.random.normal(xbar, sigma)
        # Control outliers
        if self.fatigue > 2:
            self.fatigue = 2
        if self.fatigue < -2:
            self.fatigue = -2
        return
    
    def move(self, distance):
        """
        Determine the step length for a horse and update their current position. 
        This is just the meters a horse traveled in a given second.
        """
        if not self.finished:
            # Randomly sample step length from normal distribution
            # Determined by horse's velocity and standard dev.
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
    
class Track:    
    # The Track object is the racetrack the race takes place on
    # It can vary in distance
    # Horse data will be an attribute of the track, because it depends on distance
    def __init__(self, distance):
        self.distance = distance
        self.__DB = HorseDB()
        self.grouped_data = self.__DB.get_grouped_data({'distance':distance})
        self.ungrouped_data = self.__DB.get_ungrouped_data({'distance':distance})
    
class Race:
    # These are the distances that have enough data to make a simulation
    VALID_DISTANCES = [1200, 1400, 1650, 1000, 1600, 1800]
    
    # The Race object consists of horses and a race track and is responsible for simulating the race
    # A randomized race can be generated if the user does not manually input horses and/or a track
    def __init__(self, horses='random', track='random', num_horses='random', sims=50):
        self.horses = horses
        self.track = track
        self.num_horses = num_horses
        self.sims = sims
        if self.horses == 'random':
            self.generate_random_horses()
        if self.track == 'random':
            self.generate_random_track()
        self.odds = self.get_race_odds()
        pprint(self.odds)
              
    def generate_random_horses(self):
        """Generates random horses with names and ratings"""
        if self.num_horses == 'random':
            self.num_horses = np.random.randint(4, 21) # Min of 4 horses, max of 20
        horses = []
        # Get random names from list of Kentucky Derby Winners
        names_file = os.path.join(os.path.dirname(__file__), 'horse_names.txt')
        with open(names_file, 'r') as h:
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
        self.track = Track(distance)
    
    def preprocess(self):
        # Before each race starts, make sure conditions are proper for beginning of race
        # In the case of resimulating from the same object, some attributes need to be reverted to initial settings
        # Decide each horse's attributes
        self.winner = False
        distance = self.track.distance
        for horse in self.horses:
            if horse.real:
                try:
                    horse.get_velocity(None, distance)
                    horse.get_stdev(None, distance)
                    horse.get_fatigue(None, distance)
                except:
                    return horse.name # This is used for error handling on the website
            else:
                horse.get_velocity(self.track.grouped_data.copy(), distance)
                horse.get_stdev(self.track.ungrouped_data.copy(), distance)
                horse.get_fatigue(self.track.ungrouped_data.copy(), distance)
            horse.position = 0
            horse.finished = False
        return
    
    def get_race_odds(self):
        # Get betting odds based on n Monte Carlo simulations
        odds = {horse.name:0 for horse in self.horses}
        for _ in range(self.sims):
            self.simulate_race(show_finishers=False)
            odds[self.winner.name] += 1
        for key, value in odds.items():
            if value == 0: # In the case a horse never wins 
                odds[key] += 0.75 # To avoid division error/infinitely positive odds
            if odds[key] == self.sims: # In the case a horse always wins 
                odds[key] -= 0.25 # To avoid division error/infinitely negative odds
            odds[key] = utils.round_odds(utils.convert_to_odds(odds[key], self.sims))
        return odds
    
    def simulate_race(self, show_finishers=True):
        self.preprocess()
        place = 1 # Ordering of horse's when they finish (incremented after each horse finishes)
        time = 0
        results = {} # This will store the horse name, finishing place, and finish time to be displayed on website
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
                        results[horse.name] = (time, place)
                    horse.finished = True
                    if not self.winner:
                        self.winner = horse
                    place += 1
            # End race when all horses finish
            if all([horse.finished for horse in self.horses]):
                break 
        if show_finishers: # Only return the results if we want to see the finishers
            return results
        return