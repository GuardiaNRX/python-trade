"""
Moduł atomic writes: atomowe zapisy plików (text, CSV, Parquet).
"""
import os
import tempfile

import pandas as pd


def atomic_write_bytes(path: str, data: bytes) -> None:
    """
    Atomowy zapis bajtów do pliku.

    Args:
        path: Ścieżka docelowa
        data: Dane binarne
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with tempfile.NamedTemporaryFile(delete=False, dir=os.path.dirname(path)) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name

    os.replace(tmp_path, path)


def atomic_write_text(path: str, text: str, encoding: str = "utf-8") -> None:
    """
    Atomowy zapis tekstu do pliku.

    Args:
        path: Ścieżka docelowa
        text: Tekst do zapisu
        encoding: Kodowanie (domyślnie UTF-8)
    """
    atomic_write_bytes(path, text.encode(encoding))


def atomic_write_csv(df: pd.DataFrame, path: str, **kwargs) -> None:
    """
    Atomowy zapis DataFrame do CSV.

    Args:
        df: DataFrame do zapisu
        path: Ścieżka docelowa
        **kwargs: Dodatkowe argumenty do to_csv
    """
    tmp = df.to_csv(index=False, **kwargs)
    atomic_write_text(path, tmp)


def atomic_write_parquet(df: pd.DataFrame, path: str, **kwargs) -> None:
    """
    Atomowy zapis DataFrame do Parquet.

    Args:
        df: DataFrame do zapisu
        path: Ścieżka docelowa
        **kwargs: Dodatkowe argumenty do to_parquet
    """
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)

    with tempfile.NamedTemporaryFile(delete=False, dir=d, suffix=".parquet") as t:
        df.to_parquet(t.name, **kwargs)
        tmp_path = t.name

    os.replace(tmp_path, path)
