"""Command-line front-end for the Hotel database (no web server needed).

Run with:  python main.py
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