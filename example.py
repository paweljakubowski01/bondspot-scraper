from bondspot_scraper import fetch_data
from datetime import datetime

df = fetch_data(
    start_date=datetime(year=2024, month=9, day=30),
    end_date=datetime(year=2024, month=10, day=12),
    data_type="bond",
    method="compress_by_column_all_instruments",
    columns_to_analyze=["Price B"]
)

print(df.head(10))