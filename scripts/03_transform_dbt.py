"""Lancement des transformations dbt (staging → marts).

Usage:
    python scripts/03_transform_dbt.py
    python scripts/03_transform_dbt.py --select staging
    python scripts/03_transform_dbt.py --select marts.contexte_eolien
    python scripts/03_transform_dbt.py --test
"""
import argparse
import subprocess
import sys
import os

DBT_PROJECT_DIR = os.path.join(os.path.dirname(__file__), "..", "dbt")


def run_dbt(args_list: list[str]) -> int:
    cmd = ["dbt", *args_list, "--project-dir", DBT_PROJECT_DIR, "--profiles-dir", DBT_PROJECT_DIR]
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, text=True)
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Lance les transformations dbt du pipeline éolien")
    parser.add_argument("--select", "-s", help="Sélection de modèles dbt (ex: staging, marts.contexte_eolien)")
    parser.add_argument("--test", action="store_true", help="Exécute dbt test après le run")
    parser.add_argument("--full-refresh", action="store_true", help="Reconstruction complète des tables")
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()

    run_args = ["run", f"--threads={args.threads}"]
    if args.select:
        run_args += ["--select", args.select]
    if args.full_refresh:
        run_args.append("--full-refresh")

    rc = run_dbt(run_args)
    if rc != 0:
        print("dbt run a échoué", file=sys.stderr)
        sys.exit(rc)

    if args.test:
        test_args = ["test"]
        if args.select:
            test_args += ["--select", args.select]
        rc = run_dbt(test_args)
        if rc != 0:
            print("dbt test a échoué", file=sys.stderr)
            sys.exit(rc)

    print("Transformations dbt terminées avec succès.")


if __name__ == "__main__":
    main()
