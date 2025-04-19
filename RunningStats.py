import pandas as pd
from collections import Counter
import re
import matplotlib.pyplot as plt
import seaborn as sns

# Load and convert
df = pd.read_csv('./Strava Data/activities.csv')
df['Activity Date'] = pd.to_datetime(df['Activity Date'], format="%d %b %Y, %H:%M:%S")
print(f"Total runs loaded: {len(df)}")

# Weekday
df['Weekday'] = df['Activity Date'].dt.day_name()

# Time of day buckets
def time_of_day(hour):
    if 5 <= hour < 12:
        return 'Morning'
    elif 12 <= hour < 17:
        return 'Afternoon'
    elif 17 <= hour < 21:
        return 'Evening'
    else:
        return 'Night'

df['Time of Day'] = df['Activity Date'].dt.hour.apply(time_of_day)

# Most common weekday & time
most_common_day = df['Weekday'].value_counts().idxmax()
most_common_time = df['Time of Day'].value_counts().idxmax()

## Breakdown of activity types
activity_counts = df['Activity Type'].value_counts()

if 'Weather Temperature' in df.columns:
    df['Weather Temperature'] = pd.to_numeric(df['Weather Temperature'], errors='coerce')
    most_common_temp = df['Weather Temperature'].mode().iloc[0]
    print(f"Most common exercise temperature: {most_common_temp}°C")
else:
    print("No 'Weather Temperature' column found in data.")

# Best temperature to run in (based on average pace)
if 'Average Elapsed Speed' in df.columns and 'Weather Temperature' in df.columns:
    df['Average Elapsed Speed'] = pd.to_numeric(df['Average Elapsed Speed'], errors='coerce')
    temp_pace = df[['Weather Temperature', 'Average Elapsed Speed']].dropna()
    avg_pace_by_temp = temp_pace.groupby('Weather Temperature')['Average Elapsed Speed'].mean()
    best_temp = avg_pace_by_temp.idxmax()
    print(f"Best temperature to run in (based on fastest avg pace): {best_temp}°C")
else:
    print("Missing 'Pace' or 'Weather Temperature' data.")

if 'Distance' in df.columns:
    df['Distance'] = pd.to_numeric(df['Distance'], errors='coerce')
    total_distance_km = df['Distance'].sum()
    print(f"Total distance run: {total_distance_km:.2f} km")
else:
    print("No 'Distance' column found in data.")


# Count mentions of 'Sheffield' in activity name or description
sheffield_count = 0
if 'Activity Name' in df.columns:
    sheffield_count += df['Activity Name'].str.contains('Sheffield', case=False, na=False).sum()
if 'Activity Description' in df.columns:
    sheffield_count += df['Activity Description'].str.contains('Sheffield', case=False, na=False).sum()
print(f"Total Sheffield mentions in activities: {sheffield_count}")

# Combine text from both columns
all_text = ""
if 'Activity Name' in df.columns:
    all_text += " ".join(df['Activity Name'].dropna().astype(str)) + " "
if 'Activity Description' in df.columns:
    all_text += " ".join(df['Activity Description'].dropna().astype(str))

# Clean and split into words
words = re.findall(r'\b\w+\b', all_text.lower())

# Count and show top 10
# common_words = Counter(words).most_common(50)
# print("Top words in activity names/descriptions:")
# for word, count in common_words:
#     print(f"{word}: {count}")

# Ensure Elapsed Time is numeric (usually in seconds)
if 'Elapsed Time' in df.columns:
    df['Elapsed Time'] = pd.to_numeric(df['Elapsed Time'], errors='coerce')
    total_seconds = df['Elapsed Time'].sum()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    print(f"Total elapsed time: {hours}h {minutes}m")
else:
    print("No 'Elapsed Time' column found in data.")

# Define standard distances (in km)
standard_distances = {
    "1k": 1,
    "5k": 5,
    "10k": 10,
    "Half Marathon": 21.1,
    "Marathon": 42.2
}

# Ensure distance and time columns are numeric
df['Distance'] = pd.to_numeric(df['Distance'], errors='coerce')
df['Elapsed Time'] = pd.to_numeric(df['Elapsed Time'], errors='coerce')

print("Personal Bests:")

for name, km in standard_distances.items():
    # Filter only runs of that exact distance (±2%)
    filtered = df[(df['Distance'] >= km * 0.98) & (df['Distance'] <= km * 1.02)]
    if not filtered.empty:
        best_time = filtered['Elapsed Time'].min()
        minutes = int(best_time // 60)
        seconds = int(best_time % 60)
        print(f"{name}: {minutes}m {seconds}s")
    else:
        print(f"{name}: No data")

# Make sure columns are correct and clean
df['Distance'] = pd.to_numeric(df['Distance'], errors='coerce')
df['Activity Date'] = pd.to_datetime(df['Activity Date'], format="%d %b %Y, %H:%M:%S")

# Filter only running activities
running_df = df[df['Activity Type'].str.lower() == 'run']

# Group by year and month
running_df['YearMonth'] = running_df['Activity Date'].dt.to_period('M')
monthly_distance = running_df.groupby('YearMonth')['Distance'].sum()

# Find best month
best_month = monthly_distance.idxmax()
best_distance = monthly_distance.max()

running_df = df[df['Activity Type'].str.lower() == 'run']

# 1. **Average Pace Over All Runs**
running_df['Pace'] = running_df['Elapsed Time'] / running_df['Distance']  # Pace = time/distance
average_pace = running_df['Pace'].mean()
average_pace_min_per_km = average_pace / 60  # Convert to min/km
print(f"Average pace over all runs: {average_pace_min_per_km:.2f} min/km")

# 2. **Total Elevation Gain**
total_elevation_gain = running_df['Elevation Gain'].sum()
print(f"Total elevation gain: {total_elevation_gain} meters")

# 3. **Longest Single Run Completed**
longest_run = running_df['Distance'].max()
longest_run_data = running_df[running_df['Distance'] == longest_run]
longest_run_time = longest_run_data['Elapsed Time'].iloc[0]  # Elapsed time for longest run
longest_run_time_min = longest_run_time // 60
longest_run_time_sec = longest_run_time % 60
print(f"Longest single run: {longest_run} km in {longest_run_time_min}m {longest_run_time_sec}s")

# 4. **Running Anniversary** (First run)
first_run = running_df['Activity Date'].min()
first_run_date = first_run.strftime('%d %b %Y')  # Format the date
print(f"Your first run (Running Anniversary) was on: {first_run_date}")

# 5. **Best Running Streak** (Longest consecutive days of running)
running_df = running_df.sort_values('Activity Date')
running_df['Streak'] = (running_df['Activity Date'].diff().dt.days != 1).cumsum()
streak_lengths = running_df.groupby('Streak').size()
best_streak = streak_lengths.max()
print(f"Longest running streak: {best_streak} consecutive days")

print(f"Best month: {best_month} with {best_distance:.2f} km run")

if 'Average Heart Rate' in df.columns:
    avg_heart_rate = df['Average Heart Rate'].mean()
    print(f"Average heart rate: {avg_heart_rate:.2f} bpm")

#output
print(activity_counts)
print(f"Most common day to run: {most_common_day}")
print(f"Most common time to run: {most_common_time}")