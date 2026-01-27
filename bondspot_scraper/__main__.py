from datetime import datetime
from bondspot_scraper import fetch_data


def main():
    # Date Range
    start_date = datetime(2024, 9, 30)
    end_date = datetime(2024, 10, 12)

    # Data Types and Compression Methods
    data_types = ["bond", "fixing", "repo"]
    methods = [
        "compress_by_column_all_instruments",
        "compress_by_instrument_all_columns",
        "compress_full_dataset"
    ]

    # Example columns for each group
    columns_map = {
        "bond": ["Price B"],
        "fixing": ["Price B"],
        "repo": ["Average"]
    }

    # Sample instrument
    test_instrument = "DS0725"

    # Fetch data only once (fetcher will check if it exists)
    print("Fetching source data (if not present)...")
    fetch_data(
        start_date=start_date,
        end_date=end_date,
        data_type="bond",
        method="compress_by_column_all_instruments",
        columns_to_analyze=columns_map["bond"]
    )

    # Processing all combinations
    for data_type in data_types:
        for method in methods:
            print(f"\nProcessing: {data_type} - {method}")
            kwargs = {
                "start_date": start_date,
                "end_date": end_date,
                "data_type": data_type,
                "method": method
            }

            if method == "compress_by_column_all_instruments":
                kwargs["columns_to_analyze"] = columns_map[data_type]
            elif method == "compress_by_instrument_all_columns":
                kwargs["instrument_name"] = test_instrument

            try:
                fetch_data(**kwargs)
            except Exception as e:
                print(f"Error during processing {data_type} - {method}: {e}")


if __name__ == "__main__":
    main()
