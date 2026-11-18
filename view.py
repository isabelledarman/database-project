"""Web front-end for the Hotel database (Flask).

Run with:  python view.py   then open http://127.0.0.1:5001/
(For the version without a web interface, run main.py instead.)
"""

# third party modules
from flask import (Flask, render_template, send_from_directory, request,
                   redirect, url_for, flash, abort)
import pymysql

# project modules
import config
from logic import Database, TABLES


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
    return render_template('index.html')

@app.route('/all', methods=['GET'])
def show_all():
    return render_template('all.html', data=db.get_all_data())

@app.route('/manage', methods=['GET'])
def manage():
    """Add, edit and delete rows in any table."""
    return render_template('manage.html', manage=db.get_manage_data())

def _edit(table, action, success):
    """Run an insert/update/delete from the /manage page, flash the outcome, and go back to that table."""
    if table not in TABLES:
        abort(404)
    try:
        action(table, request.form)
        flash(success, 'ok')
    except ValueError as e:
        flash(f'{table}: {e}', 'error')
    except pymysql.MySQLError as e:
        flash(f'{table}: ' + (str(e.args[1]) if len(e.args) > 1 else str(e)), 'error')
    return redirect(url_for('manage', _anchor='manage-' + table))

@app.route('/table/<table>/insert', methods=['POST'])
def table_insert(table):
    return _edit(table, db.insert_row, f'Added a row to {table}.')

@app.route('/table/<table>/update', methods=['POST'])
def table_update(table):
    return _edit(table, db.update_row, f'Updated a row in {table}.')

@app.route('/table/<table>/delete', methods=['POST'])
def table_delete(table):
    return _edit(table, db.delete_row, f'Deleted a row from {table}.')

@app.route('/resources/<path:path>')
def send_resources(path):
    """Serve CSS, images, etc."""
    return send_from_directory('resources', path)

@app.route('/query/1', methods = ['GET'])
def query1():
    city = request.args.get('city', '')
    bed = request.args.get('bed', '')
    smoking = request.args.get('smoking', '0')=='1'
    check_in = request.args.get('check_in', '')
    check_out = request.args.get('check_out', '')

    rows = None
    if city and bed and check_in and check_out:
        rows = db.available_rooms(city, bed, smoking, check_in, check_out)

    return render_template('query1.html', rows = rows, cities = db.get_cities(), beds = db.get_beds())

@app.route('/query/2', methods = ['GET'])
def query2():
    city = request.args.get('city', '')
    check_in = request.args.get('check_in', '')
    check_out = request.args.get('check_out', '')
    
    rows = None
    if city and check_in and check_out:
        rows = db.available_accessible_rooms(city, check_in, check_out)
    
    return render_template('query2.html', rows = rows, cities = db.get_cities())

@app.route('/query/3', methods = ['GET'])
def query3():
    city = request.args.get('city','')
    rows = None
    if city:
        rows = db.mountain_or_ocean(city)
    return render_template('query3.html', rows = rows, cities = db.get_cities())
    

@app.route('/query/4', methods = ['GET'])
def query4():
    name = request.args.get('name','')
    phone = request.args.get('phone','')
    rows = None
    if name and phone:
        rows = db.reservations_by_person(name, phone)
    return render_template('query4.html', rows = rows)

@app.route('/query/5', methods = ['GET'])
def query5():
    name = request.args.get('name','')
    phone = request.args.get('phone','')
    rows = None
    if name and phone:
        rows = db.guest_charges_list(name, phone)
    return render_template('query5.html', rows = rows)

@app.route('/query/6', methods = ['GET'])
def query6():
    rows = db.no_show_reservations()
    return render_template('query6.html', rows = rows)

@app.route('/query/7', methods = ['GET'])
def query7():
    rows = db.bonus_list()
    return render_template('query7.html', rows = rows)

@app.route('/query/8', methods = ['GET'])
def query8():
    rows = db.reservation_details()
    return render_template('query8.html', rows = rows)

if __name__ == '__main__':
    app.run(host=app.host, port=app.port, debug=app.debug)