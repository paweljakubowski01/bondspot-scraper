from datetime import datetime
from pathlib import Path
from typing import Optional, List

from .fetcher import fetch_tables_parallel
from .bond_praser import (
    compress_by_column_all_instruments as bond_compress_by_column,
    compress_by_instrument_all_columns as bond_compress_by_instrument,
    compress_full_dataset as bond_compress_full
)

from .fixing_praser import (
    compress_by_column_all_instruments as fixing_compress_by_column,
    compress_by_instrument_all_columns as fixing_compress_by_instrument,
    compress_full_dataset as fixing_compress_full
)

from .repo_praser import (
    compress_by_column_all_instruments as repo_compress_by_column,
    compress_by_instrument_all_columns as repo_compress_by_instrument,
    compress_full_dataset as repo_compress_full
)

# Fixed list of tables to exclude
EXCLUDE_TABLES = [0, 1, 3]  # <- sample ID, adjust to your needs


def fetch_data(
    start_date,
    end_date,
    data_type: str = "bond",
    method: str = "compress_by_column_all_instruments",
    max_workers: int = 8,
    instrument_name: Optional[str] = None,
    columns_to_analyze: Optional[List[str]] = None
):
    """
    Fetches and processes BondSpot data (bond, fixing, repo).

    Args:
        start_date (datetime): Start date of the data range.
        end_date (datetime): End date of the data range.
        data_type (str): Type of data to process: 'bond', 'fixing', or 'repo'.
        method (str): Compression method to apply.
        max_workers (int): Number of threads for parallel data fetching.
        instrument_name (str, optional): Instrument name (required for some methods).
        columns_to_analyze (list[str], optional): Columns to include in analysis.

    Returns:
        pd.DataFrame: Processed DataFrame ready for analysis or export.
    """
    project_root = Path(__file__).resolve().parent.parent
    raw_path = project_root / "data" / "raw"
    raw_path.mkdir(parents=True, exist_ok=True)

    fetch_tables_parallel(
        start_date=start_date,
        end_date=end_date,
        save_path=str(raw_path),
        exclude_tables=EXCLUDE_TABLES,
        max_workers=max_workers
    )

    folder_map = {
        "bond": "bonds_pln",
        "fixing": "fixing",
        "repo": "repo"
    }

    data_folder = raw_path / folder_map.get(data_type, "")
    if not data_folder.exists() or not any(data_folder.glob("*.parquet")):
        raise FileNotFoundError(f"There is missing data in the folder: {data_folder}")

    if data_type == "bond":
        if method == "compress_by_column_all_instruments":
            df = bond_compress_by_column(str(raw_path / "bonds_pln"), columns_to_analyze)
        elif method == "compress_by_instrument_all_columns":
            if not instrument_name:
                raise ValueError("You must provide 'instrument_name' for method 'compress_by_instrument_all_columns'.")
            df = bond_compress_by_instrument(str(raw_path / "bonds_pln"), instrument_name)
        elif method == "compress_full_dataset":
            df = bond_compress_full(str(raw_path / "bonds_pln"))
        else:
            raise ValueError(f"Unknown compression method: {method}")

    elif data_type == "fixing":
        if method == "compress_by_column_all_instruments":
            df = fixing_compress_by_column(str(raw_path / "fixing"), columns_to_analyze)
        elif method == "compress_by_instrument_all_columns":
            if not instrument_name:
                raise ValueError("You must provide 'instrument_name' for method 'compress_by_instrument_all_columns'.")
            df = fixing_compress_by_instrument(str(raw_path / "fixing"), instrument_name)
        elif method == "compress_full_dataset":
            df = fixing_compress_full(str(raw_path / "fixing"))
        else:
            raise ValueError(f"Unknown compression method: {method}")

    elif data_type == "repo":
        if method == "compress_by_column_all_instruments":
            df = repo_compress_by_column(str(raw_path / "repo"), columns_to_analyze)
        elif method == "compress_by_instrument_all_columns":
            if not instrument_name:
                raise ValueError("You must provide 'instrument_name' for method 'compress_by_instrument_all_columns'.")
            df = repo_compress_by_instrument(str(raw_path / "repo"), instrument_name)
        elif method == "compress_full_dataset":
            df = repo_compress_full(str(raw_path / "repo"))
        else:
            raise ValueError(f"Unknown compression method: {method}")
    else:
        raise ValueError(f"Unknown data type: {data_type}")

    # CONVERSION: commas to dots and floats
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = df[col].str.replace(',', '.').astype(float)
            except Exception:
                pass

    # Writing to a file
    cleared_path = project_root / "data" / "cleared"
    cleared_path.mkdir(parents=True, exist_ok=True)

    output_file = cleared_path / f"{data_type}-{method}.xlsx"
    df.to_excel(output_file, engine="openpyxl")
    print(f"Saved processed data to: {output_file}")

    return df


def help():
    """
    Displays available functionalities and usage examples for the bondspot_scraper package.
    """
    print("""
BondSpot Scraper - Data Fetching and Processing Library
=======================================================

Available data types:
- 'bond'   : Bond transactions
- 'fixing' : Bond fixing data
- 'repo'   : Conditional (repo) transactions

Available compression methods:
- 'compress_by_column_all_instruments' : One column across all instruments
- 'compress_by_instrument_all_columns' : All columns for one instrument
- 'compress_full_dataset'              : Full dataset with all instruments and columns

Main function:
--------------
fetch_data(
    start_date: datetime,
    end_date: datetime,
    data_type: str = 'bond',
    method: str = 'compress_by_column_all_instruments',
    max_workers: int = 8,
    instrument_name: Optional[str] = None,
    columns_to_analyze: Optional[List[str]] = None
) -> pd.DataFrame

Example usage:
--------------
from datetime import datetime
import bondspot_scraper

df = bondspot_scraper.fetch_data(
    start_date=datetime(2024, 9, 30),
    end_date=datetime(2024, 10, 12),
    data_type='bond',
    method='compress_by_column_all_instruments',
    columns_to_analyze=['Price B']
)

df.to_excel("output.xlsx")
""")
