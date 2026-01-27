import os
import re
import pandas as pd
from typing import List, Optional


def clean_raw_fixing_data_before_parsing(file_path: str) -> pd.DataFrame:
    """
    Cleans Parquet file data for fixings:
    - Keeps only rows where the first column matches the pattern XXYYYY (e.g., DS0727).
    - Adds header: Name, ISIN, Price B, Price S, Yield B, Yield S, Fixing, Yield Fixing.
    """
    df = pd.read_parquet(file_path)

    pattern = re.compile(r'^[A-Z]{2}\d{4}$')
    df_filtered = df[df.iloc[:, 0].astype(str).str.match(pattern)].copy()

    if df_filtered.shape[1] == 8:
        df_filtered.columns = [
            "Name", "ISIN", "Price B", "Price S",
            "Yield B", "Yield S", "Fixing", "Yield Fixing"
        ]

    return df_filtered


def compress_by_column_all_instruments(
    folder_path: str,
    columns_to_analyze: Optional[List[str]] = None
) -> pd.DataFrame:
    files = [file for file in os.listdir(folder_path) if file.endswith('.parquet')]
    rows = []

    for file in files:
        file_path = os.path.join(folder_path, file)
        fixing_time, date_str = file[:4], file[5:13]
        date = pd.to_datetime(date_str, format="%Y%m%d").strftime('%Y-%m-%d')

        try:
            df = clean_raw_fixing_data_before_parsing(file_path)

            if columns_to_analyze is None:
                columns_to_analyze = ['Price B']

            selected_cols = ['Name'] + [col for col in df.columns if any(c in col for c in columns_to_analyze)]
            df = df[selected_cols]

            row = df.set_index('Name').T
            row.columns = [f"{fixing_time}-{col}" for col in row.columns]
            row.index = [date]
            rows.append(row)

        except Exception as e:
            print(f"Error in file {file}: {e}")

    if rows:
        result_df = pd.concat(rows, axis=0)
        result_df = result_df.groupby(result_df.index).first()
        result_df.sort_index(inplace=True)
    else:
        result_df = pd.DataFrame()

    return result_df


def compress_by_instrument_all_columns(
    folder_path: str,
    instrument_name: str
) -> pd.DataFrame:
    files = [file for file in os.listdir(folder_path) if file.endswith('.parquet')]
    rows = []

    for file in files:
        file_path = os.path.join(folder_path, file)
        fixing_time, date_str = file[:4], file[5:13]
        date = pd.to_datetime(date_str, format="%Y%m%d").strftime('%Y-%m-%d')

        try:
            df = clean_raw_fixing_data_before_parsing(file_path)
            df = df[df['Name'] == instrument_name]
            if df.empty:
                continue

            df = df.drop(columns=['Name'])
            df.columns = [f"{fixing_time}-{col}" for col in df.columns]
            df.index = [date]
            rows.append(df)

        except Exception as e:
            print(f"Error in file {file}: {e}")

    if rows:
        result_df = pd.concat(rows, axis=0)
        result_df = result_df.groupby(result_df.index).first()
        result_df.sort_index(inplace=True)
    else:
        result_df = pd.DataFrame()

    return result_df


def compress_full_dataset(folder_path: str) -> pd.DataFrame:
    all_data = {}
    files = sorted([f for f in os.listdir(folder_path) if f.endswith('.parquet')])

    for file in files:
        file_path = os.path.join(folder_path, file)
        fixing_time, date_str = file[:4], file[5:13]
        date = pd.to_datetime(date_str, format="%Y%m%d").strftime('%Y-%m-%d')

        try:
            df = clean_raw_fixing_data_before_parsing(file_path)
            df.set_index(keys='Name', inplace=True)
            df.columns = [col.strip() for col in df.columns]

            row_data = {}
            for instrument in df.index:
                for col in df.columns:
                    key = f"{instrument}_{fixing_time}_{col}"
                    row_data[key] = df.loc[instrument, col]

            if date not in all_data:
                all_data[date] = {}
            all_data[date].update(row_data)

        except Exception as e:
            print(f"Error in file {file}: {e}")

    result_df = pd.DataFrame.from_dict(all_data, orient='index')
    result_df.index.name = 'Date'
    result_df.sort_index(inplace=True)
    return result_df
