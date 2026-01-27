# BondSpot Scraper

Biblioteka Python do pobierania i przetwarzania danych rynkowych z serwisu [BondSpot](https://www.bondspot.pl/) - platformy obrotu obligacjami skarbowymi i innymi instrumentami dłużnymi w Polsce.

## Cel

BondSpot Scraper automatyzuje proces pobierania historycznych danych z BondSpot, parsuje tabele HTML do strukturyzowanych DataFrame'ów i zapisuje je w formacie Parquet. Biblioteka obsługuje trzy typy danych:

- **bond** - transakcje obligacjami (PLN)
- **fixing** - dane fixingowe (9:30 i 16:30)
- **repo** - transakcje warunkowe

## Instalacja

```bash
# Klonowanie repozytorium
git clone https://github.com/your-username/bondspot-scraper.git
cd bondspot-scraper

# Instalacja zależności
pip install -r requirements.txt
```

**Wymagania:** Python >= 3.12

## Szybki start

```python
from datetime import datetime
from bondspot_scraper import fetch_data

df = fetch_data(
    start_date=datetime(2024, 9, 30),
    end_date=datetime(2024, 10, 12),
    data_type="bond",
    method="compress_by_column_all_instruments",
    columns_to_analyze=["Price B"]
)

print(df.head())
```

## Parametry funkcji `fetch_data`

| Parametr | Typ | Domyślnie | Opis |
|----------|-----|-----------|------|
| `start_date` | `datetime` | wymagany | Data początkowa zakresu |
| `end_date` | `datetime` | wymagany | Data końcowa zakresu |
| `data_type` | `str` | `"bond"` | Typ danych: `"bond"`, `"fixing"`, `"repo"` |
| `method` | `str` | `"compress_by_column_all_instruments"` | Metoda kompresji (patrz niżej) |
| `max_workers` | `int` | `8` | Liczba wątków do równoległego pobierania |
| `instrument_name` | `str` | `None` | Nazwa instrumentu (wymagana dla niektórych metod) |
| `columns_to_analyze` | `list[str]` | `None` | Lista kolumn do analizy |

## Metody kompresji

| Metoda | Opis |
|--------|------|
| `compress_by_column_all_instruments` | Wybrane kolumny dla wszystkich instrumentów (szeregi czasowe) |
| `compress_by_instrument_all_columns` | Wszystkie kolumny dla jednego instrumentu |
| `compress_full_dataset` | Pełny zbiór danych bez filtrowania |

## Przykłady użycia

### Pobierz ceny bid dla wszystkich obligacji

```python
df = fetch_data(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    data_type="bond",
    method="compress_by_column_all_instruments",
    columns_to_analyze=["Price B"]
)
```

### Pobierz wszystkie dane dla konkretnego instrumentu

```python
df = fetch_data(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    data_type="bond",
    method="compress_by_instrument_all_columns",
    instrument_name="DS0725"
)
```

### Pobierz dane fixingowe

```python
df = fetch_data(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    data_type="fixing",
    method="compress_by_column_all_instruments",
    columns_to_analyze=["Fixing"]
)
```

### Pobierz dane repo

```python
df = fetch_data(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    data_type="repo",
    method="compress_by_column_all_instruments",
    columns_to_analyze=["Average"]
)
```

## Struktura danych wyjściowych

Dane są zapisywane w dwóch lokalizacjach:

```
data/
├── raw/           # Surowe dane w formacie Parquet
│   ├── bonds_pln/
│   ├── fixing/
│   └── repo/
└── cleared/       # Przetworzone dane w formacie Excel
```

## Dostępne kolumny

### Bond (obligacje)
`Name`, `ISIN`, `Price B`, `Price S`, `First`, `Max`, `Min`, `Last`, `Average`, `Volume`, `Turnover_Mln`, `Num_Transactions`

### Fixing
`Name`, `ISIN`, `Price B`, `Price S`, `Yield B`, `Yield S`, `Fixing`, `Yield Fixing`

### Repo
`Name`, `ISIN`, `Code`, `Days`, `Min`, `Max`, `Average`, `Turnover_Mln`

## Licencja

MIT License - zobacz plik [LICENSE](LICENSE)

## Autor

Paweł Jakubowski (pawel01jakubowski@gmail.com)
