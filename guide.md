## "Building a Dating Site Database Application"

---

## Pre-Class Setup (Do This Before Class)

1. **Test MySQL connection** - Ensure MySQL server is running
2. **Have the shared folder** with all project files
3. **Have the schema.sql ready** to run

---

## Two Ways to Build the Front-End

The database part of the project (Sections 1 and 2) is the **same for everyone**. After that, choose one front-end:

| | **Option A: Web app** | **Option B: Command-line app** |
|---|---|---|
| Front-end file | `view.py` + `templates/` + `resources/` | `main.py` |
| Packages | `pymysql`, `Flask` | `pymysql` only |
| Run with | `python view.py`, then open the browser | `python main.py` |
| Guide sections | 1, 2, **3A**, 4, 5 | 1, 2, **3B**, 4 (skip 4.3), 5 |

Both options use the **same** `config.py`, `logic.py` and `schema.sql`. That is the point of keeping the database layer separate.

---

### **SECTION 1: Setup**

**Point:** "We'll build a simple dating queue application called 'FindPeople.com' where people can join a line and select their interests."

---

#### 1.1 Create Virtual Environment
```bash
# Python 3.12
python3 -m venv demo

# Activate it
# On Mac/Linux:
source demo/bin/activate
# On Windows:
demo\Scripts\activate
```

**Common Alert:** "Notice your terminal prompt changes with `(demo)`. If you don't see this, your environment isn't active!"

**Why Virtual Environment?** "Keeps project dependencies isolated. Different projects might need different package versions."

---

#### 1.2 Install Required Packages
```bash
# Option A (web app):
pip install pymysql Flask

# Option B (command-line app):
pip install pymysql
```

**Show `pip list`** to verify installation.

**Point:** "PyMySQL is our database connector. Flask is a lightweight web framework, needed only for the web version. We could use Django, but Flask is simpler for learning."

---

#### 1.3 Create Database Schema
```bash
# Open MySQL
mysql -u root -p
```

**In MySQL console:**
```sql
-- Show the schema.sql file in VS Code first
source schema.sql

-- Verify tables were created
SHOW TABLES;
DESC People;
DESC Interests;
DESC PersonInterests;

-- Check sample data
SELECT * FROM Interests;
```

**Exit MySQL:** `exit;`

**Point:** "Three tables: `People`, `Interests`, and `PersonInterests`. A person can have many interests and an interest can belong to many people, so `PersonInterests` is the many-to-many link table."

---

### **SECTION 2: Database Connection Layer (both options)**

#### 2.1 Create `config.py`
**Type live or show pre-made:**
```python
# Database credentials (used by BOTH the web app and the command-line app)
DB_USER = 'root'
DB_NAME = 'project3510'
DB_PASSWORD = '123'
DB_HOST = 'localhost'

# Flask app settings (only used by the web app, view.py)
APP_HOST = '127.0.0.1'
APP_PORT = 5001
APP_DEBUG = True
```

**Point:** "Change `DB_PASSWORD` to your own MySQL password. In production, NEVER hardcode passwords. Use environment variables. But for now, this is fine."

---

#### 2.2 Create `logic.py` - The Database Layer

**Start with the Database class structure:**
```python
import pymysql

class Database(object):
    """Database object to handle all DB operations"""

    def __init__(self, opts):
        """Initialize and connect to database"""
        self.opts = opts
        self.__connect()

    def __connect(self):
        """Establish MySQL connection"""
        self.conn = pymysql.connect(
            host=self.opts.DB_HOST,
            user=self.opts.DB_USER,
            password=self.opts.DB_PASSWORD,
            database=self.opts.DB_NAME
        )

    def close(self):
        """Close the connection when the program ends"""
        self.conn.close()
```

**Point:** "We encapsulate all database logic in one class. This is called the **Data Access Layer** pattern. Both front-ends (web and command line) call this same class."

---

#### 2.3 Add Query Methods

**Method 1: Get All People with Their Interests (Read Operation)**
```python
def get_people(self):
    """Fetch everyone in the line, in the order they joined, with their interests"""
    cur = self.conn.cursor(pymysql.cursors.DictCursor)
    cur.execute('''
        SELECT p.first_name, p.last_name,
               GROUP_CONCAT(i.name ORDER BY i.sort_order SEPARATOR ', ') AS interests
        FROM People p
        LEFT JOIN PersonInterests pi ON p.id = pi.person_id
        LEFT JOIN Interests i ON pi.interest_id = i.id
        GROUP BY p.id, p.first_name, p.last_name, p.time_added
        ORDER BY p.time_added;
    ''')
    results = cur.fetchall()
    cur.close()
    return results
```

