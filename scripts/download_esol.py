"""Download ESOL dataset from MoleculeNet."""
import urllib.request
import csv
from pathlib import Path

def download_esol():
    url = "https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/delaney-processed.csv"
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / "esol.csv"
    urllib.request.urlretrieve(url, out_path)
    print(f"Downloaded ESOL dataset to {out_path}")

if __name__ == "__main__":
    download_esol()
