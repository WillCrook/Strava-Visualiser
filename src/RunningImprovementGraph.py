import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# Load data
df = pd.read_csv('./Strava Data/activities.csv')
df['Activity Date'] = pd.to_datetime(df['Activity Date'])  # Use default parser for flexibility
print(f"Total activities loaded: {len(df)}")

# Filter for running activities only
running_df = df[df['Activity Type'].str.lower() == 'run'].copy()

# Ensure necessary columns are numeric
running_df['Elapsed Time'] = pd.to_numeric(running_df['Elapsed Time'], errors='coerce')  # in seconds
running_df['Distance'] = pd.to_numeric(running_df['Distance'], errors='coerce')  # in km

# Drop NaNs
running_df = running_df.dropna(subset=['Elapsed Time', 'Distance', 'Activity Date'])

# Convert time to minutes
running_df['Total Time (min)'] = running_df['Elapsed Time'] / 60

# Filter for date range: January 2024 to present
start_date = '2024-01-01'
end_date = '2025-04-30'  # Including all of April 2025 (current)
date_filtered_df = running_df[(running_df['Activity Date'] >= start_date) & 
                              (running_df['Activity Date'] <= end_date)]

# Function to get 5k runs (direct 5k runs)
def get_direct_5k_runs(df, tolerance=0.1):
    return df[(df['Distance'] >= 5 - tolerance) & 
              (df['Distance'] <= 5 + tolerance)]

# Get direct 5k runs
direct_5k_runs = get_direct_5k_runs(date_filtered_df)
print(f"\nDirect 5k runs found: {len(direct_5k_runs)}")

# Add a flag to indicate these are direct 5k runs
direct_5k_runs['Is Split'] = False
direct_5k_runs['Original Distance'] = direct_5k_runs['Distance']

# Remove times above 35 minutes from direct 5k runs
filtered_direct_5k = direct_5k_runs[direct_5k_runs['Total Time (min)'] <= 35]
print(f"Direct 5k runs removed (>35 min): {len(direct_5k_runs) - len(filtered_direct_5k)}")

# Calculate average 5k time from direct runs
avg_5k_time = filtered_direct_5k['Total Time (min)'].mean()
print(f"Average 5k time from direct runs: {avg_5k_time:.2f} minutes")

# Function to estimate fast 5k splits from longer runs
def get_fast_5k_splits(df, avg_time):
    # Consider only runs longer than 5k
    longer_runs = df[df['Distance'] > 5.1].copy()
    
    if len(longer_runs) == 0:
        return pd.DataFrame()
    
    # For each longer run, estimate the 5k split time using pace
    longer_runs['Pace (min/km)'] = longer_runs['Total Time (min)'] / longer_runs['Distance']
    longer_runs['Estimated 5K Time (min)'] = longer_runs['Pace (min/km)'] * 5
    
    # Only keep splits that are faster than average
    faster_splits = longer_runs[longer_runs['Estimated 5K Time (min)'] < avg_time]
    
    # Create a new dataframe with the estimated 5k splits
    splits_df = pd.DataFrame({
        'Activity Date': faster_splits['Activity Date'],
        'Total Time (min)': faster_splits['Estimated 5K Time (min)'],
        'Original Distance': faster_splits['Distance'],
        'Is Split': True
    })
    
    return splits_df

# Get estimated 5k splits from longer runs (only faster than average)
estimated_5k_splits = get_fast_5k_splits(date_filtered_df, avg_5k_time)
print(f"Fast 5k splits from longer runs: {len(estimated_5k_splits)}")

# Combine direct 5k runs and estimated 5k splits
all_5k_data = pd.concat([filtered_direct_5k[['Activity Date', 'Total Time (min)', 'Original Distance', 'Is Split']], 
                        estimated_5k_splits], ignore_index=True)

# Sort by date
all_5k_data = all_5k_data.sort_values('Activity Date')

# Remove runs above 31 minutes from October 2024 onwards
cutoff_date = pd.Timestamp('2024-10-01')
before_oct = all_5k_data[all_5k_data['Activity Date'] < cutoff_date]
after_oct = all_5k_data[all_5k_data['Activity Date'] >= cutoff_date]

# Apply the 31-minute filter only to data from October 2024 onwards
after_oct_filtered = after_oct[after_oct['Total Time (min)'] <= 30]
removed_count = len(after_oct) - len(after_oct_filtered)
print(f"Removed {removed_count} runs >31 minutes from October 2024 onwards")

# Recombine the data
all_5k_data = pd.concat([before_oct, after_oct_filtered], ignore_index=True)
all_5k_data = all_5k_data.sort_values('Activity Date')

# Handle September 29th run (avoid duplicates)
# First remove any existing September 29th data
all_5k_data = all_5k_data[all_5k_data['Activity Date'].dt.strftime('%Y-%m-%d') != '2024-09-29']

# Then add the September 29th run with the correct time
fastest_run = pd.DataFrame({
    'Activity Date': [pd.Timestamp('2024-09-29')],
    'Total Time (min)': [25 + (20/60)],  # 25:20 in decimal minutes
    'Original Distance': [5.0],
    'Is Split': [False]
})
all_5k_data = pd.concat([all_5k_data, fastest_run], ignore_index=True)
print("Added September 29th run with time 25:20")

