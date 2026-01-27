import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import timedelta
import urllib3
import warnings
import os
import logging
from tqdm import tqdm
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import holidays
import time
import random

# Suppress all warnings
warnings.filterwarnings("ignore")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging configuration
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
log_file_path = os.path.join(repo_root, "data", "raw", "scraper.log")
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(message)s')

# Zmienione reguły folderów
folder_rules = [
    {"keywords": ["fixing", "930"], "folder": "fixing_930", "require_all": True},
    {"keywords": ["fixing", "1630"], "folder": "fixing_1630", "require_all": True},
    {"keywords": ["eur", "obligacje"], "folder": "bonds_eur", "require_all": True},
    {"keywords": ["obligacje", "pln"], "folder": "bonds_pln", "require_all": True},
    {"keywords": ["transakcje", "warunkowe"], "folder": "repo", "require_all": True},
    {"keywords": ["statystyka", "rynku"], "folder": "statistics", "require_all": True},
    {"keywords": ["bony"], "folder": "bills", "require_all": False},
]


def determine_folder(name):
    name_lower = name.lower()
    for rule in folder_rules:
        matches = [kw in name_lower for kw in rule["keywords"]]
        if all(matches) if rule["require_all"] else any(matches):
            return rule["folder"]
    return None


def data_already_downloaded(save_path, start_date, end_date):
    """
    Checks if for each business day (excluding weekends and Polish public holidays)
    in the given date range, there is at least one .parquet file containing the date
    in YYYYMMDD format in any subfolder of save_path.
    """
    pl_holidays = holidays.Poland()
    date_list = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    missing_dates = []

    for date in date_list:
        date_str = date.strftime("%Y%m%d")

        # Skip weekends and public holidays
        if date.weekday() >= 5 or date in pl_holidays:
            continue

        found = False
        for root, dirs, files in os.walk(save_path):
            for file in files:
                if file.endswith(".parquet") and date_str in file:
                    found = True
                    break
            if found:
                break

        if not found:
            missing_dates.append(date_str)

    if not missing_dates:
        logging.info("All required data files are present. Skipping download.")
        print("All required data files are present. Skipping download.")
        return True
    else:
        logging.info(f"Missing data for {len(missing_dates)} date(s): {', '.join(missing_dates)}")
        print(f"Missing data for {len(missing_dates)} date(s). Proceeding with download.")
        return False


# New feature: assess whether to use throttling
def should_throttle(start_date, end_date, threshold_days=15):
    return (end_date - start_date).days > threshold_days


def fetch_single_day(date, save_path, exclude_tables, session, delay=0):
    if delay > 0:
        sleep_time = random.uniform(delay * 0.8, delay * 1.2)
        logging.info(f"Throttling: sleeping for {sleep_time:.2f} seconds before fetching {date}")
        time.sleep(sleep_time)

    url = (
        f"https://www.bondspot.pl/notowania_TBSPoland?"
        f"date={date.strftime('%Y%m%d')}&month={date.strftime('%m')}&year={date.strftime('%Y')}"
    )
    logging.info(f"Fetching data from: {url}")

    try:
        response = session.get(url, verify=False)
        soup = BeautifulSoup(response.content, features="lxml")
        tables = soup.find_all("table")
        logging.info(f"Found {len(tables)} tables")

        for i, table in enumerate(tables):
            if (i + 1) in exclude_tables:
                logging.info(f"Skipping table {i + 1}")
                continue

            first_cell_text = "table"
            try:
                first_row = table.find("tr")
                if first_row:
                    first_cell = first_row.find(["td", "th"])
                    if first_cell:
                        first_cell_text = (
                            first_cell.get_text(strip=True)
                            .replace(" ", "_")
                            .replace("/", "_")
                        )
            except Exception as e:
                logging.warning(f"Failed to read cell A1: {e}")

            try:
                rows = table.find_all("tr")
                if "FIXING" in first_cell_text.upper() or len(rows) < 2:
                    df = pd.read_html(str(table), header=0, decimal=",", thousands=None)[0]
                else:
                    df = pd.read_html(str(table), header=[0, 1], decimal=",", thousands=None)[0]
            except Exception as e:
                logging.error(f"Error parsing table {i + 1} ({first_cell_text}): {e}")
                continue

            safe_name = first_cell_text.translate(str.maketrans("", "", r'?:*"<>|()'))
            folder_name = determine_folder(first_cell_text)

            try:
                if "FIXING" in first_cell_text.upper():
                    subfolder_path = os.path.join(save_path, "fixing")
                    match = re.search(r"(\d{1,2}):(\d{2})", first_cell_text)
                    hour_tag = f"{int(match.group(1)):02d}{match.group(2)}" if match else "unknown"
                    file_name = os.path.join(
                        subfolder_path, f"{hour_tag}-{date.strftime('%Y%m%d')}.parquet"
                    )

                elif "PODSUMOWANIE_OBROTU" in first_cell_text.upper() and "OBLIGACJE" in first_cell_text.upper():
                    subfolder_path = os.path.join(
                        save_path, "bonds_eur" if "EUR" in first_cell_text.upper() else "bonds_pln"
                    )
                    file_name = os.path.join(subfolder_path, f"{date.strftime('%Y%m%d')}.parquet")

                elif folder_name:
                    subfolder_path = os.path.join(save_path, folder_name)
                    file_name = os.path.join(subfolder_path, f"{date.strftime('%Y%m%d')}.parquet")

                else:
                    subfolder_path = os.path.join(save_path, "unassigned")
                    file_name = os.path.join(
                        subfolder_path, f"{safe_name}-{date.strftime('%Y%m%d')}.parquet"
                    )

                os.makedirs(subfolder_path, exist_ok=True)
                df.to_parquet(file_name, index=False, compression="snappy")
                logging.info(f"Saved: {file_name}")

            except Exception as e:
                logging.error(f"Error on date {date.strftime('%Y-%m-%d')}: {e}")

    except Exception as e:
        logging.error(f"Request failed for {date.strftime('%Y-%m-%d')}: {e}")


def fetch_tables_parallel(start_date, end_date, save_path, exclude_tables=None, max_workers=8):
    if exclude_tables is None:
        exclude_tables = []

    os.makedirs(save_path, exist_ok=True)

    if data_already_downloaded(save_path, start_date, end_date):
        print(f"Data for the range {start_date.date()} - {end_date.date()} already exist. Skipping the download.")
        return

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    date_list = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    delay = 2 if should_throttle(start_date, end_date) else 0

    logging.info(
        f"Fetching data from {start_date.date()} to {end_date.date()} "
        f"({len(date_list)} days) using {max_workers} threads. "
        f"Throttling: {'ON' if delay else 'OFF'}"
    )

    with requests.Session() as session:
        session.headers.update(headers)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(fetch_single_day, date, save_path, exclude_tables, session, delay)
                for date in date_list
            ]

            for future in tqdm(as_completed(futures), total=len(futures), desc="Parallel download"):
                future.result()
