"""
Moduł do zapisywania raportów i metadanych.
"""
import os
import json
from typing import Dict, Any
import pandas as pd


def ensure_dir(path: str) -> None:
    """
    Tworzy katalog jeśli nie istnieje.
    
    Parameters:
    -----------
    path : str
        Ścieżka do katalogu
    """
    os.makedirs(path, exist_ok=True)


def save_table(df: pd.DataFrame, outdir: str, name: str) -> str:
    """
    Zapisuje DataFrame do pliku CSV.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame do zapisania
    outdir : str
        Katalog wyjściowy
    name : str
        Nazwa pliku (bez rozszerzenia)
        
    Returns:
    --------
    str
        Pełna ścieżka do zapisanego pliku
    """
    ensure_dir(outdir)
    filepath = os.path.join(outdir, f"{name}.csv")
    df.to_csv(filepath)
    return filepath


def save_metadata(meta: Dict[str, Any], outdir: str, name: str) -> str:
    """
    Zapisuje metadane do pliku JSON.
    
    Parameters:
    -----------
    meta : Dict[str, Any]
        Słownik z metadanymi
    outdir : str
        Katalog wyjściowy
    name : str
        Nazwa pliku (bez rozszerzenia)
        
    Returns:
    --------
    str
        Pełna ścieżka do zapisanego pliku
    """
    ensure_dir(outdir)
    filepath = os.path.join(outdir, f"{name}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return filepath


def write_markdown(report_md: str, outdir: str, filename: str) -> str:
    """
    Zapisuje raport Markdown do pliku.
    
    Parameters:
    -----------
    report_md : str
        Treść raportu w formacie Markdown
    outdir : str
        Katalog wyjściowy
    filename : str
        Nazwa pliku (z rozszerzeniem .md)
        
    Returns:
    --------
    str
        Pełna ścieżka do zapisanego pliku
    """
    ensure_dir(outdir)
    filepath = os.path.join(outdir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_md)
    return filepath
