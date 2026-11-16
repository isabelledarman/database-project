"""Web front-end for the Hotel database (Flask).

Run with:  python view.py   then open http://127.0.0.1:5001/
(For the version without a web interface, run main.py instead.)
"""

# third party modules
from flask import Flask, render_template, send_from_directory

# project modules
import config
from logic import Database


# instantiate application and database object
app = Flask(__name__)
db = Database(config)

# configure the web app according to the config object
app.host = config.APP_HOST
app.port = config.APP_PORT
app.debug = config.APP_DEBUG


@app.route('/', methods=['GET'])
def index():
    """Display everything in the database, organized by hotel, reservation, guest and bonus"""
    return render_template('index.html', data=db.get_all_data())


@app.route('/resources/<path:path>')
def send_resources(path):
    """Serve CSS, images, etc."""
    return send_from_directory('resources', path)


if __name__ == '__main__':
    app.run(host=app.host, port=app.port, debug=app.debug)