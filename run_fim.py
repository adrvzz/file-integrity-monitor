#!/usr/bin/env python3
"""
run_fim.py

Entry point — run this script directly instead of executing
fim/cli.py on its own (the fim package uses relative imports, which
only resolve correctly when it's imported as a package, e.g. from
this script).

Examples:
    python run_fim.py baseline ./sample_target
    python run_fim.py scan ./sample_target
    python run_fim.py watch ./sample_target
"""

from fim.cli import main

if __name__ == "__main__":
    main()
