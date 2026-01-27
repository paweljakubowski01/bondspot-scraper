import os
import re
import pandas as pd
from typing import List, Optional


def clean_raw_bond_data_before_parsing(file_path: str) -> pd.DataFrame:
    """
    Cleans Parquet file data for bond transactions:
    - Keeps only rows where the first column matches the pattern XXYYYY (e.g., DS0727).
    - Adds header: Name, ISIN, Price B, Price S, First, Max, Min, Last, Average, Volume, Turnover_Mln, Num_Transactions.
    """
    df = pd.read_parquet(file_path)

    # Filter rows where the first column matches the pattern XXYYYY
    pattern = re.compile(r'^[A-Z]{2}\d{4}$')
    df_filtered = df[df.iloc[:, 0].astype(str).str.match(pattern)].copy()

    # Set column headers
    df_filtered.columns = [
        "Name", "ISIN", "Price B", "Price S", "First", "Max", "Min",
        "Last", "Average", "Volume", "Turnover_Mln", "Num_Transactions"
    ]

    return df_filtered


def compress_by_column_all_instruments(
    folder_path: str,
    columns_to_analyze: Optional[List[str]] = None
) -> pd.DataFrame:
    files = os.listdir(folder_path)
    parquet_files = [file for file in files if file.endswith('.parquet')]
    result_df = pd.DataFrame()

    for file in parquet_files:
        file_path = os.path.join(folder_path, file)
        date = file[:8]

        try:
            df = clean_raw_bond_data_before_parsing(file_path)

            if columns_to_analyze is None:
                columns_to_analyze = ['Price B']

            df = df[['Name'] + columns_to_analyze]
            row = df.set_index('Name').T
            row.index = [pd.to_datetime(date, format='%Y%m%d').strftime('%Y-%m-%d')]
            row.columns = [f"{col}_PriceB" for col in row.columns]
            result_df = pd.concat([result_df, row])

        except Exception as e:
            print(f"Error in file {file}: {e}")

    return result_df


def compress_by_instrument_all_columns(
    folder_path: str,
    instrument_name: str
) -> pd.DataFrame:
    files = os.listdir(folder_path)
    parquet_files = [file for file in files if file.endswith('.parquet')]
    result_df = pd.DataFrame()

    for file in parquet_files:
        file_path = os.path.join(folder_path, file)
        date = file[:8]

        try:
            df = clean_raw_bond_data_before_parsing(file_path)
            df = df[df['Name'] == instrument_name]
            if df.empty:
                continue

            df = df.drop(columns=['Name'])
            df.index = [pd.to_datetime(date, format='%Y%m%d').strftime('%Y-%m-%d')]
            result_df = pd.concat([result_df, df])

        except Exception as e:
            print(f"Error in file {file}: {e}")

    return result_df


def compress_full_dataset(folder_path: str) -> pd.DataFrame:
    all_data = {}
    files = sorted([f for f in os.listdir(folder_path) if f.endswith('.parquet')])

    for file in files:
        file_path = os.path.join(folder_path, file)
        date_str = file[:8]

        try:
            df = clean_raw_bond_data_before_parsing(file_path)
            df.set_index(keys='Name', inplace=True)
            df.columns = [col.strip() for col in df.columns]

            row_data = {}
            for instrument in df.index:
                for col in df.columns:
                    key = f"{instrument}_{col}"
                    row_data[key] = df.loc[instrument, col]

            date = pd.to_datetime(date_str, format='%Y%m%d').date()
            all_data[date] = row_data

        except Exception as e:
            print(f"Error in file {file}: {e}")

    result_df = pd.DataFrame.from_dict(all_data, orient='index')
    result_df.index.name = 'Date'
    result_df.sort_index(inplace=True)
    return result_df
