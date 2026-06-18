from pathlib import Path

import pandas as pd

survivors = []
DATA_DIR = Path("data")
CSV_PATH = DATA_DIR / "survivors.csv"

def add_survivor(data):

    survivors.append(data)

def save_csv():

    DATA_DIR.mkdir(exist_ok=True)

    df = pd.DataFrame(survivors)

    df.to_csv(
        CSV_PATH,
        index=False
    )