**Points:**
- "DictCursor returns rows as dictionaries instead of tuples"
- "Always ORDER BY time_added to show the queue correctly"
- "LEFT JOIN keeps people who have no interests yet; an inner JOIN would drop them"
- "GROUP BY gives one row per person; GROUP_CONCAT joins their interest names into one string"
- "fetchall() loads all results into memory - fine for small datasets"

---

**Method 2: Insert Person and Their Interests (Write Operation)**
```python
def insert_person(self, firstname, lastname, phone, age, interest_ids=()):
    """Add a person and their interests as ONE transaction."""
    cur = self.conn.cursor()
    try:
        # CRITICAL: Use parameterized queries to prevent SQL injection!
        cur.execute('''INSERT INTO People (first_name, last_name, phone, age, time_added)
                       VALUES (%s, %s, %s, %s, NOW())''', (firstname, lastname, phone, age))
        person_id = cur.lastrowid                  # the new AUTO_INCREMENT id
        for interest_id in interest_ids:
            cur.execute('''INSERT INTO PersonInterests (person_id, interest_id)
                           VALUES (%s, %s)''', (person_id, interest_id))
        self.conn.commit()                         # MUST COMMIT for changes to persist!
        return person_id
    except pymysql.MySQLError:
        self.conn.rollback()                       # undo the half-finished insert
        raise
    finally:
        cur.close()
```

**Points:**
- "`cur.lastrowid` gives the id MySQL just assigned to the new person"
- "We commit only once, at the end: either the person AND all their interests are saved, or nothing is. That's atomicity."
- "If any insert fails (e.g. an interest id that doesn't exist breaks the foreign key), `rollback()` undoes everything"

```python
# BAD - Vulnerable to SQL Injection:
sql = f"INSERT INTO People VALUES ('{firstname}', '{lastname}')"

# GOOD - Parameterized query:
sql = "INSERT INTO People VALUES (%s, %s)"
cur.execute(sql, (firstname, lastname))
```

**SQL Injection:**
"If someone enters `'; DROP TABLE People; --` as their first name, what happens?"
- you can check that BAD approach would execute DROP TABLE
- and GOOD approach treats it as literal text

---

**Method 3: Get Interests**
```python
def get_interests(self):
    """Fetch all interests, in display order"""
    cur = self.conn.cursor(pymysql.cursors.DictCursor)
    cur.execute('SELECT id, name FROM Interests ORDER BY sort_order;')
    results = cur.fetchall()
    cur.close()
    return results
```

**Point:** "The web app uses this for the checkboxes; the command-line app prints it as a numbered list."

---

### **SECTION 3A: Option A - Flask Web Application**

#### 3A.1 Create Project Structure
```bash
mkdir templates
mkdir resources

# Move index.html to templates/
# Move CSS and images to resources/
```

**Show final structure:**
```
dating_app_demo/
├── demo/
├── config.py
├── logic.py
├── schema.sql
├── view.py
├── templates/
│   └── index.html
└── resources/
    ├── style.css
    └── looking_forward.jpg
```

---

#### 3A.2 Create `view.py` - The Web Layer

**Initialize Flask App:**
```python
import pymysql
from flask import Flask, render_template, request, redirect, send_from_directory
import config
from logic import Database

# Create Flask app and database connection
app = Flask(__name__)
db = Database(config)

# Configure the app
app.host = config.APP_HOST
app.port = config.APP_PORT
app.debug = config.APP_DEBUG
```

**Point:** "Flask uses the `@app.route()` decorator to map URLs to functions."

---

#### 3A.3 Main Page Route (GET Request)

```python
@app.route('/', methods=['GET'])
def index():
    """Display the main page with form and current queue"""
    people = db.get_people()
    interests = db.get_interests()
    return render_template('index.html', people=people, interests=interests)
```

**Show `index.html` in VS Code:**
```html
<!-- Point out Jinja2 templating -->
{% for person in people %}
  <li>{{person['first_name']}} {{person['last_name']}}</li>
{% endfor %}
```

**Point:** "Flask uses Jinja2 templates. The `{{ }}` syntax injects Python variables into HTML."

---

#### 3A.4 Form Submission Route (POST Request)

```python
@app.route('/insert', methods=['POST'])
def insert():
    """Handle form submission to add a new person"""
    # Extract form data
    firstname = request.form.get('firstname', '').strip()
    lastname = request.form.get('lastname', '').strip()
    phone = request.form.get('phone', '').strip()
    age = request.form.get('age', '').strip()
    interest_ids = request.form.getlist('interests')   # every checked checkbox

    # Validate data
    if not firstname or not lastname:
        return "First and last name are required!", 400

    if not phone.isdigit() or len(phone) != 10:
        return "Phone must be 10 digits!", 400

    try:
        age = int(age)
        if age < 18 or age > 99:
            return "Age must be between 18 and 99!", 400
    except ValueError:
        return "Invalid age!", 400

    if not all(i.isdigit() for i in interest_ids):
        return "Invalid interest!", 400

    # Insert into database
    try:
        db.insert_person(firstname, lastname, phone, age, [int(i) for i in interest_ids])
    except pymysql.MySQLError:
        return "Error adding to database", 500
    return redirect('/')  # Redirect back to main page
```

