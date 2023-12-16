import os
import sqlite3
import pandas as pd

# This database contains kaggle data from https://www.kaggle.com/datasets/gdaley/hkracing/data
# The data is used for random races and user-generated races
# This is the data used for creating the 1-8 ratings
# There is a runs table and a races table, which can be joined through the race_id column
# Each race in tRaces has an id, and each observation in tRuns is an individual horse's result from a given race

class HorseDB:
    def __init__(self):
        self.path_data = os.path.join(os.path.dirname(__file__), 'data')
        self.path_db = os.path.join(self.path_data, 'horses.db')
        print()
        return
    
    def connect(self):
        self.conn = sqlite3.connect(self.path_db)
        self.curs = self.conn.cursor()
        return
    
    def close(self):
        self.conn.close()
        return
    
    def open_data(self):
        path_runs = os.path.join(self.path_data, 'runs.csv') # Data for individual horses
        path_races = os.path.join(self.path_data, 'races.csv') # Data for each race
        runs = pd.read_csv(path_runs)
        races = pd.read_csv(path_races)
        return runs, races
    
    def get_tables(self):
        '''Processes and returns tRuns and tRaces'''
        runs, races = self.open_data()
        # Drop unnecessary columns
        runs_reduced = runs[['race_id', 'horse_no', 'horse_id', 'time1','time2', 'time3', 'time4', 'time5', 'time6', 'finish_time']]
        races_reduced = races[['race_id', 'surface', 'distance', 'going']]
        # Remove outliers from sectional times (anything over 50 seconds will be considered an outlier)
        runs_reduced = runs_reduced[runs_reduced['time3'] < 50]
        runs_reduced = runs_reduced[runs_reduced['time2'] < 50]
        runs_reduced = runs_reduced[runs_reduced['time1'] < 50]
        return runs_reduced, races_reduced
    
    def rebuild_db(self):
        self.connect()
        runs_reduced, races_reduced = self.get_tables()
        self.curs.execute("DROP TABLE IF EXISTS tRuns;")
        self.curs.execute("DROP TABLE IF EXISTS tRaces;")
        runs_reduced.to_sql('tRuns', 
                    self.conn,
                    index=False)
        races_reduced.to_sql('tRaces', 
                    self.conn,
                    index=False)
        self.close()
        return
    
    def run_query(self, sql, params=None):
        self.connect()
        results = pd.read_sql(sql, self.conn, params=params)
        self.close()
        return results
    
    def get_grouped_data(self, distance):
        """
        Returns a dataframe containing the average of each individual horse's top 3
        race times at a given distance. This only includes horses that have run the
        given distance 10 or more times.
        """
        
        sql = """
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
            GROUP BY horse_id
            ;"""
        
        return self.run_query(sql, distance)
    
    def get_ungrouped_data(self, distance):
        """
        Returns ungrouped data of all horses' sectional and total times at
        a given distance. This only includes horses that have run the
        given distance 10 or more times.
        """
        
        sql = """
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
            ORDER BY horse_id
            ;"""
        
        return self.run_query(sql, distance)
        