import os
from src import ActivityHeatMap, MapCoverage, RunningImprovementGraph, RunningStats

#Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

#Run Scripts
def run_all():
    print("Running Activity Heat Map...")
    ActivityHeatMap.run(DATA_DIR, OUTPUT_DIR)

    print("Running Map Coverage...")
    MapCoverage.run(DATA_DIR, OUTPUT_DIR)

    print("Running Running Improvement Graph...")
    RunningImprovementGraph.run(DATA_DIR, OUTPUT_DIR)

    print("Running Running Stats...")
    RunningStats.run(DATA_DIR, OUTPUT_DIR)

if __name__ == "__main__":
    run_all()
    print("All analyses complete! Check outputs folder.")