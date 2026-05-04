"""Téléchargement des sources open data du pipeline SIG éolien.

Usage:
    python scripts/01_download_data.py --source cadastre --dept 60
    python scripts/01_download_data.py --source bdtopo
    python scripts/01_download_data.py --source all
"""
import argparse
import requests
import zipfile
import io
import os
from pathlib import Path

DATA_DIR = Path("data/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "cadastre": {
        "url": "https://cadastre.data.gouv.fr/bundler/cadastre-etalab/departements/{dept}/geojson/parcelles",
        "requires_dept": True,
        "ext": "geojson",
    },
    "sia": {
        "url": "https://www.sia.aviation-civile.gouv.fr/dvd/espace_libraire/produits/produits_numeriques_non_aeronautiques/bdosa/BDOSA_SHP.zip",
        "requires_dept": False,
        "ext": "zip",
    },
    "zaer": {
        "url": "https://www.data.gouv.fr/fr/datasets/r/zones-acceleration-enr-communes.geojson",
        "requires_dept": False,
        "ext": "geojson",
    },
    "zaer_arretees": {
        "url": "https://www.data.gouv.fr/fr/datasets/r/zones-acceleration-enr-prefets.geojson",
        "requires_dept": False,
        "ext": "geojson",
    },
    "monuments_histo": {
        "url": "https://data.culture.gouv.fr/api/explore/v2.1/catalog/datasets/merimee/exports/geojson",
        "requires_dept": False,
        "ext": "geojson",
    },
    "rne_elus": {
        "url": "https://www.data.gouv.fr/fr/datasets/r/d5f400de-ae3f-4966-8cb6-a85c70c6c24a",
        "requires_dept": False,
        "ext": "csv",
    },
}


def download(source: str, dept: str | None = None, timeout: int = 300) -> Path:
    cfg = SOURCES[source]
    url = cfg["url"].format(dept=dept) if cfg.get("requires_dept") else cfg["url"]
    suffix = f"_{dept}" if dept else ""
    dest = DATA_DIR / f"{source}{suffix}.{cfg['ext']}"

    print(f"[{source}] Téléchargement depuis {url}")
    resp = requests.get(url, timeout=timeout, stream=True)
    resp.raise_for_status()

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total * 100
                print(f"\r  {pct:.1f}% ({downloaded/1e6:.1f} MB)", end="", flush=True)
    print(f"\n[{source}] Sauvegardé → {dest}")

    if cfg["ext"] == "zip":
        dest = _extract_zip(dest, DATA_DIR / source)

    return dest


def _extract_zip(zip_path: Path, extract_dir: Path) -> Path:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(extract_dir)
    zip_path.unlink()
    print(f"  Extrait → {extract_dir}")
    return extract_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Téléchargement sources open data SIG éolien")
    parser.add_argument("--source", required=True, choices=[*SOURCES.keys(), "all"], help="Source à télécharger")
    parser.add_argument("--dept", help="Code département (ex: 60, 2A). Requis pour source=cadastre")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    if args.source == "all":
        for src, cfg in SOURCES.items():
            if cfg.get("requires_dept"):
                if args.dept:
                    download(src, dept=args.dept, timeout=args.timeout)
                else:
                    print(f"[{src}] Ignoré (--dept requis)")
            else:
                download(src, timeout=args.timeout)
    else:
        cfg = SOURCES[args.source]
        if cfg.get("requires_dept") and not args.dept:
            parser.error(f"--dept requis pour source={args.source}")
        download(args.source, dept=args.dept, timeout=args.timeout)


if __name__ == "__main__":
    main()
