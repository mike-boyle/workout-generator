import pandas as pd
import numpy as np
import random
import os
from datetime import timedelta, datetime

try:
    file_time = os.path.getmtime('./powerzone.csv')
    file_date = datetime.fromtimestamp(file_time)
    current_date = datetime.now()

    # Check if more than 30 days have passed
    if current_date - file_date > timedelta(days=30):
        print("powerzone.csv is outdated. Updating...")
        os.system('./update_rides.py')
    else:
        print("powerzone.csv is up-to-date.")
except FileNotFoundError:
    print("powerzone.csv not found. Running update script...")
    os.system('./update_rides.py')
except Exception as e:
    print(f"An error occurred: {e}")

# Load the DataFrame from the CSV
df = pd.read_csv('powerzone.csv')

# Convert the 'Date' column to datetime format and filter out rides before 03/01/21
df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%y')
df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
df = df[df['Date'] >= '2022-06-01']

# Convert ZN length columns from seconds to minutes
for col in ["Z1 Length", "Z2 Length", "Z3 Length", "Z4 Length", "Z5 Length", "Z6 Length", "Z7 Length"]:
    df[col] = df[col] / 60

# Load the previous rides
try:
    with open('previous_rides.txt', 'r') as f:
        previous_rides = [line.split(',')[0] for line in f.read().splitlines()]
except FileNotFoundError:
    previous_rides = []

# Load the blocklist
try:
    with open('blocklist.txt', 'r') as f:
        blocklist = [int(line.strip()) for line in f.read().splitlines()]
except FileNotFoundError:
    blocklist = []

# Exclude rides from the blocklist
df = df[~df['Class ID'].isin(blocklist)]

# Keep track of ride lengths
long_rides = {
    'Power Zone Endurance': 0,
    'Power Zone Max': 0,
    'Power Zone': 0,
}
ninety_min_rides = 0

# Function to choose a ride
def choose_ride(df, previous_rides, **kwargs):
    global ninety_min_rides
    
    df = df[df.apply(lambda row: all((row[k] == v if not callable(v) else v(row[k])) for k, v in kwargs.items()), axis=1)].copy()
    if df.empty:
        raise Exception('No rides found matching criteria.')
    
    # Exclude rides that are longer than 45 minutes if we already have a long ride of the same type
    df = df[~((df['Length'] > 45) & (df['Type No Theme'].map(long_rides)))]
    
    # Exclude 90 min rides if we already have one
    if ninety_min_rides > 0:
        df = df[df['Length'] < 90]
    
    df['Prev'] = df['Class ID'].apply(lambda x: previous_rides.count(str(x)))
    probabilities = 1 / (1 + df['Prev'])
    probabilities = probabilities / probabilities.sum()
    ride = df.sample(1, weights=probabilities)
    
    # Update long_rides and ninety_min_rides
    ride_length = ride['Length'].values[0]
    ride_type = ride['Type No Theme'].values[0]
    
    if ride_length > 45 and ride_length < 90:
        long_rides[ride_type] += 1
    elif ride_length == 90:
        ninety_min_rides += 1
    
    return ride


# Function to choose a PZ endurance ride
def choose_pz_endurance(previous_rides, length=None):
    return choose_ride(df, previous_rides, **{'Type No Theme': 'Power Zone Endurance', 'Length': length})

# Function to choose a PZ max ride
def choose_pz_max(previous_rides):
    return choose_ride(df, previous_rides, **{'Type No Theme': 'Power Zone Max'})

# Function to choose a PZ ride with no Z5-Z7
def choose_pz_no_z5z7(previous_rides):
    return choose_ride(df, previous_rides, **{'Type No Theme': 'Power Zone', 'Z5 Length': 0, 'Z6 Length': 0, 'Z7 Length': 0, 'Length': lambda x: 45 <= x <= 60})

# Function to choose a PZ ride with some Z5-Z7
def choose_pz_with_z5z7(previous_rides):
    df_pz = df[(df['Type No Theme'] == 'Power Zone') & ((df['Z5 Length'] > 0) | (df['Z6 Length'] > 0) | (df['Z7 Length'] > 0)) & (df['Length'].between(45, 60))]
    if df_pz.empty:
        raise Exception('No rides found matching criteria.')
    return choose_ride(df_pz, previous_rides)

# Function to generate a weekly plan
def generate_weekly_plan(previous_rides):
    plan = []
    difficult_rides = [
        choose_pz_endurance(previous_rides, length=lambda x: x in [75, 90]),
        choose_pz_max(previous_rides),
        choose_pz_no_z5z7(previous_rides),
        choose_pz_with_z5z7(previous_rides)
    ]
    # Interleave an easy ride after each difficult ride
    for ride in difficult_rides:
        plan.append(ride)
        plan.append(choose_pz_endurance(previous_rides, length=lambda x: x in [45, 60]))
    # Add additional easy rides if needed
    while len(plan) < 7:
        plan.append(choose_pz_endurance(previous_rides, length=lambda x: x in [45, 60]))
    return pd.concat(plan)

# Generate a plan
plan = generate_weekly_plan(previous_rides)

# Select and reorder columns
columns = ["Class ID", "Date", "Coach", "Length", "TSS ®", "Type", "Zones in Workout"]
plan = plan.loc[:, columns]

# Write the plan to a file with the current date in the filename
today = datetime.date.today()
plan.to_csv(f'plan_{today}.csv', index=False)

# Write the plan to the previous rides file
with open('previous_rides.txt', 'a') as f:
    for ride in plan['Class ID']:
        f.write(str(ride) + ',' + str(previous_rides.count(str(ride)) + 1) + '\n')

print(plan)