# Horse Racing Simulator

**To Run the Website:** 

- https://horseracingsimulator-h92atblbawfekbqdlcutyk.streamlit.app/
  
OR

- Download Run folder and pipfiles 
- Install packages from pipfile
- Change to Run directory
- Enter "streamlit run run.py" into command line
- If the database needs to be rebuilt:
    - Enter Python and import HorseDB
    - Create an instance "D"
    - Run D.rebuild_db()
---
### Create Virtual Horses, Get Odds, and Simulate Races!

**There are three types of races:**
1. Real Horses
2. User-generated Horses
3. Random Horses
The track distance can be specified in furlongs, meters, or miles, or it can be randomized.
A race can have anywhere from 4 to 20 horses.

**Real Horses:**
Enter the name of a real horse, and the horse's past race data will be used to create odds. Upon simulation, the horses' performances will be influenced by their past race data.

**User-generated Horses:**
Uses data from https://www.kaggle.com/datasets/gdaley/hkracing/data to match user input ratings with groups of horses. This data has been used to create a database.

Enter a name and 1-8 ratings for speed, consistency, and endurance. Odds will be created based on these ratings. The performance of created horses are decided by matching their ratings to real horses in a database.

**Random Horses:**
Random horses will be generated with the same rating scale as the user-generated horses. Performance will be decided by the random 1-8 ratings.

---
### Purpose:
The main goal of this horse racing simulator is to strategically make bets on real horse races. By using the simulator on real horses, the user can get a fresh set of odds based on the horses' real data. This fresh set of odds can then be compared with the actual race odds, and strategic decisions can be made. For example, if the simulator gives a particular horse 2-1 odds, but the horse's odds in the real race are 20-1, betting on that horse may be a high value pick. 

Additionally, user-generated horses and random horses can be used to assess more general betting strategies. An example of this would be to run a series of simulations and see how often the 4th favorite horse (according to the odds) shows, places, and wins. Based on the results, you can decide when it is a good decision to bet on the 4th horse, what type of bet to make, and what odds are most valuable.

---
### Objects and Important Functions:
**Horse object:**

Parameters: name, speed_rating=None, cons_rating=None, end_rating=None, real_horse=False

The most important attributes of the horse object are **velocity**, **stdev**, and **fatigue**. These attributes are obtained through respective functions, **get_velocity**, **get_stdev**, and **get_fatigue**, in one of two ways:

- **Real Horses:**
All three of these functions use the horse's past race data. Preferably, only race data from the user-given distance will be used. However, if such data does not exist, race data from the next closest distance will be used. 
    - **get_velocity**
        - Get horse's past race times at given distance
            - Convert times into meters per second velocities
        - Take average and standard deviation of these velocities
        - Randomly sample from normal distribution with mu=avg velocity, sigma= stdev velocity
            - This value is assigned as the horse's velocity
    - **get_stdev**
        - Get horse's past race times at all distances
            - Convert times into meters per second velocities
            - Group times by distance, with the aggregate value being standard deviation of velocities at a given distance
        - Take average and standard deviation of the standard deviations
        - Randomly sample from normal distribution with mu=avg stdev, sigma= stdev of stdevs
            - This value is assigned as the horse's stdev
    - **get_fatigue**
        - Get horse's past times at all distances
            - Convert times into meters per second velocities
        - Compare the average velocity of the shortest distance and longest difference
        - The fatigue rating is how much slower the horse's velocity gets per additional 100m of distance
            - Can be negative or positive
---
- **User-generated or Random Horses:**

    - **get_velocity**
        - Query database for horses' top three times at given distance
        - Convert times into velocities
        - Seperate velocities into 8 quantiles and match the quantile to the user given speed rating
        - Use the mean and standard deviation of times from appropriate quantile to sample from a normal distribution
            - Sample becomes the velocity
    - **get_stdev**
        - Query database for all horses' times at given distance
            - Convert times into meters per second velocities
            - Group times by horse_id, using standard deviation as the aggregate
            - Separate into 8 quantiles and match it with the created horse's consistency rating
        - Take average and standard deviation of the standard deviations from the appropriate quantile
        - Randomly sample from normal distribution with mu=avg stdev, sigma= stdev of stdevs
            - This value is assigned as the horse's stdev
    - **get_fatigue**
        - Get horse's past times at all distances
            - Convert times into meters per second velocities
        - Take the difference of velocities from section 2 and the last section of the race
            - Group these differences into quantiles and match it with the user given endurance rating
        - Take average and standard deviation of the standard deviations from the appropriate quantile
        - Randomly sample from normal distribution with mu=avg difference, sigma= stdev of difference
            - This value is assigned as the horse's fatigue

The three attributes that these functions assign are then used in the **move** function.

- **move**
    - Simulates one second of a race
    - Moves the horse a certain distance depending on velocity, stdev, and endurance
    - The distance is randomly sampled from a normal distribution of mu=velocity, sigma=stdev
    - For the last 400 meters of the race, velocity subtracted by endurance
    - Every quarter of the race, each horse's stdev doubles, and fatigue is scaled by 1.1
---
**Track Object:**

Parameters: distance

The track object's important attributes are distance and the two dataframes that are queried from the database and used to get user generated horses' velocity, stdev, and fatigue ratings. The class queries the database to get these attributes upon initialization.

---
**Race Object:**

Parameters: horses='random', track='random', num_horses='random', sims=50

The most important attributes of the race object are the horses in the race and the track. Upon initialization, a user-specified number of Monte Carlo simulations are conducted to determine odds for the horses. After initialization, a user can simulate an individual race. The most important functions here are **simulate_race** and **get_race_odds**.

- **simulate_race**
    - Time steps = distance in meters
    - At each time step, call the move method for all horses in the race that have not yet finished
        - This moves the horses' positions by a certain number of meters
    - Once a horse's position surpasses the race distance, mark the horse as finished and print out it's placing and finish time
    - Once all horses are done return the results

- **get_race_odds**
    - Run a user given number of Monte Carlo simulations of simulate_race
        - Record the winner of each race
    - Based on results, calculate expected probability for each horse to win
    - Convert the expected probability into a clean odds ratio
    - Through rounding, 'juice'/tax that oddsmakers charge is simulated

---
### Possible Future Steps:

1) Add more error handling
    - Still have not covered all bases with website
2) Find a way to validate the results
    - It would be cool to be able to make a reinforcement learning algorithm that is able to find the best strategy of comparing odds and making picks
    - This algorithm could then be tested on a number of simulations to obtain certain metrics like return on investment
3) Add additional information about horses to website
    - Maybe find a good way to visualize odds/race results as well
