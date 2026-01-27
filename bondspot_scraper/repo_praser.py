import os
import re
import pandas as pd
from typing import List, Optional


def clean_raw_repo_transactions(file_path: str) -> pd.DataFrame:
    """
    Cleans Parquet file data for conditional transactions:
    - Keeps only rows where the first column matches the pattern XXYYYY (e.g., DS0727).
    - Adds header: Name, ISIN, Code, Days, Min, Max, Average, Turnover_Mln.
    """
    df = pd.read_parquet(file_path)

    # Filter rows where the first column matches the pattern XXYYYY
    pattern = re.compile(r'^[A-Z]{2}\d{4}$')
    df_filtered = df[df.iloc[:, 0].astype(str).str.match(pattern)].copy()

    # Set column headers (if data has no headers)
    if df_filtered.shape[1] == 8:
        df_filtered.columns = ["Name", "ISIN", "Code", "Days", "Min", "Max", "Average", "Turnover_Mln"]

    return df_filtered


def compress_by_column_all_instruments(
    folder_path: str,
    columns_to_analyze: Optional[List[str]] = None
) -> pd.DataFrame:
    files = sorted([file for file in os.listdir(folder_path) if file.endswith('.parquet')])
    result_df = pd.DataFrame()

    for file in files:
        file_path = os.path.join(folder_path, file)
        date_str = file[:8]

        try:
            df = clean_raw_repo_transactions(file_path)

            if columns_to_analyze is None:
                columns_to_analyze = ['Average']

            # Make sure 'Code' is always present
            required_columns = ['Name', 'Code'] + columns_to_analyze
            df = df[required_columns]

            # Creating a unique identifier
            df['Name_Code'] = df['Name'] + "-" + df['Code']
            df_unique = df.drop_duplicates(subset='Name_Code', keep='first')

            # Transposition and formatting
            row = df_unique.set_index('Name_Code')[columns_to_analyze].T
            row.index = [pd.to_datetime(date_str, format='%Y%m%d').strftime('%Y-%m-%d')]
            row.columns = [f"{col}_{columns_to_analyze[0]}" for col in row.columns]

            result_df = pd.concat([result_df, row])

        except Exception as e:
            print(f"Error in file {file}: {e}")

    result_df.index.name = 'Date'
    result_df.sort_index(inplace=True)
    return result_df


def compress_by_instrument_all_columns(
    folder_path: str,
    instrument_name: str
) -> pd.DataFrame:
    files = [file for file in os.listdir(folder_path) if file.endswith('.parquet')]
    all_data = {}

    for file in files:
        file_path = os.path.join(folder_path, file)
        date_str = file[:8]

        try:
            df = clean_raw_repo_transactions(file_path)
            df = df[df['Name'] == instrument_name]
            if df.empty:
                continue

            row_data = {}
            for _, row in df.iterrows():
                code = row['Code']
                for col in df.columns:
                    if col not in ['Name', 'Code']:
                        key = f"{col}-{code}"
                        row_data[key] = row[col]

            all_data[pd.to_datetime(date_str, format='%Y%m%d').strftime('%Y-%m-%d')] = row_data

        except Exception as e:
            print(f"Error in file {file}: {e}")

    result_df = pd.DataFrame.from_dict(all_data, orient='index')
    result_df.index.name = 'Date'
    result_df.sort_index(inplace=True)
    return result_df


def compress_full_dataset(folder_path: str) -> pd.DataFrame:
    all_data = {}
    files = sorted([f for f in os.listdir(folder_path) if f.endswith('.parquet')])

    for file in files:
        file_path = os.path.join(folder_path, file)
        date_str = file[:8]

        try:
            df = clean_raw_repo_transactions(file_path)
            df['Name_Code'] = df['Name'] + "-" + df['Code']
            df.set_index(keys='Name_Code', inplace=True)
            df = df.drop(columns=['Name', 'Code'])
            df.columns = [col.strip() for col in df.columns]
            df = df.groupby(df.index).first()

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
