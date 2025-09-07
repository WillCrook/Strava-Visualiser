import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import calendar
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path

def generate_activity_heatmap(input_file=None, output_dir=None):
    # Load and convert
    project_root = Path(__file__).resolve().parent.parent
    if input_file is None:
        input_file = project_root / "data" / 'user_data' / 'Strava Data' / 'activities.csv'
    if output_dir is None:
        output_dir = project_root / "outputs"
    
    output_dir.mkdir(exist_ok=True)

    df = pd.read_csv(input_file)
    df['Activity Date'] = pd.to_datetime(df['Activity Date'], format="%d %b %Y, %H:%M:%S")
    print(f"Total runs loaded: {len(df)}")

    # Extract year, month, day, and weekday
    df['Year'] = df['Activity Date'].dt.year
    df['Month'] = df['Activity Date'].dt.month
    df['Day'] = df['Activity Date'].dt.day
    df['Weekday'] = df['Activity Date'].dt.weekday  # Monday = 0, Sunday = 6

    # Count activities by date
    daily_counts = df.groupby(['Year', 'Month', 'Day']).size().reset_index(name='count')

    # Create a date index for the entire year range in the data
    start_date = df['Activity Date'].min()
    end_date = df['Activity Date'].max()
    date_range = pd.date_range(start=start_date, end=end_date)

    # Create a DataFrame with all dates
    all_dates = pd.DataFrame({
        'Activity Date': date_range,
        'Year': date_range.year,
        'Month': date_range.month,
        'Day': date_range.day,
        'Weekday': date_range.weekday
    })

    # Merge with activity counts
    merged_df = all_dates.merge(
        daily_counts, 
        on=['Year', 'Month', 'Day'], 
        how='left'
    ).fillna(0)

    # Calculate coordinates for the heatmap cells
    merged_df['week_number'] = merged_df['Activity Date'].dt.isocalendar().week
    # Adjust for year wrapping (last week of previous year might be week 53)
    merged_df['adjusted_week'] = merged_df.apply(
        lambda x: x['week_number'] - min(merged_df[merged_df['Year'] == x['Year']]['week_number']) + 
                (0 if x['Year'] == min(merged_df['Year']) else 
                max(merged_df[merged_df['Year'] == min(merged_df['Year'])]['week_number'])), 
        axis=1
    )

    # Create GitHub-like color scheme (light to dark green)
    github_colors = ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39']
    github_cmap = LinearSegmentedColormap.from_list('github', github_colors)

    # Create a figure with GitHub-like style
    fig, ax = plt.subplots(figsize=(16, 6), facecolor='white')

    # Prepare the data matrix for plotting
    max_week = merged_df['adjusted_week'].max() + 1
    activity_matrix = np.zeros((7, max_week))  # 7 days, weeks calculated above

    # Fill the matrix with activity counts
    for _, row in merged_df.iterrows():
        weekday = row['Weekday']
        week = int(row['adjusted_week'])
        count = row['count']
        activity_matrix[weekday, week] = count

    # Determine max count for color scaling (cap at 95th percentile to prevent outliers dominating)
    vmax = np.percentile(activity_matrix[activity_matrix > 0], 95)
    if vmax < 3:
        vmax = 3  # Ensure we have at least 3 different color levels

    # Plot the heatmap
    im = ax.imshow(activity_matrix, cmap=github_cmap, aspect='auto', 
                interpolation='none', vmin=0, vmax=vmax)

    # Set y-axis tick labels (days of week)
    day_labels = ['Mon', 'Wed', 'Fri']
    ax.set_yticks(np.arange(3))
    ax.set_yticklabels(day_labels)

    # Minimize padding
    plt.tight_layout(pad=3)

    # Set x-axis tick labels (months)
    months = []
    month_positions = []

    for year in merged_df['Year'].unique():
        year_data = merged_df[merged_df['Year'] == year]
        for month in range(1, 13):
            month_data = year_data[year_data['Month'] == month]
            if not month_data.empty:
                # Get the week number of the first day of the month
                first_day = month_data.iloc[0]
                month_positions.append(first_day['adjusted_week'])
                months.append(calendar.month_abbr[month])

    # Only show a subset of months to avoid crowding
    if len(month_positions) > 12:
        # Show every 2nd or 3rd month
        step = len(month_positions) // 8
        month_positions = month_positions[::step]
        months = months[::step]

    ax.set_xticks(month_positions)
    ax.set_xticklabels(months)

    # Remove spines
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Add gridlines that match GitHub's style
    ax.set_axisbelow(True)
    ax.grid(False)

    # Add title in GitHub style
    plt.title('Activity Contributions', fontsize=16, pad=20)

    handles = []
    labels = ['No activities', '1 activity', '2 activities', '3 activities', '4+ activities']

    # Add an explanation text
    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, facecolor=github_colors[0], edgecolor='none', label=labels[0]),
        plt.Rectangle((0, 0), 1, 1, facecolor=github_colors[1], edgecolor='none', label=labels[1]),
        plt.Rectangle((0, 0), 1, 1, facecolor=github_colors[2], edgecolor='none', label=labels[2]),
        plt.Rectangle((0, 0), 1, 1, facecolor=github_colors[3], edgecolor='none', label=labels[3]),
        plt.Rectangle((0, 0), 1, 1, facecolor=github_colors[4], edgecolor='none', label=labels[4])
    ]

    # Create a small additional axis for the legend
    leg_ax = fig.add_axes([0.92, 0.15, 0.07, 0.7])
    leg_ax.axis('off')

    # Add the legend to this axis
    leg = leg_ax.legend(handles=legend_elements, title="Activity Level", loc='center left')
    plt.setp(leg.get_title(), fontsize=12)

    # Save as PNG with high DPI
    output_file = output_dir / 'activity.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved activity plot to {output_file}")

    # Display
    plt.close()

if __name__ == "__main__":
    generate_activity_heatmap()