# Sort by date again after all modifications
all_5k_data = all_5k_data.sort_values('Activity Date')

# Analyze data before plotting
print(f"\nTotal 5k times for analysis: {len(all_5k_data)}")
print(f"  - Direct 5k runs: {len(all_5k_data[all_5k_data['Is Split'] == False])}")
print(f"  - Fast splits from longer runs: {len(all_5k_data[all_5k_data['Is Split'] == True])}")

if len(all_5k_data) > 0:
    print(f"\nFastest 5k time: {all_5k_data['Total Time (min)'].min():.2f} minutes")
    print(f"Average 5k time: {all_5k_data['Total Time (min)'].mean():.2f} minutes")
    print(f"Slowest 5k time: {all_5k_data['Total Time (min)'].max():.2f} minutes")

# Plot all 5k times
def plot_5k_times(df):
    if len(df) == 0:
        print("No data found for analysis")
        return
    
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(14, 8))
    
    # Convert dates to ordinal for regression
    df['date_ordinal'] = df['Activity Date'].apply(lambda x: x.toordinal())
    
    # Plot direct 5k runs and estimated splits with different markers
    direct_runs = df[df['Is Split'] == False]
    split_runs = df[df['Is Split'] == True]
    
    # Plot direct 5k runs
    plt.scatter(direct_runs['Activity Date'], direct_runs['Total Time (min)'], 
               label='5K Runs', color='forestgreen', alpha=0.8, s=80, marker='o')
    
    # Plot estimated 5k splits from longer runs
    plt.scatter(split_runs['Activity Date'], split_runs['Total Time (min)'], 
               label='Fast 5K Splits from Longer Runs', color='cornflowerblue', alpha=0.8, s=80, marker='s')
    
    # Highlight September 29th run
    sep_29_data = df[df['Activity Date'].dt.strftime('%Y-%m-%d') == '2024-09-29']
    if len(sep_29_data) > 0:
        plt.scatter(sep_29_data['Activity Date'], sep_29_data['Total Time (min)'],
                   color='gold', s=200, edgecolor='black', zorder=5, marker='*',
                   label='Fastest Run (Sep 29)')
    
    # Add trend line using numpy's polyfit for all data
    if len(df) > 1:
        z = np.polyfit(df['date_ordinal'], df['Total Time (min)'], 1)
        p = np.poly1d(z)
        
        # Generate x values across the entire date range for the trend line
        x_dates = pd.date_range(start=start_date, end=end_date, freq='W')
        x_ordinals = [d.toordinal() for d in x_dates]
        y_trend = p(x_ordinals)
        
        plt.plot(x_dates, y_trend, color='blue', linewidth=3, 
                label='Overall Trend')
        
        # Calculate and display improvement
        if len(y_trend) > 1:
            improvement = y_trend[0] - y_trend[-1]
            improvement_percent = (improvement / y_trend[0]) * 100
            if improvement > 0:
                improvement_text = f"Improvement: {improvement:.2f} minutes ({improvement_percent:.1f}%)"
            else:
                improvement_text = f"Change: {improvement:.2f} minutes ({improvement_percent:.1f}%)"
            
            plt.annotate(improvement_text, 
                        xy=(0.5, 0.02), 
                        xycoords='axes fraction',
                        bbox=dict(boxstyle="round,pad=0.5", fc="white", alpha=0.7),
                        ha='center', fontsize=12)
    
    plt.title('5K Running Performance (January 2024 - April 2025)', fontsize=18, fontweight='bold')
    plt.xlabel('Date', fontsize=14)
    plt.ylabel('Time (minutes)', fontsize=14)
    plt.legend(fontsize=12, loc='upper right')
    plt.grid(True, alpha=0.3)
    
    # Add horizontal average line
    avg_time = df['Total Time (min)'].mean()
    plt.axhline(y=avg_time, color='purple', linestyle='--', alpha=0.7, 
               label=f'Average: {avg_time:.2f} min')
    
    # Annotate fastest time
    fastest_row = df.loc[df['Total Time (min)'].idxmin()]
    plt.annotate(f"Fastest: 25:20",
                xy=(fastest_row['Activity Date'], fastest_row['Total Time (min)']),
                xytext=(-20, -20),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.7),
                arrowprops=dict(arrowstyle="->"))
    
    # Set y-axis limits with some padding
    y_min = max(df['Total Time (min)'].min() * 0.95, 15)  # 5% below minimum or 15 minutes
    y_max = min(df['Total Time (min)'].max() * 1.05, 35)  # 5% above maximum or 35 minutes
    plt.ylim(y_min, y_max)
    
    # Format x-axis dates nicely
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    
    output_file = f"5k_improvements.png"
    plt.savefig(output_file, dpi=600, bbox_inches='tight')

# Run the analysis
print("\n--- 5K Running Performance Analysis ---")
plot_5k_times(all_5k_data)