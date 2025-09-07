import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import calendar
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
from datetime import timedelta

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

    # Extract year
    df['Year'] = df['Activity Date'].dt.year

    # GitHub-like color scheme
    github_colors = ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39']
    github_cmap = LinearSegmentedColormap.from_list('github', github_colors)

    years = sorted(df['Year'].unique())

    last_year_output = None

    for year in years:
        year_start = pd.Timestamp(year=year, month=1, day=1)
        year_end = pd.Timestamp(year=year, month=12, day=31)

        # Build a continuous date index for the year
        date_range = pd.date_range(start=year_start, end=year_end)
        all_dates = pd.DataFrame({'Activity Date': date_range})

        # Count activities by exact date
        daily_counts = (
            df[df['Year'] == year]
            .groupby(df['Activity Date'].dt.floor('D'))
            .size()
            .rename('count')
            .reset_index()
            .rename(columns={'Activity Date': 'Activity Date'})
        )

        # Merge with all days, fill missing with 0
        merged_df = all_dates.merge(daily_counts, on='Activity Date', how='left').fillna({'count': 0})

        # Compute Sunday-start weekday (Sun=0, Mon=1, ..., Sat=6)
        weekday_mon0 = merged_df['Activity Date'].dt.weekday  # Mon=0..Sun=6
        merged_df['weekday_sun0'] = (weekday_mon0 + 1) % 7

        # Compute week index starting Sundays
        jan1 = pd.Timestamp(year=year, month=1, day=1)
        jan1_weekday_sun0 = (jan1.weekday() + 1) % 7
        first_sunday = jan1 - pd.to_timedelta(jan1_weekday_sun0, unit='D')

        sundays = merged_df['Activity Date'] - pd.to_timedelta(merged_df['weekday_sun0'], unit='D')
        merged_df['week_index'] = ((sundays - first_sunday).dt.days // 7).astype(int)

        # Prepare the data matrix
        max_week = merged_df['week_index'].max() + 1
        activity_matrix = np.zeros((7, max_week))

        for _, row in merged_df.iterrows():
            r = int(row['weekday_sun0'])
            c = int(row['week_index'])
            activity_matrix[r, c] = row['count']

        # Color scaling
        positive = activity_matrix[activity_matrix > 0]
        vmax = np.percentile(positive, 95) if positive.size else 3
        if vmax < 3:
            vmax = 3

        # Plot
        fig, ax = plt.subplots(figsize=(16, 6), facecolor='white')
        ax.imshow(activity_matrix, cmap=github_cmap, aspect='auto', interpolation='none', vmin=0, vmax=vmax)

        # Y-axis labels: show Mon/Wed/Fri only, with Sunday-start indexing
        ax.set_yticks([1, 3, 5])
        ax.set_yticklabels(['Mon', 'Wed', 'Fri'])

        # X-axis month ticks for this year only
        months = []
        month_positions = []
        for m in range(1, 13):
            first_day = pd.Timestamp(year=year, month=m, day=1)
            wd = (first_day.weekday() + 1) % 7
            month_pos = int(((first_day - pd.to_timedelta(wd, unit='D')) - first_sunday).days // 7)
            months.append(calendar.month_abbr[m])
            month_positions.append(month_pos)

        # Thin labels if crowded
        if len(month_positions) > 12:
            step = max(1, len(month_positions) // 12)
            months = months[::step]
            month_positions = month_positions[::step]

        ax.set_xticks(month_positions)
        ax.set_xticklabels(months)

        # Style
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(False)

        plt.title(f'Activity Heat Map {year}', fontsize=16, pad=20)

        # Legend
        labels = ['No activities', '1 activity', '2 activities', '3 activities', '4+ activities']
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, facecolor=github_colors[0], edgecolor='none', label=labels[0]),
            plt.Rectangle((0, 0), 1, 1, facecolor=github_colors[1], edgecolor='none', label=labels[1]),
            plt.Rectangle((0, 0), 1, 1, facecolor=github_colors[2], edgecolor='none', label=labels[2]),
            plt.Rectangle((0, 0), 1, 1, facecolor=github_colors[3], edgecolor='none', label=labels[3]),
            plt.Rectangle((0, 0), 1, 1, facecolor=github_colors[4], edgecolor='none', label=labels[4])
        ]
        leg_ax = fig.add_axes([0.92, 0.15, 0.07, 0.7])
        leg_ax.axis('off')
        leg = leg_ax.legend(handles=legend_elements, title="Activity Level", loc='center left')
        plt.setp(leg.get_title(), fontsize=12)

        # Save per-year plot
        output_file = output_dir / f'activity_{year}.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved activity plot to {output_file}")
        last_year_output = output_file
        plt.close()

    # Also save the most recent year's chart as the default filename for convenience
    if last_year_output is not None:
        default_output = output_dir / 'activity.png'
        try:
            # Re-save or copy the last figure path as default by loading and saving through matplotlib is heavy.
            # Simpler: create a symlink if possible, otherwise copy bytes.
            import os
            if default_output.exists():
                default_output.unlink()
            try:
                os.symlink(last_year_output, default_output)
            except Exception:
                # Fallback: copy
                with open(last_year_output, 'rb') as src, open(default_output, 'wb') as dst:
                    dst.write(src.read())
            print(f"Saved default activity plot to {default_output}")
        except Exception as e:
            print(f"Could not write default activity.png: {e}")

if __name__ == "__main__":
    generate_activity_heatmap()