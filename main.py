"""Displays all data, no web server needed. Web interface has all queries.

Run with:  python3 main.py
"""

import config
from logic import Database


def main():
    db = Database(config)
    try:
        db.display_all()
    finally:
        db.close()


if __name__ == '__main__':
    main()