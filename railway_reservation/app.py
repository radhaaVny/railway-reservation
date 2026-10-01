import os, sqlite3, random
from datetime import date, datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from data_structures.linked_list import BookingLinkedList, BookingNode
from data_structures.queue import WaitingQueue, QueueNode

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "database.db")
app = Flask(__name__)
app.secret_key = "ads-mini-project-demo-key"

# ---------------- ADS structures: one Linked List + one Queue per (train, date) ----------------
STRUCT = {}

def get_struct(train_id, jdate):
    key = (train_id, jdate)
    if key not in STRUCT:
        STRUCT[key] = {"ll": BookingLinkedList(), "q": WaitingQueue()}
    return STRUCT[key]

def load_structures():
    """Rebuild Linked Lists and Queues from SQLite at startup (persistence)."""
    STRUCT.clear()
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    q = """SELECT b.*, p.name, t.number FROM bookings b JOIN passengers p ON p.id=b.passenger_id
           JOIN trains t ON t.id=b.train_id WHERE b.status='CONFIRMED' ORDER BY b.id"""
    for r in con.execute(q):
        get_struct(r["train_id"], r["journey_date"])["ll"].append(
            BookingNode(r["pnr"], r["name"], r["number"], r["seat_no"], r["journey_date"]))
    q = """SELECT b.*, p.name, t.number FROM waiting_list w JOIN bookings b ON b.id=w.booking_id
           JOIN passengers p ON p.id=b.passenger_id JOIN trains t ON t.id=b.train_id ORDER BY w.id"""
    for r in con.execute(q):
        get_struct(r["train_id"], r["journey_date"])["q"].enqueue(
            QueueNode(r["pnr"], r["name"], r["number"], r["journey_date"]))
    con.close()

# ---------------- Database ----------------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()