**CRITICAL POINTS:**

1. **Always Validate Input:**
   - "Never trust user input!"
   - "Check data types, lengths, ranges"

2. **POST-Redirect-GET Pattern:**
   - "After POST, always redirect"
   - "Prevents duplicate submissions if user refreshes"

3. **HTTP Status Codes:**
   - 200: Success
   - 400: Bad Request (client error)
   - 500: Server Error

4. **Checkboxes:**
   - "`request.form.getlist('interests')` returns the value of every checked box"

---

#### 3A.5 Static Files Route

```python
@app.route('/resources/<path:path>')
def send_resources(path):
    """Serve CSS, images, etc."""
    return send_from_directory('resources', path)
```

---

#### 3A.6 Run the Application

```python
if __name__ == '__main__':
    app.run(host=app.host, port=app.port, debug=app.debug)
```

**Start the server:**
```bash
python view.py
```

**Expected output:**
```
* Running on http://127.0.0.1:5001/
* Debug mode: on
```

---

### **SECTION 3B: Option B - Command-Line Application (no web interface)**

#### 3B.1 Project Structure

```
dating_app_demo/
├── demo/
├── config.py
├── logic.py
├── schema.sql
└── main.py
```

**Point:** "No templates, no resources, no Flask. `main.py` replaces `view.py` and the templates. `logic.py` doesn't change at all."

---

#### 3B.2 Create `main.py` - The Menu Loop

```python
import pymysql
import config
from logic import Database

MENU = """
=== FindPeople.com ===
1) Show the line
2) Join the line
3) Quit"""

def main():
    db = Database(config)
    try:
        while True:
            print(MENU)
            choice = input("Choose: ").strip()
            if choice == '1':
                show_line(db)
            elif choice == '2':
                join_line(db)
            elif choice == '3':
                print("Goodbye!")
                break
            else:
                print("Please choose 1, 2 or 3.")
    finally:
        db.close()

if __name__ == '__main__':
    main()
```

**Point:** "Compare with the web version: each menu choice plays the role of a route, `input()` plays the role of the HTML form, and `print()` plays the role of the template."

---

#### 3B.3 Show the Line

```python
def show_line(db):
    """Print everyone in the queue"""
    people = db.get_people()
    if not people:
        print("The line is empty.")
        return
    print("\nThe line:")
    for number, person in enumerate(people, start=1):
        interests = person['interests'] or 'no interests yet'
        print(f"  {number}. {person['first_name']} {person['last_name']}  ({interests})")
```

---

#### 3B.4 Join the Line (Input + Validation)

```python
def join_line(db):
    """Ask for a person's details, validate them, then insert"""
    first = input("First name: ").strip()
    last = input("Last name: ").strip()
    phone = input("Phone (10 digits): ").strip()
    age = input("Age: ").strip()

    # Never trust user input: validate it first
    if not first or not last:
        print("First and last name are required!")
        return
    if not (phone.isdigit() and len(phone) == 10):
        print("Phone must be 10 digits!")
        return
    if not age.isdigit() or not 18 <= int(age) <= 99:
        print("Age must be a number between 18 and 99!")
        return

    interest_ids = choose_interests(db)
    try:
        db.insert_person(first, last, phone, int(age), interest_ids)
        print(f"Added {first} {last} to the line!")
    except pymysql.MySQLError as error:
        print("Error adding to database:", error)
```

**Points:**
- "Same validation rules as the web version"
- "`age.isdigit()` is checked before `int(age)`, so typing `abc` prints a message instead of crashing"
- "`choose_interests()` (in `main.py`) prints the interests as a numbered list and returns the ids the user picks"

---

#### 3B.5 Run the Application

```bash
python main.py
```

**Expected output:**
```
=== FindPeople.com ===
1) Show the line
2) Join the line
3) Quit
Choose:
```

---

### **SECTION 4: Live Testing & Debugging**

#### 4.1 Test the Application

**Option A:** Open browser to `http://127.0.0.1:5001/`
**Option B:** Run `python main.py` and choose `2) Join the line`

**Live Actions:**
1. **Add a valid person:**
   - First: John
   - Last: D
   - Phone: 5551234567
   - Age: 25
   - Pick some interests (checkboxes, or numbers like `1, 4, 9`)
   - Submit → Show they appear in "The line" with their interests

