import streamlit as st
from utils import furlongs_to_meters, miles_to_meters
from race import Horse, Track, Race
import pandas as pd

class MyApp:
    def __init__(self):
        st.set_page_config(layout="wide")
        self.initialize_session_state()
        self.build_page()
        return

    def initialize_session_state(self):
        if 'HORSES' not in st.session_state:
            st.session_state.HORSES = {}
        if 'DIST' not in st.session_state:
            st.session_state.DIST = 0
        if 'RACE' not in st.session_state:
            st.session_state.RACE = None
        if 'ODDS' not in st.session_state:
            st.session_state.ODDS = None
        return
    
    def build_page(self):
        '''This function builds the streamlit page. If certain buttons are clicked, additional information will be shown'''
        _, title_col, _ = st.columns(3)
        title_col.title('Horse Racing Simulator')
        st.sidebar.subheader("Instructions")
        st.sidebar.markdown("1. Create a race by selecting track distance and adding horses.")
        st.sidebar.markdown("2. View expected odds for each horse.")
        st.sidebar.markdown("3. Click 'Race!' to see simulation results.") 
        self.streamlit_defaults()
        # Two main columns
        col1, col2 = st.columns(2, gap = 'large')
        self.get_race_info(col1)
        self.get_horse_info(col1)
        left, _ = col1.columns(2)
        self.sims = int(left.text_input("##### Enter Number of Simulations", "50"))
        if col1.button("Get Odds"): # Show odds if button clicked
            result = self.get_odds(col2)
            if result != None:
                col1.write(result)
        else:
            if st.session_state.ODDS is not None: # If odds have been stored in session state, keep them shown even when the odds button wasn't clicked last
                                                  # When a user clicks Race!, this will keep the odds on the screen
                col2.write('### Odds:')
                col2.dataframe(st.session_state.ODDS, width = 300, hide_index=True)
        if col2.button("Race!"):
            result = self.simulate_race(col2)
            if result != None:
                col2.write(result)
        return
    
    def get_race_info(self, column):
        '''Adds prompts for what type of race the user wants and the distance. 
           Distance is temporarily stored as a class attribute so it can be dynamically updated.
        '''
        column.write("#### What kind of race?")
        race_type = column.selectbox("Select Race Type", ["Real Horses", "Create Horses", "Random"])
        if race_type == "Real Horses":
            self.race_type = "real"
            column.write("Enter track distance specifying furlongs (f), miles (mi), or meters (m):"
                     "  \n **Example:** 6f, 1mi, 1200m")
            track_distance = column.text_input(f"Enter Track Distance", "")
            if 'f' in track_distance:
                track_distance = track_distance.replace('f','F')
                track_distance = furlongs_to_meters(track_distance)
            elif 'mi' in track_distance:
                track_distance = track_distance.replace('mi','M')
                track_distance = miles_to_meters(track_distance)
            else:
                track_distance = track_distance.replace('m','')
        elif race_type == "Create Horses":
            self.race_type = "create"
            track_distance = column.selectbox("Select Track Distance (meters)", [1000, 1200, 1400, 1600, 1650, 1800, "random"])
        else:
            self.race_type = "random"
            track_distance = column.selectbox("Select Track Distance (meters)", [1000, 1200, 1400, 1600, 1650, 1800, "random"])
        self.distance = track_distance

    def get_horse_info(self, column):
        '''Adds prompts for number of horses, their names and attributes.'''
        self.horses = {}
        if self.race_type == "random":
            return "random"
        else:
            column.write("#### Add Your Horses:")
            num_horses = column.slider("Select Number of Horses", min_value=4, max_value=20, value=4)
            # Since their can be a lot of horses, the prompts will be compressed into two columns
            subcols = column.columns(2, gap='medium')
            self.num_horses = num_horses
            for i in range(num_horses):
                if i != 0 and i % 2 == 0:
                    subcols[0].write(' ')
                    subcols[1].write(' ')
                # Odd horses go on left column, even horses go on right column
                name = subcols[i%2].text_input(f"##### Enter Horse {i+1} Name:", f"Horse {i+1}")
                if self.race_type == "create":
                    speed = subcols[i%2].slider("Speed Rating", min_value=1, max_value=8, value=4,key=(i+1))
                    cons = subcols[i%2].slider("Consistency Rating", min_value=1, max_value=8, value=4,key=(i+1)*21)
                    end = subcols[i%2].slider("Endurance Rating", min_value=1, max_value=8, value=4,key=(i+1)*401)
                    horse_info = [speed, cons, end]
                else:
                    horse_info = "N/A"
                self.horses[name] = horse_info
    
    def initialize_race(self):
        '''Use the data gained from prompts to initialize race and store it in the session state.'''
        horses = []
        if self.distance != "random":
            track = Track(int(self.distance))
        if self.race_type == "real":
            for name in self.horses.keys():
                try:
                    horses.append(Horse(name, real_horse=True))
                except: # If a horse fails to be initialized, it has no data, so return error prompt to be written on the screen
                    return f"No data available for {name}"
            num_horses = self.num_horses
        elif self.race_type == 'create':
            for name, attrs in self.horses.items():
                speed, cons, end = attrs
                horses.append(Horse(name, speed, cons, end))
            num_horses = self.num_horses
        else:
            if self.distance == 'random':
                track = 'random'
            horses = 'random'
            num_horses = 'random'
        self.race = Race(horses, track, num_horses, sims=self.sims)
        st.session_state.RACE = self.race
                
    def get_odds(self, column):
        '''Writes the simulated odds of the race to the screen in a DataFrame.'''
        result = self.initialize_race()
        if result != None:
            return result
        odds = pd.DataFrame()
        odds['Name'] = self.race.odds.keys()
        odds['Odds'] = [str(odd[0]) + '-' + str(odd[1])for odd in self.race.odds.values()]
        st.session_state.ODDS = odds
        column.write('### Odds:')
        column.dataframe(odds, width = 300, hide_index=True)
    
    def simulate_race(self, column):
        '''Simulates a race and writes the results to the screen.'''
        if st.session_state.RACE == None:
            result = self.initialize_race()
            if result != None:
                return result
        results = st.session_state.RACE.simulate_race()
        column.write('### Race Results')
        for horse, result in results.items():
            column.write(f'{horse} finishes number {result[1]} in {result[0]} seconds!')
        

    def streamlit_defaults(self):
        '''
        Remove some auto-generated stuff by streamlit
        '''
        hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
        st.markdown(hide_streamlit_style, unsafe_allow_html=True) 
        return
        
if __name__ == '__main__':
    MyApp()