def init_db():
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT, phone TEXT, password_hash TEXT);
    CREATE TABLE IF NOT EXISTS trains(id INTEGER PRIMARY KEY, number TEXT, name TEXT, source TEXT, destination TEXT,
        departure TEXT, arrival TEXT, total_seats INTEGER);
    CREATE TABLE IF NOT EXISTS passengers(id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, age INTEGER, gender TEXT, phone TEXT);
    CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY, pnr TEXT UNIQUE, user_id INTEGER, passenger_id INTEGER,
        train_id INTEGER, journey_date TEXT, seat_no INTEGER, status TEXT, created_at TEXT, cancelled_at TEXT);
    CREATE TABLE IF NOT EXISTS waiting_list(id INTEGER PRIMARY KEY, booking_id INTEGER, train_id INTEGER,
        journey_date TEXT, joined_at TEXT);
    """)
    if not con.execute("SELECT 1 FROM users").fetchone():
        con.execute("INSERT INTO users(username,email,phone,password_hash) VALUES(?,?,?,?)",
                    ("demo", "demo@railway.com", "9876543210", generate_password_hash("demo123")))
        con.executemany("INSERT INTO trains(number,name,source,destination,departure,arrival,total_seats) VALUES(?,?,?,?,?,?,?)", [
            ("12706", "Intercity Express", "Vijayawada", "Hyderabad", "06:30 AM", "12:15 PM", 5),
            ("17202", "Golconda Express", "Vijayawada", "Hyderabad", "05:45 PM", "11:30 PM", 3),
            ("12723", "Telangana Express", "Hyderabad", "Vijayawada", "07:10 AM", "01:05 PM", 4),
            ("12759", "Charminar Express", "Hyderabad", "Chennai", "06:00 PM", "06:15 AM", 5),
            ("12842", "Coromandel Express", "Chennai", "Vijayawada", "08:45 AM", "02:30 PM", 4),
            ("12727", "Godavari Express", "Visakhapatnam", "Hyderabad", "05:15 PM", "05:40 AM", 3)])
    con.commit(); con.close()

# ---------------- Helpers ----------------
def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if "uid" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return f(*a, **k)
    return w

def stations():
    rows = db().execute("SELECT source s FROM trains UNION SELECT destination FROM trains ORDER BY 1").fetchall()
    return [r[0] for r in rows]

def seats_left(train, jdate):
    return train["total_seats"] - len(get_struct(train["id"], jdate)["ll"])

def make_pnr():
    while True:
        p = str(random.randint(10**9, 10**10 - 1))
        if not db().execute("SELECT 1 FROM bookings WHERE pnr=?", (p,)).fetchone():
            return p

def parse_date(s):
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    return d if d >= date.today() else None

# ---------------- Auth ----------------
@app.route("/")
def index():
    return redirect(url_for("dashboard" if "uid" in session else "login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ident, pw = request.form.get("identity", "").strip(), request.form.get("password", "")
        if not ident or not pw:
            flash("Enter your username/email and password.", "error")
        else:
            u = db().execute("SELECT * FROM users WHERE username=? OR email=?", (ident, ident)).fetchone()
            if u and check_password_hash(u["password_hash"], pw):
                session.clear()
                session["uid"], session["username"] = u["id"], u["username"]
                session.permanent = bool(request.form.get("remember"))
                return redirect(url_for("dashboard"))
            flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

# ---------------- Pages ----------------
@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["uid"]
    cnt = lambda s: db().execute("SELECT COUNT(*) FROM bookings WHERE user_id=? AND status=?", (uid, s)).fetchone()[0]
    recent = db().execute("""SELECT b.*, p.name pname, t.number, t.name tname FROM bookings b
        JOIN passengers p ON p.id=b.passenger_id JOIN trains t ON t.id=b.train_id
        WHERE b.user_id=? ORDER BY b.id DESC LIMIT 1""", (uid,)).fetchone()
    ads = []
    for (tid, jd), s in sorted(STRUCT.items(), key=lambda x: x[0][1]):
        if len(s["ll"]) or len(s["q"]):
            t = db().execute("SELECT number FROM trains WHERE id=?", (tid,)).fetchone()
            ads.append({"train": t["number"], "date": jd, "ll": s["ll"].to_list(), "q": s["q"].to_list()})
    return render_template("dashboard.html", stations=stations(), today=date.today().isoformat(),
        n_trains=db().execute("SELECT COUNT(*) FROM trains").fetchone()[0],
        n_conf=cnt("CONFIRMED"), n_wait=cnt("WAITING"), recent=recent, ads=ads)

@app.route("/search")
@login_required
def search():
    src, dst, jd = request.args.get("from", ""), request.args.get("to", ""), request.args.get("date", "")
    results, searched = [], False
    if src or dst or jd:
        searched = True
        if not src or not dst or not jd:
            flash("Select source, destination and journey date.", "error")
        elif src == dst:
            flash("Source and destination cannot be the same.", "error")
        elif not parse_date(jd):
            flash("Select a valid journey date (today or later).", "error")
        else:
            for t in db().execute("SELECT * FROM trains WHERE source=? AND destination=?", (src, dst)):
                results.append({"t": t, "left": seats_left(t, jd)})
    return render_template("trains.html", stations=stations(), results=results, searched=searched,
                           src=src, dst=dst, jd=jd, today=date.today().isoformat())

@app.route("/book/<int:tid>", methods=["GET", "POST"])
@login_required
def book(tid):
    train = db().execute("SELECT * FROM trains WHERE id=?", (tid,)).fetchone()
    jd = request.values.get("date", "")
    if not train or not parse_date(jd):
        flash("Invalid train or journey date.", "error")
        return redirect(url_for("search"))
    st = get_struct(tid, jd)
    left = seats_left(train, jd)
    if request.method == "POST":
        name, age = request.form.get("name", "").strip(), request.form.get("age", "")
        gender, phone = request.form.get("gender", ""), request.form.get("phone", "").strip()
        action = request.form.get("action")
        err = None
        if not name or not all(c.isalpha() or c == " " for c in name): err = "Enter a valid full name."
        elif not age.isdigit() or not 1 <= int(age) <= 120: err = "Enter a valid age (1-120)."
        elif gender not in ("Male", "Female", "Other"): err = "Select a gender."
        elif not (phone.isdigit() and len(phone) == 10): err = "Enter a valid 10-digit phone number."
        elif action == "book" and left <= 0: err = "No seats are currently available."
        elif action == "waitlist" and left > 0: err = "Seats are available. Please book a seat."
        elif action not in ("book", "waitlist"): err = "Invalid request."
        if err:
            flash(err, "error")
        else:
            con = db()
            pid = con.execute("INSERT INTO passengers(user_id,name,age,gender,phone) VALUES(?,?,?,?,?)",
                              (session["uid"], name, int(age), gender, phone)).lastrowid
            pnr, now = make_pnr(), datetime.now().isoformat(timespec="seconds")
            if action == "book":
                seat = next(s for s in range(1, train["total_seats"] + 1) if s not in st["ll"].seats())
                st["ll"].append(BookingNode(pnr, name, train["number"], seat, jd))       # Linked List insert
                con.execute("INSERT INTO bookings(pnr,user_id,passenger_id,train_id,journey_date,seat_no,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                            (pnr, session["uid"], pid, tid, jd, seat, "CONFIRMED", now))
            else:
                st["q"].enqueue(QueueNode(pnr, name, train["number"], jd))               # Queue enqueue
                bid = con.execute("INSERT INTO bookings(pnr,user_id,passenger_id,train_id,journey_date,seat_no,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                  (pnr, session["uid"], pid, tid, jd, None, "WAITING", now)).lastrowid
                con.execute("INSERT INTO waiting_list(booking_id,train_id,journey_date,joined_at) VALUES(?,?,?,?)", (bid, tid, jd, now))
            con.commit()
            return redirect(url_for("confirmation", pnr=pnr))
    return render_template("booking.html", train=train, jd=jd, left=left)

def booking_row(pnr, uid):
    return db().execute("""SELECT b.*, p.name pname, t.number, t.name tname, t.source, t.destination FROM bookings b
        JOIN passengers p ON p.id=b.passenger_id JOIN trains t ON t.id=b.train_id
        WHERE b.pnr=? AND b.user_id=?""", (pnr, uid)).fetchone()

@app.route("/confirmation/<pnr>")
@login_required
def confirmation(pnr):
    b = booking_row(pnr, session["uid"])
    if not b:
        flash("Booking not found.", "error")
        return redirect(url_for("dashboard"))
    wl = get_struct(b["train_id"], b["journey_date"])["q"].position(pnr) if b["status"] == "WAITING" else None
    return render_template("confirmation.html", b=b, wl=wl)

@app.route("/my-bookings")
@login_required
def my_bookings():
    tab = request.args.get("tab", "CONFIRMED").upper()
    tab = tab if tab in ("CONFIRMED", "WAITING", "CANCELLED") else "CONFIRMED"
    rows = db().execute("""SELECT b.*, p.name pname, t.number, t.name tname FROM bookings b
        JOIN passengers p ON p.id=b.passenger_id JOIN trains t ON t.id=b.train_id
        WHERE b.user_id=? AND b.status=? ORDER BY b.id DESC""", (session["uid"], tab)).fetchall()
    items = []
    for r in rows:
        wl = get_struct(r["train_id"], r["journey_date"])["q"].position(r["pnr"]) if tab == "WAITING" else None
        items.append({"r": r, "wl": wl})
    return render_template("my_bookings.html", tab=tab, items=items)

@app.route("/cancel/<pnr>", methods=["POST"])
@login_required
def cancel(pnr):
    con = db()
    b = con.execute("SELECT * FROM bookings WHERE pnr=? AND user_id=?", (pnr, session["uid"])).fetchone()
    if not b:
        flash("Booking not found.", "error")
        return redirect(url_for("my_bookings"))
    if b["status"] == "CANCELLED":
        flash("This ticket is already cancelled.", "error")
        return redirect(url_for("my_bookings", tab="CANCELLED"))
    st, now = get_struct(b["train_id"], b["journey_date"]), datetime.now().isoformat(timespec="seconds")
    if b["status"] == "WAITING":
        st["q"].remove(pnr)
        con.execute("DELETE FROM waiting_list WHERE booking_id=?", (b["id"],))
        con.execute("UPDATE bookings SET status='CANCELLED', cancelled_at=? WHERE id=?", (now, b["id"]))
        con.commit()
        flash("Waiting-list ticket cancelled.", "success")
        return redirect(url_for("my_bookings", tab="CANCELLED"))
    st["ll"].remove(pnr)                                                       # 1. remove from Linked List
    con.execute("UPDATE bookings SET status='CANCELLED', cancelled_at=? WHERE id=?", (now, b["id"]))  # 2. update DB
    freed = b["seat_no"]                                                        # 3. release seat
    if not st["q"].is_empty():                                                  # 4. check Queue
        n = st["q"].dequeue()                                                   # 5. dequeue first waiting passenger
        st["ll"].append(BookingNode(n.pnr, n.passenger, n.train_no, freed, n.journey_date))
        con.execute("UPDATE bookings SET status='CONFIRMED', seat_no=? WHERE pnr=?", (freed, n.pnr))
        con.execute("DELETE FROM waiting_list WHERE booking_id=(SELECT id FROM bookings WHERE pnr=?)", (n.pnr,))
        flash("Seat released successfully. The first passenger from the waiting list has been confirmed.", "success")
    else:
        flash("Seat released successfully.", "success")
    con.commit()
    return redirect(url_for("my_bookings", tab="CANCELLED"))

@app.route("/waiting-list")
@login_required
def waiting_list():
    groups = []
    for (tid, jd), s in sorted(STRUCT.items(), key=lambda x: x[0][1]):
        if len(s["q"]):
            groups.append({"train": s["q"].front.train_no, "date": jd, "q": s["q"].to_list()})
    return render_template("waiting_list.html", groups=groups)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        email, phone = request.form.get("email", "").strip(), request.form.get("phone", "").strip()
        if "@" not in email or not (phone.isdigit() and len(phone) == 10):
            flash("Enter a valid email and 10-digit phone number.", "error")
        else:
            db().execute("UPDATE users SET email=?, phone=? WHERE id=?", (email, phone, session["uid"]))
            db().commit()
            flash("Profile updated.", "success")
        return redirect(url_for("profile"))
    u = db().execute("SELECT * FROM users WHERE id=?", (session["uid"],)).fetchone()
    return render_template("profile.html", u=u)

init_db()
load_structures()

if __name__ == "__main__":
    app.run(debug=True)