2. **Check database:**
```bash
mysql -u root -p project3510
SELECT * FROM People;
SELECT * FROM PersonInterests;
```

**Point:** "See the AUTO_INCREMENT ID and the time_added timestamp filled in, plus one PersonInterests row per chosen interest!"

---

#### 4.2 Demonstrate Common Errors (both options)

**Error 1: Missing Required Field**
- Leave first name blank
- Submit → Show validation error

**Error 2: Invalid Phone**
- Enter "abc123" as phone
- Show error message

**Error 3: SQL Injection Attempt**
- Enter `'; DROP TABLE People; --` as first name
- Show it's safely stored as text

**Error 4: Forgot to Commit**
```python
# Temporarily comment out self.conn.commit() in insert_person
# Show data doesn't persist
# Re-add it and explain
```

---

#### 4.3 Check Flask Debug Mode (Option A only)

**Intentionally cause an error:**
```python
# In insert() function, add:
x = 1 / 0  # Division by zero
```

**Show the debug page with:**
- Stack trace
- Variable values
- Interactive debugger

**Point:** "Debug mode is AMAZING for learning but NEVER use in production - it exposes your code!"

**Option B equivalent:** the same error in `main.py` prints a Python traceback in the terminal.

---

### **SECTION 5: Wrap-Up & Extensions**

#### Key Takeaways (Review These):

1. **Three-Layer Architecture:**
   - Database Layer (`logic.py`), shared by both options
   - Application Layer (`view.py` for web, `main.py` for command line)
   - Presentation Layer (`templates/` for web, `print()` for command line)

2. **Security Best Practices:**
   - ✅ Parameterized queries (prevent SQL injection)
   - ✅ Input validation (check data before DB)
   - ✅ Never trust user input
   - ❌ Don't hardcode passwords in production

3. **Database Operations:**
   - SELECT: Read data (with JOINs across tables)
   - INSERT: Write data
   - Always COMMIT writes; ROLLBACK on error
   - Use ORDER BY for consistent results

4. **Web Development Patterns (Option A):**
   - GET: Retrieve pages/data
   - POST: Submit forms
   - POST-Redirect-GET: Prevent duplicate submissions
   - Template rendering: Separate logic from HTML

---

#### Common Questions:

**Q: Why not just use raw SQL in the routes or in main.py?**
**A:** Separation of concerns. If you change databases (MySQL → PostgreSQL), you only update logic.py. It's also why the web app and the command-line app can share the same logic.py.

**Q: What if 1000 people submit at once?**
**A:** Connection pooling, async operations, caching. Topics for advanced courses!

**Q: Is this production-ready?**
**A:** NO! Missing: CSRF protection, rate limiting, proper error handling, logging, etc.

**Q: Why Flask instead of Django?**
**A:** Flask is minimal and explicit - great for learning. Django is better for large projects.

---

## Troubleshooting Guide

### Issue: "Module not found: pymysql" (or flask)
**Solution:** Virtual environment not activated or package not installed
```bash
source demo/bin/activate  # Activate first!
pip install pymysql Flask   # Option B only needs pymysql
```

### Issue: "Can't connect to MySQL server" / "Access denied"
**Solution:** Check MySQL is running and the password in config.py is yours
```bash
mysql -u root -p
# If this fails, MySQL isn't running
```

### Issue: "Table doesn't exist"
**Solution:** Schema not created
```bash
mysql -u root -p < schema.sql
```

### Issue: "Data not showing up in database"
**Solution:** Forgot `commit()`
```python
self.conn.commit()  # Add this after INSERT/UPDATE/DELETE!
```

### Issue: "Form data is None" or KeyError (Option A)
**Solution:** Check form field names match
```html
<input name="firstname" />  <!-- Must match -->
```
```python
request.form['firstname']  # Exact match!
```

### Issue: "Port 5001 is in use" (Option A)
**Solution:** An old `python view.py` is still running. Stop it with Ctrl+C in its terminal, or change `APP_PORT` in config.py to e.g. 5002.

---

## Files Checklist

**Both options:**
- ✅ config.py
- ✅ logic.py
- ✅ schema.sql

**Option A (web app):**
- ✅ view.py
- ✅ templates/index.html
- ✅ resources/style.css
- ✅ resources/looking_forward.jpg

**Option B (command-line app):**
- ✅ main.py

---

## Additional Resources for Students

- Flask Documentation: https://flask.palletsprojects.com/
- PyMySQL Documentation: https://pymysql.readthedocs.io/
- SQL Injection Prevention: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
---

**Good luck with your project! 🎓**
