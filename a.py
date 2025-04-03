import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import random
from datetime import datetime, timedelta
import re

BG_COLOR = "#f5f5f5"
PRIMARY_COLOR = "#34495e"
SECONDARY_COLOR = "#3498db"
ACCENT_COLOR = "#e74c3c"
TEXT_COLOR = "#2c3e50"
FONT = ("Segoe UI", 10)
HEADER_FONT = ("Segoe UI", 14, "bold")
BUTTON_STYLE = {"bg": SECONDARY_COLOR, "fg": "white", "font": FONT, "borderwidth": 1}
ENTRY_STYLE = {"font": FONT, "borderwidth": 1, "relief": "solid"}


class AuthManager:
    def __init__(self, db):
        self.email = []
        self.password = []
        self.db = db

    def valid_email(self, email):
        return email in self.email

    def valid_password(self, password):
        return password in self.password

    def hash_password(self, password, salt="", rounds=10):
        new_password = password + salt
        hashed_value = 2166136261
        for i in range(rounds):
            for characters in new_password:
                hashed_value = ((hashed_value << 5) + hashed_value) ^ ord(characters)
                hashed_value &= 0xFFFFFFFF
        return format(hashed_value, '08x') # returns in hex

    def generate_salt(self, length=8):
        characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        salt = ""
        for i in range(length):
            character = random.choice(characters)
            salt = salt + character
        return salt

    def login_check(self, email, password):
        customer = self.db.fetch_customer_email(email)
        if customer:
            hash = customer[4]
            salt = customer[5]
            hashed_password = self.hash_password(password, salt)
            return hashed_password == hash
        return False

    def staff_check(self, Staff_Number):
        if Staff_Number == "admin":
            return True
        staff = self.db.fetch_staff_number(Staff_Number)
        if staff:
            return True
        else:
            return False


class DatabaseManager:
    def __init__(self):
        self.connection = sqlite3.connect("barberdb.db")
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Customer (
            CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
            Surname TEXT,
            FirstName TEXT,
            Email TEXT,
            Hashed_Password TEXT,
            Salt TEXT,
            Date_Of_Birth TEXT)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Haircut (
            HaircutID INTEGER PRIMARY KEY AUTOINCREMENT,
            Haircut_Name TEXT,
            Price REAL,
            Estimated_Time INTEGER)''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Booking (
                BookingID INTEGER PRIMARY KEY,
                Date TEXT,
                Time TEXT,
                CustomerID INTEGER,
                HaircutID INTEGER,
                Locked BOOLEAN DEFAULT 0,
                Duration TEXT,
                ExpiryTime TEXT,
                FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID),
                FOREIGN KEY (HaircutID) REFERENCES Haircut(HaircutID)
                UNIQUE(Date, Time) 
            )
        ''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Staff (
            StaffID INTEGER PRIMARY KEY AUTOINCREMENT, 
            Email TEXT,
            Staff_Number TEXT)''')
        self.insert_admin()

    def insert_admin(self):
        self.cursor.execute("SELECT * FROM Staff WHERE Email=?", ('admin',))
        admin = self.cursor.fetchone()

        if not admin:
            self.cursor.execute('''INSERT INTO Staff (Email, Staff_Number) VALUES (?, ?)''', ('admin', 'admin'))
            self.connection.commit()

    def check_table(self):
        self.cursor.execute("PRAGMA table_info(Customer);")
        ys = self.cursor.fetchall()
        print(ys)

    def get_peak_hours(self, days):
        self.cursor.execute('''
            SELECT 
                strftime('%H:00', Time) AS Hour,
                COUNT(*) AS Bookings
            FROM Booking
            WHERE Date >= date('now', '-' || ? || ' DAYS')
            AND Locked = 1
            GROUP BY Hour
            ORDER BY Bookings DESC
        ''', (days,))
        return self.cursor.fetchall()

    def get_revenue_breakdown(self, period):
        self.cursor.execute(f'''
            SELECT 
                strftime('%Y-%m', Date) AS Period,
                Haircut.Haircut_Name,
                SUM(Haircut.Price) AS Revenue,
                COUNT(*) AS Bookings
            FROM Booking
            JOIN Haircut ON Booking.HaircutID = Haircut.HaircutID
            WHERE Date >= date('now', '-' || ? || ' DAYS')
            GROUP BY Period, Haircut.HaircutID
            ORDER BY Period DESC, Revenue DESC
        ''', (period,))
        return self.cursor.fetchall()

    def get_popular_haircuts(self, days):
        self.cursor.execute('''
            SELECT 
                Haircut.Haircut_Name,
                COUNT(*) AS Bookings
            FROM Booking
            JOIN Haircut ON Booking.HaircutID = Haircut.HaircutID
            WHERE Booking.Date >= date('now', '-' || ? || ' DAYS')
            GROUP BY Haircut.HaircutID
            ORDER BY Bookings DESC
        ''', (days,))
        return self.cursor.fetchall()

    def get_loyal_customers(self, min_visits):
        self.cursor.execute('''
            SELECT 
                Customer.FirstName || ' ' || Customer.Surname AS Customer,
                COUNT(*) AS Visits,
                GROUP_CONCAT(DISTINCT Haircut.Haircut_Name) AS Styles,
                MAX(Booking.Date) AS LastVisit
            FROM Booking
            JOIN Customer ON Booking.CustomerID = Customer.CustomerID
            JOIN Haircut ON Booking.HaircutID = Haircut.HaircutID
            GROUP BY Booking.CustomerID
            HAVING Visits >= ?
            ORDER BY Visits DESC
        ''', (min_visits,))
        return self.cursor.fetchall()

    def insert_customer(self, surname, firstname, email, hashed_password, salt, date_of_birth):
        self.cursor.execute('''INSERT INTO Customer (Surname, FirstName, Email, 
        Hashed_Password, Salt, Date_Of_Birth) VALUES (?, ?, ?, ?, ?, ?)''', (surname, firstname, email,
                                                                             hashed_password, salt, date_of_birth))
        self.connection.commit()

    def insert_haircut(self, haircutname, price, estimated_time):
        self.cursor.execute('''INSERT INTO Haircut (Haircut_Name, Price, Estimated_Time) VALUES (?,?,?)''',
                            (haircutname, price, estimated_time))

    def insert_booking(self, date, time, customerID, haircutID):
        try:
            self.cursor.execute("SELECT Estimated_Time FROM Haircut WHERE HaircutID=?", (haircutID,))
            duration = self.cursor.fetchone()[0]

            available = self.get_available_slots(date)
            if not available or time not in available:
                messagebox.showerror("Time slot is already booked or unavailable")

            self.cursor.execute("""
                INSERT INTO Booking (Date, Time, CustomerID, HaircutID, Locked, Duration) 
                VALUES (?, ?, ?, ?, 1, ?)
            """, (date, time, customerID, haircutID, duration))

            self.connection.commit()
            return True

        except:
            self.connection.rollback()
            messagebox.showerror("Error while trying to insert booking.")
            return False

    def fetch_customer_email(self, email):
        self.cursor.execute("SELECT * FROM Customer WHERE Email=?", (email,))
        return self.cursor.fetchone()

    def fetch_staff_number(self, Staff_Number):
        self.cursor.execute("SELECT * FROM Staff WHERE Staff_Number=?", (Staff_Number,))

    def fetch_all_customers(self):
        self.cursor.execute("SELECT * FROM Customer")
        return self.cursor.fetchall()

    def fetch_all_haircuts(self):
        self.cursor.execute("SELECT * FROM Haircut")
        return self.cursor.fetchall()

    def fetch_all_bookings(self):
        self.cursor.execute("SELECT * FROM Booking")
        return self.cursor.fetchall()

    def fetch_all_staff(self):
        self.cursor.execute("SELECT * FROM Staff")
        return self.cursor.fetchall()


    def fetch_all_data(self):
        customers = self.fetch_all_customers()
        haircuts = self.fetch_all_haircuts()
        bookings = self.fetch_all_bookings()
        staff = self.fetch_all_staff()
        return {"customers": customers, "haircuts": haircuts, "bookings": bookings, "staff": staff}

    def get_available_slots(self, date):
        try:
            self.cursor.execute("""
                SELECT Time FROM Booking 
                WHERE Date = ? 
                AND (
                    Locked = 1 
                    OR 
                    (ExpiryTime > datetime('now'))
            """, (date,))

            unavailable_times = {row[0] for row in self.cursor.fetchall()}

            all_slots = [f"{hour:02d}:00" for hour in range(9, 18)]

            available_slots = []
            for slot in all_slots:
                if slot not in unavailable_times:
                    available_slots.append(slot)
            return available_slots


        except:
            messagebox.showerror("There was an error finding available slots")
            return []

    def remove_customer(self, CustomerID):
        self.cursor.execute('''DELETE FROM Customer WHERE CustomerID = ?''', (CustomerID,))
        self.connection.commit()

    def remove_haircut(self, HaircutID):
        self.cursor.execute('''DELETE FROM Haircut WHERE HaircutID = ?''', (HaircutID,))
        self.connection.commit()

    def remove_booking(self, BookingID):
        self.cursor.execute('''DELETE FROM Booking WHERE BookingID = ?''', (BookingID,))
        self.connection.commit()

    def remove_expired_bookings(self):
        try:
            self.connection.execute("BEGIN TRANSACTION")
            self.cursor.execute('''
                DELETE FROM Booking 
                WHERE Locked = 0 AND ExpiryTime <= datetime('now')
            ''')
            self.connection.commit()
            return self.cursor.rowcount
        except:
            self.connection.rollback()
            messagebox.showerror("Error while removing expired bookings")
            return 0

    def merge_sort(self, records, sortby='id', ascending=True):
        fields = ['id', 'name', 'date']

        try:
            sort_index = fields.index(sortby)
        except ValueError:
            sort_index = 0

        if len(records) <= 1:
            return records

        mid = len(records) // 2
        leftlist = self.merge_sort(records[:mid], sortby, ascending)
        rightlist = self.merge_sort(records[mid:], sortby, ascending)

        sorted_list = []
        left_pointer = 0
        right_pointer = 0

        while left_pointer < len(leftlist) and right_pointer < len(rightlist):
            left_value = leftlist[left_pointer][sort_index]
            right_value = rightlist[right_pointer][sort_index]

            if sortby == 'date':
                try:
                    left_date = datetime.strptime(left_value, "%Y-%m-%d")
                    right_date = datetime.strptime(right_value, "%Y-%m-%d")
                    left_value = left_date
                    right_value = right_date
                except ValueError:
                    pass
            elif str(left_value).isdigit():
                left_value = int(left_value)
                right_value = int(right_value)

            if ascending:
                if left_value < right_value:
                    sorted_list.append(leftlist[left_pointer])
                    left_pointer += 1
                else:
                    sorted_list.append(rightlist[right_pointer])
                    right_pointer += 1
            else:
                if left_value > right_value:
                    sorted_list.append(leftlist[left_pointer])
                    left_pointer += 1
                else:
                    sorted_list.append(rightlist[right_pointer])
                    right_pointer += 1

        sorted_list.extend(leftlist[left_pointer:])
        sorted_list.extend(rightlist[right_pointer:])
        return sorted_list


class UIManager:
    def __init__(self, app, db):
        self.db = db
        self.app = app
        self.auth = app.auth
        self.current_user = None
        self.setup_styles()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('.', background=BG_COLOR, font=FONT)
        self.style.configure('TButton', background=SECONDARY_COLOR, foreground='white')
        self.style.map('TButton', background=[('active', PRIMARY_COLOR)])
        self.style.configure('Header.TLabel', font=HEADER_FONT)
        self.style.configure('TEntry', **ENTRY_STYLE)

    def create_window(self, title, size="400x400"):
        window = tk.Toplevel()
        window.title(title)
        window.geometry(size)
        window.configure(bg=BG_COLOR)
        return window

    def main_menu(self):
        window = self.create_window("Barber Booking System", "600x400")

        header = ttk.Label(window, text="Welcome to Barber Pro", style='Header.TLabel')
        header.pack(pady=40)

        btn_frame = ttk.Frame(window)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="Login", width=15,
                   command=lambda: [window.destroy(), self.app.login()]).pack(pady=10)
        ttk.Button(btn_frame, text="Register", width=15,
                   command=lambda: [window.destroy(), self.app.register()]).pack(pady=10)

        window.mainloop()

    def show_database(self):
        def sort_bookings(sort_by='date', ascending=True):
            all_bookings = self.db.fetch_all_bookings()
            booking_data = []

            for booking in all_bookings:
                booking_data.append((booking[0], f"{booking[1]} {booking[2]}", booking[1]))

            sorted_bookings = self.db.merge_sort(
                booking_data,
                sortby=sort_by,
                ascending=ascending
            )

            booking_box.delete(0, tk.END)
            for sorted_booking in sorted_bookings:
                full_booking = None
                for booking in all_bookings:
                    if booking[0] == sorted_booking[0]:
                        full_booking = booking
                        break

                if full_booking:
                    booking_text = (
                        f"BookingID: {full_booking[0]}, Date: {full_booking[1]}, "
                        f"Time: {full_booking[2]}, Customer: {full_booking[3]}, "
                        f"Haircut: {full_booking[4]}, Locked: {full_booking[5]}"
                    )
                    booking_box.insert(tk.END, booking_text)
        if self.staff_login():
            data = self.db.fetch_all_data()
            window = self.create_window("Database Contents", "1200x800")

            notebook = ttk.Notebook(window)
            notebook.pack(fill='both', expand=True)

            cust_frame = ttk.Frame(notebook)
            notebook.add(cust_frame, text="Customers")

            customer_list = tk.Listbox(cust_frame, width=120, height=30, font=FONT)
            customer_list.pack(side='left', fill='both', expand=True, padx=10, pady=10)

            scroll_cust = ttk.Scrollbar(cust_frame, orient='vertical', command=customer_list.yview)
            scroll_cust.pack(side='right', fill='y')
            customer_list.config(yscrollcommand=scroll_cust.set)

            haircut_frame = ttk.Frame(notebook)
            notebook.add(haircut_frame, text="Haircuts")

            haircut_box = tk.Listbox(haircut_frame, width=120, height=30, font=FONT)
            haircut_box.pack(side='left', fill='both', expand=True, padx=10, pady=10)

            scroll_hair = ttk.Scrollbar(haircut_frame, orient='vertical', command=haircut_box.yview)
            scroll_hair.pack(side='right', fill='y')
            haircut_box.config(yscrollcommand=scroll_hair.set)

            booking_frame = ttk.Frame(notebook)
            notebook.add(booking_frame, text="Bookings")

            filter_frame = ttk.Frame(booking_frame)
            filter_frame.pack(fill='x', pady=5)

            ttk.Label(filter_frame, text="Filter by Date (YYYY-MM-DD):").pack(side='left', padx=5)
            date_filter_entry = ttk.Entry(filter_frame, width=12)
            date_filter_entry.pack(side='left', padx=5)

            ttk.Button(filter_frame, text="Apply Filter",
                       command=lambda: self.filter_bookings_by_date(booking_box, date_filter_entry.get())).pack(side='left',
                                                                                                                padx=5)

            ttk.Button(filter_frame, text="Clear Filter",
                       command=lambda: self.load_all_bookings(booking_box)).pack(side='left', padx=5)

            sort_frame = ttk.Frame(booking_frame)
            sort_frame.pack(fill='x', pady=5)

            ttk.Button(sort_frame, text="Sort by Date (Oldest)",
                       command=lambda: sort_bookings('date', True)).pack(side='left', padx=5)

            ttk.Button(sort_frame, text="Sort by Date (Newest)",
                       command=lambda: sort_bookings('date', False)).pack(side='left', padx=5)

            booking_box = tk.Listbox(booking_frame, width=120, height=30, font=FONT)
            booking_box.pack(side='left', fill='both', expand=True, padx=10, pady=10)

            scroll_book = ttk.Scrollbar(booking_frame, orient='vertical', command=booking_box.yview)
            scroll_book.pack(side='right', fill='y')
            booking_box.config(yscrollcommand=scroll_book.set)

            staff_frame = ttk.Frame(notebook)
            notebook.add(staff_frame, text="Staff")

            staff_box = tk.Listbox(staff_frame, width=120, height=30, font=FONT)
            staff_box.pack(side='left', fill='both', expand=True, padx=10, pady=10)

            scroll_staff = ttk.Scrollbar(staff_frame, orient='vertical', command=staff_box.yview)
            scroll_staff.pack(side='right', fill='y')
            staff_box.config(yscrollcommand=scroll_staff.set)

            for customer in data["customers"]:
                customer_list.insert(tk.END,
                                     f"ID: {customer[0]}, Name: {customer[1]} {customer[2]}, "
                                     f"Email: {customer[3]}, DOB: {customer[6]}"
                                     )

            for haircut in data["haircuts"]:
                haircut_box.insert(tk.END,
                                   f"ID: {haircut[0]}, Name: {haircut[1]}, "
                                   f"Price: £{haircut[2]:.2f}, Duration: {haircut[3]}"
                                   )

            self.load_all_bookings(booking_box)

            if "staff" in data:
                for staff in data["staff"]:
                    staff_box.insert(tk.END,
                                     f"ID: {staff[0]}, Email: {staff[1]}, Staff Number: {staff[2]}"
                                     )



            btn_frame = ttk.Frame(window)
            btn_frame.pack(fill='x', pady=10)

            ttk.Button(btn_frame, text="Close", command=window.destroy).pack(side='right', padx=5)

    def filter_bookings_by_date(self, booking_box, date_filter):
        try:
            datetime.strptime(date_filter, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("error", "Please enter in YYYY-MM-DD")
            return

        all_bookings = self.db.fetch_all_bookings()
        booking_box.delete(0, tk.END)

        found = False
        for booking in all_bookings:
            if booking[1] == date_filter:
                booking_box.insert(tk.END,
                                   f"BookingID: {booking[0]}, Date: {booking[1]}, Time: {booking[2]}, "
                                   f"Customer: {booking[3]}, Haircut: {booking[4]}, Locked: {booking[5]}"
                                   )
                found = True

        if not found:
            booking_box.insert(tk.END, "No bookings found for this date")

    def load_all_bookings(self, booking_box):
        booking_box.delete(0, tk.END)
        for booking in self.db.fetch_all_bookings():
            booking_box.insert(tk.END,
                               f"BookingID: {booking[0]}, Date: {booking[1]}, Time: {booking[2]}, "
                               f"Customer: {booking[3]}, Haircut: {booking[4]}, Locked: {booking[5]}"
                               )

    def register(self):
        def validate_date(date_str):
            try:
                if len(date_str) != 10:
                    return False
                day, month, year = map(int, date_str.split('/'))
                if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2025):
                    return False
                return True
            except:
                return False

        def create():
            new_email = email_entry.get()
            new_password = password_entry.get()
            date_of_birth = dateofbirth_entry.get()

            if not new_email or not new_password:
                messagebox.showerror("Error", "Email and Password must be entered.")
                return

            if not validate_date(date_of_birth):
                messagebox.showerror("Error", "Date must be in format DD/MM/YYYY")
                return

            salt = self.app.auth.generate_salt()
            hashed_password = self.auth.hash_password(new_password, salt)
            self.app.db.insert_customer(surname_entry.get(), firstname_entry.get(), new_email,
                                        hashed_password, salt, date_of_birth)

            self.app.auth.email.append(new_email)
            self.app.auth.password.append(hashed_password)
            register_widget.destroy()
            self.app.main_menu()

        register_widget = self.create_window("Register", "450x350")

        form_frame = ttk.Frame(register_widget)
        form_frame.pack(pady=20, padx=20, fill='both', expand=True)

        labels = ["Email:", "Password:", "Surname:", "First Name:", "Date of Birth:"]
        entries = []

        for i, text in enumerate(labels):
            ttk.Label(form_frame, text=text).grid(row=i, column=0, pady=5, sticky='e')
            entry = ttk.Entry(form_frame)
            entry.grid(row=i, column=1, pady=5, padx=5, sticky='ew')
            entries.append(entry)

        email_entry, password_entry, surname_entry, firstname_entry, dateofbirth_entry = entries
        dateofbirth_entry.insert(0, "DD/MM/YYYY")

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=5, columnspan=2, pady=15)

        ttk.Button(btn_frame, text="Create Account", command=create).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Back",
                   command=lambda: [register_widget.destroy(), self.app.main_menu()]).pack(side='left', padx=5)

    def staff_login(self):
        window = self.create_window("Staff Login")

        ttk.Label(window, text="Enter your ID").pack(pady=10)
        staffID_entry = ttk.Entry(window)
        staffID_entry.pack(pady=5)

        login = [False]
        def staff_check():
            if self.auth.staff_check(staffID_entry.get()):
                login[0] = True
                window.destroy()
            else:
                messagebox.showerror("Error", "Invalid Staff ID")


        btn_frame = ttk.Frame(window)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="Login", command=staff_check).pack(side='left',padx=5)
        ttk.Button(btn_frame, text="Back", command=window.destroy).pack(side='left',padx=5)

        window.wait_window()

        return login[0]
    def login(self):
        def attempt_login():
            email = email_entry.get()
            password = password_entry.get()
            if email == "admin" and password == "admin":
                messagebox.showinfo("Success", "Login successful!")
                login_widget.destroy()
                self.app.main_page()

            if self.auth.login_check(email, password):
                self.current_user = self.db.fetch_customer_email(email)
                messagebox.showinfo("Success", "Login successful!")
                login_widget.destroy()
                self.app.main_page()
            else:
                messagebox.showerror("Error", "Invalid email or password.")

        login_widget = self.create_window("Login")

        form_frame = ttk.Frame(login_widget)
        form_frame.pack(pady=20, padx=20, fill='both', expand=True)

        ttk.Label(form_frame, text="Email:").grid(row=0, column=0, pady=5, sticky='e')
        email_entry = ttk.Entry(form_frame)
        email_entry.grid(row=0, column=1, pady=5, padx=5, sticky='ew')

        ttk.Label(form_frame, text="Password:").grid(row=1, column=0, pady=5, sticky='e')
        password_entry = ttk.Entry(form_frame, show="*")
        password_entry.grid(row=1, column=1, pady=5, padx=5, sticky='ew')

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=2, columnspan=2, pady=15)

        ttk.Button(btn_frame, text="Login", command=attempt_login).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Back",
                   command=lambda: [login_widget.destroy(), self.app.main_menu()]).pack(side='left', padx=5)

    def pricing(self):
        window = self.create_window("Pricing", "600x400")

        self.db.cursor.execute("SELECT * FROM Haircut")
        haircuts = self.db.cursor.fetchall()

        tree = ttk.Treeview(window, columns=("Name", "Price", "Duration"), show="headings")
        tree.heading("Name", text="Haircut Name")
        tree.heading("Price", text="Price (£)")
        tree.heading("Duration", text="Duration")

        for haircut in haircuts:
            tree.insert("", tk.END, values=(haircut[1], f"£{haircut[2]:.2f}", haircut[3]))

        tree.pack(fill='both', expand=True, padx=10, pady=10)

        ttk.Button(window, text="Close", command=window.destroy).pack(pady=10)

    def process_booking(self, selected_time, haircut_name, card_number, card_cvc, expiry_date):
        current_time = datetime.now().strftime("%H:%M")
        if selected_time < current_time:
            messagebox.showerror("Error", "Cannot book past time slots")
            return False

        if not self.validate_payment(card_number, card_cvc, expiry_date):
            return False

        try:
            self.db.connection.execute("BEGIN TRANSACTION")

            self.db.cursor.execute(
                "SELECT HaircutID, Price, Estimated_Time FROM Haircut WHERE Haircut_Name = ?",
                (haircut_name,)
            )
            haircut = self.db.cursor.fetchone()

            if not haircut:
                messagebox.showerror("Error", "Selected haircut not found")
                self.db.connection.rollback()
                return False

            haircut_id, price, duration = haircut
            customer_id = self.get_current_customer_id()
            booking_date = datetime.now().strftime("%Y-%m-%d")

            self.db.cursor.execute("""
                   SELECT 1 FROM Booking 
                   WHERE Date = ? AND Time = ? 
                   AND (
                       Locked = 1
                       OR 
                       (ExpiryTime > datetime('now'))
                   )
               """, (booking_date, selected_time))

            if self.db.cursor.fetchone():
                messagebox.showerror("Error", "This time slot is no longer available")
                self.db.connection.rollback()
                return False

            expiry_time = (datetime.now() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            self.db.cursor.execute("""
                INSERT INTO Booking (Date, Time, CustomerID, HaircutID, Locked, Duration, ExpiryTime)
                VALUES (?, ?, ?, ?, 0, ?, ?)
            """, (booking_date, selected_time, customer_id, haircut_id, duration, expiry_time))

            payment_success = True

            if payment_success:
                self.db.cursor.execute("""
                    UPDATE Booking 
                    SET Locked = 1, ExpiryTime = NULL 
                    WHERE BookingID = last_insert_rowid()
                """)
                self.db.connection.commit()

                messagebox.showinfo(
                    "Success",
                    f"Booking confirmed for {selected_time}!\n"
                    f"Service: {haircut_name} ({duration} minutes)\n"
                    f"Amount: £{price:.2f}"
                )
                return True
            else:
                self.db.connection.rollback()
                return False

        except:
            self.db.connection.rollback()
            messagebox.showerror("error",
                                 "something went wrong while booking, please try again and check credentials")
            return False

    def validate_payment(self, card_number, card_cvc, expiry_date):
        if not (card_number.isdigit() and len(card_number) >= 13):
            messagebox.showerror("Error", "Invalid card number (must be at least 13 digits)")
            return False

        if not (card_cvc.isdigit() and len(card_cvc) == 3):
            messagebox.showerror("Error", "Invalid CVC (must be 3 digits)")
            return False

        try:
            month, year = expiry_date.split('/')
            if not (1 <= int(month) <= 12):
                raise ValueError
            if int(year) < datetime.now().year % 100:
                raise ValueError
        except:
            messagebox.showerror("Error", "Invalid expiry date (use MM/YY format)")
            return False

        return True

    def get_current_customer_id(self):
        if self.current_user:
            return self.current_user[0]
        return None

    def create_booking_page(self, selected_time):
        window = self.create_window("Confirm Booking", "500x450")

        self.db.cursor.execute("SELECT Haircut_Name, Price FROM Haircut")
        haircuts = self.db.cursor.fetchall()

        if not haircuts:
            ttk.Label(window, text="No services available").pack(pady=20)
            ttk.Button(window, text="Close", command=window.destroy).pack(pady=10)
            return

        main_frame = ttk.Frame(window)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(main_frame,
                  text=f"Confirm Booking for {selected_time}",
                  style='Header.TLabel').pack(pady=10)

        haircut_var = tk.StringVar(value=haircuts[0][0])
        ttk.Label(main_frame, text="Select Service:").pack()
        haircut_menu = ttk.OptionMenu(main_frame, haircut_var, *[h[0] for h in haircuts])
        haircut_menu.pack(fill='x', pady=5)

        payment_frame = ttk.LabelFrame(main_frame, text="Payment Details")
        payment_frame.pack(fill='x', pady=10)

        ttk.Label(payment_frame, text="Card Number:").grid(row=0, column=0, sticky='e')
        card_entry = ttk.Entry(payment_frame)
        card_entry.grid(row=0, column=1, pady=5, sticky='ew')

        ttk.Label(payment_frame, text="Expiry (MM/YY):").grid(row=1, column=0, sticky='e')
        expiry_entry = ttk.Entry(payment_frame)
        expiry_entry.grid(row=1, column=1, pady=5, sticky='ew')

        ttk.Label(payment_frame, text="CVC:").grid(row=2, column=0, sticky='e')
        cvc_entry = ttk.Entry(payment_frame, width=5)
        cvc_entry.grid(row=2, column=1, pady=5, sticky='w')

        def on_confirm():
            selected_haircut = haircut_var.get()
            if self.process_booking(
                    selected_time,
                    selected_haircut,
                    card_entry.get(),
                    cvc_entry.get(),
                    expiry_entry.get()
            ):
                window.destroy()
                self.main_menu()

        ttk.Button(main_frame, text="Confirm Booking", command=on_confirm).pack(pady=15)

    def analytics(self):
        if self.staff_login():
            window = self.create_window("Analytics Dashboard", "1200x800")
            window.grid_columnconfigure(0, weight=1)
            window.grid_columnconfigure(1, weight=1)
            window.grid_rowconfigure(0, weight=1)
            window.grid_rowconfigure(1, weight=1)
            window.grid_rowconfigure(2, weight=0)

            peak_frame = ttk.LabelFrame(window, text="Peak Booking Hours", padding=10)
            peak_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
            self.peak_canvas = tk.Canvas(peak_frame, bg=BG_COLOR, highlightthickness=0, width=600, height=300)
            self.peak_canvas.pack(fill="both", expand=True)

            revenue_frame = ttk.LabelFrame(window, text="Revenue Analysis", padding=10)
            revenue_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=5)
            self.revenue_tree = ttk.Treeview(revenue_frame, columns=("Period", "Service", "Revenue", "Bookings"),
                                             show="headings")
            for col in ["Period", "Service", "Revenue", "Bookings"]:
                self.revenue_tree.heading(col, text=col)
                self.revenue_tree.column(col, width=120)
            scrollbar = ttk.Scrollbar(revenue_frame, orient="vertical", command=self.revenue_tree.yview)
            self.revenue_tree.configure(yscrollcommand=scrollbar.set)
            self.revenue_tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            popularity_frame = ttk.LabelFrame(window, text="Service Popularity", padding=10)
            popularity_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
            self.popularity_text = tk.Text(popularity_frame, bg=BG_COLOR, font=FONT, wrap="word")
            scrollbar = ttk.Scrollbar(popularity_frame, command=self.popularity_text.yview)
            self.popularity_text.configure(yscrollcommand=scrollbar.set)
            self.popularity_text.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            loyalty_frame = ttk.LabelFrame(window, text="Top Customers", padding=10)
            loyalty_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=5)
            self.loyalty_tree = ttk.Treeview(loyalty_frame, columns=("Customer", "Visits", "Styles"), show="headings")
            for col in ["Customer", "Visits", "Styles"]:
                self.loyalty_tree.heading(col, text=col)
                self.loyalty_tree.column(col, width=120)
            scrollbar = ttk.Scrollbar(loyalty_frame, command=self.loyalty_tree.yview)
            self.loyalty_tree.configure(yscrollcommand=scrollbar.set)
            self.loyalty_tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            control_frame = ttk.Frame(window)
            control_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)

            ttk.Label(control_frame, text="Days to analyze:").pack(side="left", padx=5)
            self.days_var = tk.StringVar(value="30")
            days_combo = ttk.Combobox(control_frame, textvariable=self.days_var,
                                      values=["7", "14", "30", "60", "90"], width=5)
            days_combo.pack(side="left", padx=5)

            ttk.Button(control_frame, text="Refresh",
                       command=lambda: self.refresh_analytics()).pack(side="left", padx=10)

            self.days_var.set("30")
            self.refresh_analytics()

            self.refresh_analytics()

    def refresh_analytics(self):
        try:
            days = int(self.days_var.get())
        except ValueError:
            days = 30
            self.days_var.set("30")

        bookings = self.db.fetch_all_bookings()
        booking_data = []

        for b in bookings:
            booking_data.append((b[0], f"{b[1]} {b[2]}", b[1]))

        sorted_bookings = self.db.merge_sort(
            booking_data,
            sortby='date',
            ascending=False
        )

        for item in self.revenue_tree.get_children():
            self.revenue_tree.delete(item)

        revenue_data = self.db.get_revenue_breakdown(days)

        for row in revenue_data:
            self.revenue_tree.insert("", "end", values=row)

        self.popularity_text.config(state="normal")
        self.popularity_text.delete(1.0, "end")

        popularity_data = self.db.get_popular_haircuts(days)
        total = 1

        if popularity_data:
            total = 0
            for item in popularity_data:
                total += item[1]

        for haircut, count in popularity_data:
            percentage = (count / total) * 100
            bar_length = int(percentage / 5)
            bar = "■" * bar_length

            max_count = max(item[1] for item in popularity_data)
            if count == max_count:
                style = "bold"
            else:
                style = "normal"

            text_line = f"{haircut.ljust(15)} {bar} {percentage:.1f}% ({count} bookings)\n"
            self.popularity_text.insert("end", text_line, style)

        self.popularity_text.tag_config("bold", font=(FONT[0], FONT[1], "bold"))
        self.popularity_text.config(state="disabled")

        for item in self.loyalty_tree.get_children():
            self.loyalty_tree.delete(item)

        loyalty_data = self.db.get_loyal_customers(3)

        for row in loyalty_data:
            self.loyalty_tree.insert("", "end", values=row[:3])
        try:
            days = int(self.days_var.get())
        except ValueError:
            days = 30
            self.days_var.set("30")

        self.refresh_peak_hours(days)

        for item in self.revenue_tree.get_children():
            self.revenue_tree.delete(item)
        revenue_data = self.db.get_revenue_breakdown(days)
        for row in revenue_data:
            self.revenue_tree.insert("", "end", values=row)

        self.popularity_text.config(state="normal")
        self.popularity_text.delete(1.0, "end")
        popularity_data = self.db.get_popular_haircuts(days)
        total = sum(item[1] for item in popularity_data) if popularity_data else 1

        for haircut, count in popularity_data:
            percentage = (count / total) * 100
            bar = "■" * int(percentage / 5)
            self.popularity_text.insert("end",
                                        f"{haircut.ljust(15)} {bar} {percentage:.1f}% ({count} bookings)\n",
                                        ("bold" if count == max(item[1] for item in popularity_data) else "normal"))

        self.popularity_text.tag_config("bold", font=(FONT[0], FONT[1], "bold"))
        self.popularity_text.config(state="disabled")

        for item in self.loyalty_tree.get_children():
            self.loyalty_tree.delete(item)
        loyalty_data = self.db.get_loyal_customers(3)
        for row in loyalty_data:
            self.loyalty_tree.insert("", "end", values=row[:3])

    def refresh_peak_hours(self, days):
        self.peak_canvas.delete("all")
        peak_data = self.db.get_peak_hours(days)

        if not peak_data:
            self.peak_canvas.create_text(300, 150, text="No booking data", fill=TEXT_COLOR)
            return

        canvas_width = 600
        canvas_height = 300

        max_bookings = max(item[1] for item in peak_data)
        left_margin = 50
        right_margin = 30
        bottom_margin = 40
        top_margin = 20
        available_width = canvas_width - left_margin - right_margin
        available_height = canvas_height - bottom_margin - top_margin

        num_bars = len(peak_data)
        bar_width = min(30, available_width / num_bars - 5)
        gap = (available_width - (num_bars * bar_width)) / (num_bars + 1)

        self.peak_canvas.create_line(
            left_margin, canvas_height - bottom_margin,
                         canvas_width - right_margin, canvas_height - bottom_margin,
            width=2
        )
        self.peak_canvas.create_line(
            left_margin, canvas_height - bottom_margin,
            left_margin, top_margin,
            width=2
        )

        for i, (hour, bookings) in enumerate(peak_data):
            x0 = left_margin + gap + i * (bar_width + gap)
            y0 = canvas_height - bottom_margin
            bar_height = (bookings / max_bookings) * available_height if max_bookings > 0 else 0
            y1 = y0 - bar_height

            self.peak_canvas.create_rectangle(
                x0, y1, x0 + bar_width, y0,
                fill=SECONDARY_COLOR, outline=PRIMARY_COLOR, width=1
            )
            self.peak_canvas.create_rectangle(
                x0 + 2, y1 + 2, x0 + bar_width + 2, y0 + 2,
                fill=SECONDARY_COLOR, outline="", width=0
            )

            hour_label = self.peak_canvas.create_text(
                x0 + bar_width / 2, y0 + 10,
                text=hour, fill=TEXT_COLOR, angle=45, anchor="n"
            )

            self.peak_canvas.create_text(
                x0 + bar_width / 2, y1 - 10,
                text=str(bookings), fill=PRIMARY_COLOR, font=(FONT[0], FONT[1], "bold")
            )

        for i in range(0, 6):
            y = canvas_height - bottom_margin - (i * (available_height / 5))
            value = int(max_bookings * (i / 5))
            self.peak_canvas.create_text(
                left_margin - 10, y,
                text=str(value), fill=TEXT_COLOR, anchor="e"
            )
            self.peak_canvas.create_line(
                left_margin - 5, y,
                left_margin, y,
                fill=TEXT_COLOR
            )

        self.peak_canvas.create_text(
            canvas_width / 2, 15,
            text=f"Peak Booking Hours (Last {days} Days)",
            fill=TEXT_COLOR, font=HEADER_FONT
        )

    def bookings(self):
        def on_date_select():
            selected_year = year_spinbox.get()
            selected_month = month_spinbox.get().zfill(2)
            selected_day = day_spinbox.get().zfill(2)
            selected_date = f"{selected_year}-{selected_month}-{selected_day}"

            try:
                self.db.cursor.execute("""
                            SELECT Time FROM Booking 
                            WHERE Date = ? 
                            AND (Locked = 1 OR (ExpiryTime > datetime('now')))
                        """, (selected_date,))

                unavailable_times = [row[0] for row in self.db.cursor.fetchall()]
                all_slots = [f"{hour:02d}:00" for hour in range(9, 18)]
                available_slots = [slot for slot in all_slots if slot not in unavailable_times]

                time_listbox.delete(0, tk.END)
                for time in available_slots:
                    time_listbox.insert(tk.END, time)
            except ValueError:
                messagebox.showerror("Error", "Invalid date selected")

        def select_time():
            selected = time_listbox.curselection()
            if not selected:
                messagebox.showerror("Error", "Please select a time slot")
                return None
            return time_listbox.get(selected[0])

        window = self.create_window("Book an Appointment", "600x500")

        main_frame = ttk.Frame(window)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="Select Appointment Date", style='Header.TLabel').pack(pady=10)

        date_frame = ttk.Frame(main_frame)
        date_frame.pack(pady=10)

        ttk.Label(date_frame, text="Year:").grid(row=0, column=0, padx=5)
        year_spinbox = ttk.Spinbox(date_frame, from_=2023, to=2025, width=5)
        year_spinbox.grid(row=0, column=1, padx=5)
        year_spinbox.set(datetime.now().year)

        ttk.Label(date_frame, text="Month:").grid(row=0, column=2, padx=5)
        month_spinbox = ttk.Spinbox(date_frame, from_=1, to=12, width=3)
        month_spinbox.grid(row=0, column=3, padx=5)
        month_spinbox.set(datetime.now().month)

        ttk.Label(date_frame, text="Day:").grid(row=0, column=4, padx=5)
        day_spinbox = ttk.Spinbox(date_frame, from_=1, to=31, width=3)
        day_spinbox.grid(row=0, column=5, padx=5)
        day_spinbox.set(datetime.now().day)

        ttk.Button(main_frame, text="Check Availability",
                   command=on_date_select).pack(pady=10)

        ttk.Label(main_frame, text="Available Times:").pack()

        time_frame = ttk.Frame(main_frame)
        time_frame.pack(fill='x', pady=10)

        time_listbox = tk.Listbox(time_frame, height=8, font=FONT)
        time_listbox.pack(side='left', fill='both', expand=True)

        scrollbar = ttk.Scrollbar(time_frame, orient='vertical', command=time_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        time_listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Select",
                   command=lambda: [
                       (time_selected := select_time()) and
                       [window.destroy(), self.create_booking_page(time_selected)]
                   ]).pack(side='left', padx=5)

        ttk.Button(btn_frame, text="Back",
                   command=lambda: [window.destroy(), self.app.main_page()]).pack(side='left', padx=5)



class BarberApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.db = DatabaseManager()
        self.auth = AuthManager(self.db)
        self.ui = UIManager(self, self.db)
        self.db.remove_expired_bookings()
        self.schedule_cleanup()

    def schedule_cleanup(self):
        def cleanup():
            expired = self.db.remove_expired_bookings()
            if expired:
                print(f"Cleaned up {expired} expired bookings")
            self.root.after(30000, cleanup)

        self.root.after(30000, cleanup)

    def main_menu(self):
        self.ui.main_menu()

    def login(self):
        self.ui.login()

    def register(self):
        self.ui.register()

    def main_page(self):
        self.main_page_window = MainPageWindow(self, self.ui)
        self.main_page_window.show()


class BookingManager:
    def __init__(self, db_connection):
        self.db = db_connection
        self.cursor = db_connection.cursor()

    def lock_time_slot(self, date, time):
        lock_duration = 10 * 60
        current_time = time.time()
        lock_end_time = current_time + lock_duration

        self.cursor.execute('''
            UPDATE Booking 
            SET Locked = 1, LockEndTime = ? 
            WHERE Date = ? AND Time = ?
        ''', (lock_end_time, date, time))
        self.db.connection.commit()


    def book_slot(self, date, time, customer_id, haircut_id):
        available_slots = self.db.get_available_slots(date)
        if time not in available_slots:
            raise Exception(f"The time slot {time} is not available.")

        self.cursor.execute('''
            INSERT INTO Booking (Date, Time, CustomerID, HaircutID, Locked) 
            VALUES (?, ?, ?, ?, 0)
        ''', (date, time, customer_id, haircut_id))
        self.db.connection.commit()
        return f"Booking successful for {time} on {date}."


class BaseWindow:
    def __init__(self):
        self.window = tk.Toplevel()
        self.window.configure(bg=BG_COLOR)

    def show(self):
        self.window.deiconify()
        self.window.mainloop()

    def close(self):
        self.window.destroy()

class MainMenuWindow(BaseWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.window.title("Barber Booking System")
        self.window.geometry("600x400")
        self.setup_ui()

    def setup_ui(self):
        header = ttk.Label(self.window, text="Welcome to Barber Pro", style='Header.TLabel')
        header.pack(pady=40)

        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="Login", width=15,
                   command=lambda: [self.close(), self.app.login()]).pack(pady=10)
        ttk.Button(btn_frame, text="Register", width=15,
                   command=lambda: [self.close(), self.app.register()]).pack(pady=10)

class MainPageWindow(BaseWindow):
    def __init__(self, app, ui):
        super().__init__()
        self.app = app
        self.ui = ui
        self.window.title("Barber Booking System")
        self.window.geometry("800x600")
        self.setup_ui()

    def setup_ui(self):
        header = ttk.Label(self.window, text="Main Menu", style='Header.TLabel')
        header.pack(pady=30)

        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(pady=30)

        ttk.Button(btn_frame, text="Book Appointment", width=20,
                   command=lambda: [self.close(), self.ui.bookings()]).grid(row=0, column=0, padx=10, pady=10)

        ttk.Button(btn_frame, text="View Pricing", width=20,
                   command=self.ui.pricing).grid(row=0, column=1, padx=10, pady=10)

        ttk.Button(btn_frame, text="View Database", width=20,
                   command=self.ui.show_database).grid(row=1, column=0, padx=10, pady=10)

        ttk.Button(btn_frame, text="Analytics", width=20,
                   command=self.ui.analytics).grid(row=1, column=1, padx=10, pady=10)

        ttk.Button(self.window, text="Logout",
                   command=lambda: [self.close(), self.app.main_menu()]).pack(side='bottom', pady=20)

class LoginWindow(BaseWindow):
    def __init__(self, app, auth):
        super().__init__()
        self.app = app
        self.auth = auth
        self.window.title("Login")
        self.setup_login_ui()

    def setup_login_ui(self):
        frame = ttk.Frame(self.window)
        frame.pack(pady=20)

        email_label = ttk.Label(frame, text="Email:")
        email_label.grid(row=0, column=0)
        self.email_entry = ttk.Entry(frame)
        self.email_entry.grid(row=0, column=1)

        password_label = ttk.Label(frame, text="Password:")
        password_label.grid(row=1, column=0)
        self.password_entry = ttk.Entry(frame, show="*")
        self.password_entry.grid(row=1, column=1)

        ttk.Button(frame, text="Login", command=self.attempt_login).grid(row=2, column=0)
        ttk.Button(frame, text="Back", command=self.back).grid(row=2, column=1)

    def attempt_login(self):
        email = self.email_entry.get()
        password = self.password_entry.get()

        if self.auth.login_check(email, password):
            messagebox.showinfo("Success", "Login successful!")
            self.close()
            self.app.main_page()
        else:
            messagebox.showerror("Error", "Invalid email or password.")

    def back(self):
        self.close()
        self.app.main_menu()

class RegisterWindow(BaseWindow):
    def __init__(self, app, auth, db):
        super().__init__()
        self.app = app
        self.auth = auth
        self.db = db
        self.window.title("Register")
        self.window.geometry("450x350")
        self.setup_ui()

    def setup_ui(self):
        form_frame = ttk.Frame(self.window)
        form_frame.pack(pady=20, padx=20, fill='both', expand=True)

        labels = ["Email:", "Password:", "Surname:", "First Name:", "Date of Birth:"]
        self.entries = []

        for i, text in enumerate(labels):
            ttk.Label(form_frame, text=text).grid(row=i, column=0, pady=5, sticky='e')
            entry = ttk.Entry(form_frame)
            entry.grid(row=i, column=1, pady=5, padx=5, sticky='ew')
            self.entries.append(entry)

        self.entries[-1].insert(0, "DD/MM/YYYY")

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=5, columnspan=2, pady=15)

        ttk.Button(btn_frame, text="Create Account", command=self.create_account).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Back", command=self.back).pack(side='left', padx=5)

    def validate_date(self, date_str):
        try:
            if len(date_str) != 10:
                return False
            day, month, year = map(int, date_str.split('/'))
            return 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2025
        except:
            return False

    def create_account(self):
        email, password, surname, firstname, dob = [e.get() for e in self.entries]

        if not email or not password:
            messagebox.showerror("Error", "Email and Password must be entered.")
            return

        if not self.validate_date(dob):
            messagebox.showerror("Error", "Date must be in format DD/MM/YYYY")
            return

        salt = self.auth.generate_salt()
        hashed_password = self.auth.hash_password(password, salt=salt)
        self.db.insert_customer(surname, firstname, email, hashed_password, salt, dob)

        self.auth.email.append(email)
        self.auth.password.append(hashed_password)
        self.close()
        self.app.main_menu()

    def back(self):
        self.close()
        self.app.main_menu()

class BookingWindow(BaseWindow):
    def __init__(self, app, ui, db):
        super().__init__()
        self.app = app
        self.ui = ui
        self.db = db
        self.window.title("Book an Appointment")
        self.window.geometry("600x500")
        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="Select Appointment Date", style='Header.TLabel').pack(pady=10)

        date_frame = ttk.Frame(main_frame)
        date_frame.pack(pady=10)

        ttk.Label(date_frame, text="Year:").grid(row=0, column=0, padx=5)
        self.year_spinbox = ttk.Spinbox(date_frame, from_=2023, to=2025, width=5)
        self.year_spinbox.grid(row=0, column=1, padx=5)
        self.year_spinbox.set(datetime.now().year)

        ttk.Label(date_frame, text="Month:").grid(row=0, column=2, padx=5)
        self.month_spinbox = ttk.Spinbox(date_frame, from_=1, to=12, width=3)
        self.month_spinbox.grid(row=0, column=3, padx=5)
        self.month_spinbox.set(datetime.now().month)

        ttk.Label(date_frame, text="Day:").grid(row=0, column=4, padx=5)
        self.day_spinbox = ttk.Spinbox(date_frame, from_=1, to=31, width=3)
        self.day_spinbox.grid(row=0, column=5, padx=5)
        self.day_spinbox.set(datetime.now().day)

        ttk.Button(main_frame, text="Check Availability",
                   command=self.on_date_select).pack(pady=10)

        ttk.Label(main_frame, text="Available Times:").pack()

        time_frame = ttk.Frame(main_frame)
        time_frame.pack(fill='x', pady=10)

        self.time_listbox = tk.Listbox(time_frame, height=8, font=FONT)
        self.time_listbox.pack(side='left', fill='both', expand=True)

        scrollbar = ttk.Scrollbar(time_frame, orient='vertical', command=self.time_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.time_listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Select", command=self.on_select).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Back", command=self.back).pack(side='left', padx=5)

    def on_date_select(self):
        selected_date = f"{self.year_spinbox.get()}-{self.month_spinbox.get().zfill(2)}-{self.day_spinbox.get().zfill(2)}"
        available_slots = self.db.get_available_slots(selected_date)

        self.time_listbox.delete(0, tk.END)
        for slot in available_slots:
            self.time_listbox.insert(tk.END, slot)

    def on_select(self):
        selected = self.time_listbox.curselection()
        if not selected:
            messagebox.showerror("Error", "Please select a time slot")
            return
        time_selected = self.time_listbox.get(selected[0])
        self.close()
        self.ui.create_booking_page(time_selected)

    def back(self):
        self.close()
        self.app.main_page()

class PricingWindow(BaseWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.window.title("Pricing")
        self.window.geometry("600x400")
        self.setup_ui()

    def setup_ui(self):
        self.db.cursor.execute("SELECT * FROM Haircut")
        haircuts = self.db.cursor.fetchall()

        tree = ttk.Treeview(self.window, columns=("Name", "Price", "Duration"), show="headings")
        tree.heading("Name", text="Haircut Name")
        tree.heading("Price", text="Price (£)")
        tree.heading("Duration", text="Duration")

        for haircut in haircuts:
            tree.insert("", tk.END, values=(haircut[1], f"£{haircut[2]:.2f}", haircut[3]))

        tree.pack(fill='both', expand=True, padx=10, pady=10)
        ttk.Button(self.window, text="Close", command=self.close).pack(pady=10)

class DatabaseWindow(BaseWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.window.title("Database Contents")
        self.window.geometry("1200x800")
        self.setup_ui()
        self.current_tab = None

    def remove(self):
        current_tab = self.tabs.tab(self.tabs.select(), "text")
        if current_tab == "Customers":
            selected_customer = self.customer_list.curselection()
            if not selected_customer:
                messagebox.showerror("Error", "Select a customer")
                return
            selected_customer_info = self.customer_list.get(selected_customer[0])

            CustomerID = re.search(r"ID: (\d+)", selected_customer_info)  # extracts ID
            try:
                if CustomerID:
                    CustomerID = int(CustomerID.group(1))  # gets rid of "ID:"
                    self.db.remove_customer(CustomerID)
                    messagebox.showinfo("Success", f"Customer ID {CustomerID} removed successfully.")
                    self.customer_list.delete(selected_customer[0])
            except:
                messagebox.showerror("Error", "Customer ID could not be extracted.")
        if current_tab == "Haircuts":
            selected_haircut = self.haircut_box.curselection()
            if not selected_haircut:
                messagebox.showerror("Error", "Select a haircut")
                return
            selected_haircut_info = self.haircut_box.get(selected_haircut[0])

            HaircutID = re.search(r"ID: (\d+)", selected_haircut_info)
            try:
                if HaircutID:
                    HaircutID = int(HaircutID.group(1))
                    self.db.remove_haircut(HaircutID)
                    messagebox.showinfo("Success", f"Haircut ID {HaircutID} removed successfully.")
                    self.haircut_box.delete(selected_haircut[0])
            except:
                messagebox.showerror("Error", "Haircut ID could not be extracted.")

        if current_tab == "Bookings":
            selected_booking = self.booking_box.curselection()
            if not selected_booking:
                messagebox.showerror("Error", "Select a booking")
                return
            selected_booking_info = self.booking_box.get(selected_booking[0])

            BookingID = re.search(r"ID: (\d+)", selected_booking_info)
            try:
                if BookingID:
                    BookingID = int(BookingID.group(1))
                    self.db.remove_booking(BookingID)
                    messagebox.showinfo("Success", f"Booking ID {BookingID} removed successfully.")
                    self.booking_box.delete(selected_booking[0])
            except:
                messagebox.showerror("Error", "Booking ID could not be extracted.")
        if current_tab == "Staff":
            selected_staff = self.staff_box.curselection()
            if not selected_staff:
                messagebox.showerror("Error", "Select a staff")
                return
            selected_staff_info = self.staff_box.get(selected_staff[0])

            StaffID = re.search(r"ID: (\d+)", selected_staff_info)
            try:
                if StaffID:
                    StaffID = int(StaffID.group(1))
                    self.db.remove_staff(StaffID)
                    messagebox.showinfo("Success", f"Staff ID {StaffID} removed successfully.")
                    self.staff_box.delete(selected_staff[0])
            except:
                messagebox.showerror("Error", "Staff ID could not be extracted.")

    def setup_ui(self):
        data = self.db.fetch_all_data()
        self.tabs = ttk.Notebook(self.window)
        self.tabs.pack(fill='both', expand=True)

        cust_frame = ttk.Frame(self.tabs)
        self.tabs.add(cust_frame, text="Customers")

        self.customer_list = tk.Listbox(cust_frame, width=120, height=30, font=FONT)
        self.customer_list.pack(side='left', fill='both', expand=True, padx=10, pady=10)

        scroll_cust = ttk.Scrollbar(cust_frame, orient='vertical', command=self.customer_list.yview)
        scroll_cust.pack(side='right', fill='y')
        self.customer_list.config(yscrollcommand=scroll_cust.set)

        haircut_frame = ttk.Frame(self.tabs)
        self.tabs.add(haircut_frame, text="Haircuts")

        self.haircut_box = tk.Listbox(haircut_frame, width=120, height=30, font=FONT)
        self.haircut_box.pack(side='left', fill='both', expand=True, padx=10, pady=10)

        scroll_hair = ttk.Scrollbar(haircut_frame, orient='vertical', command=self.haircut_box.yview)
        scroll_hair.pack(side='right', fill='y')
        self.haircut_box.config(yscrollcommand=scroll_hair.set)

        booking_frame = ttk.Frame(self.tabs)
        self.tabs.add(booking_frame, text="Bookings")

        self.booking_box = tk.Listbox(booking_frame, width=120, height=30, font=FONT)
        self.booking_box.pack(side='left', fill='both', expand=True, padx=10, pady=10)

        scroll_book = ttk.Scrollbar(booking_frame, orient='vertical', command=self.booking_box.yview)
        scroll_book.pack(side='right', fill='y')
        self.booking_box.config(yscrollcommand=scroll_book.set)

        staff_frame = ttk.Frame(self.tabs)
        self.tabs.add(staff_frame, text="Staff")

        self.staff_box = tk.Listbox(staff_frame, width=120, height=30, font=FONT)
        self.staff_box.pack(side='left', fill='both', expand=True, padx=10, pady=10)

        scroll_staff = ttk.Scrollbar(staff_frame, orient='vertical', command=self.staff_box.yview)
        scroll_staff.pack(side='right', fill='y')
        self.staff_box.config(yscrollcommand=scroll_staff.set)

        for customer in data["customers"]:
            self.customer_list.insert(tk.END,
                                 f"ID: {customer[0]}, Name: {customer[1]} {customer[2]}, "
                                 f"Email: {customer[3]}, DOB: {customer[6]}"
                                 )

        for haircut in data["haircuts"]:
            self.haircut_box.insert(tk.END,
                               f"ID: {haircut[0]}, Name: {haircut[1]}, "
                               f"Price: £{haircut[2]:.2f}, Duration: {haircut[3]}"
                               )

        for booking in data["bookings"]:
            self.booking_box.insert(tk.END,
                               f"BookingID: {booking[0]}, Date: {booking[1]}, Time: {booking[2]}, "
                               f"Customer: {booking[3]}, Haircut: {booking[4]}, Locked: {booking[5]}"
                               )

        if "staff" in data:
            for staff in data["staff"]:
                self.staff_box.insert(tk.END,
                                 f"ID: {staff[0]}, Email: {staff[1]}, Staff Number: {staff[2]}"
                                 )

        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill='x', pady=10)




        ttk.Button(btn_frame, text="Close", command=self.close).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="Remove", command=self.remove).pack(side='left', padx=5)

class AnalyticsWindow(BaseWindow):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self.window.title("Analytics Dashboard")
        self.window.geometry("1200x800")
        self.setup_ui()

    def setup_ui(self):
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_rowconfigure(2, weight=0)

        peak_frame = ttk.LabelFrame(self.window, text="Peak Booking Hours", padding=10)
        peak_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        self.peak_canvas = tk.Canvas(peak_frame, bg=BG_COLOR, highlightthickness=0, width=600, height=300)
        self.peak_canvas.pack(fill="both", expand=True)

        revenue_frame = ttk.LabelFrame(self.window, text="Revenue Analysis", padding=10)
        revenue_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=5)
        self.revenue_tree = ttk.Treeview(revenue_frame, columns=("Period", "Service", "Revenue", "Bookings"),
                                         show="headings")
        for col in ["Period", "Service", "Revenue", "Bookings"]:
            self.revenue_tree.heading(col, text=col)
            self.revenue_tree.column(col, width=120)
        scrollbar = ttk.Scrollbar(revenue_frame, orient="vertical", command=self.revenue_tree.yview)
        self.revenue_tree.configure(yscrollcommand=scrollbar.set)
        self.revenue_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        popularity_frame = ttk.LabelFrame(self.window, text="Service Popularity", padding=10)
        popularity_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.popularity_text = tk.Text(popularity_frame, bg=BG_COLOR, font=FONT, wrap="word")
        scrollbar = ttk.Scrollbar(popularity_frame, command=self.popularity_text.yview)
        self.popularity_text.configure(yscrollcommand=scrollbar.set)
        self.popularity_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        loyalty_frame = ttk.LabelFrame(self.window, text="Top Customers", padding=10)
        loyalty_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=5)
        self.loyalty_tree = ttk.Treeview(loyalty_frame, columns=("Customer", "Visits", "Styles"), show="headings")
        for col in ["Customer", "Visits", "Styles"]:
            self.loyalty_tree.heading(col, text=col)
            self.loyalty_tree.column(col, width=120)
        scrollbar = ttk.Scrollbar(loyalty_frame, command=self.loyalty_tree.yview)
        self.loyalty_tree.configure(yscrollcommand=scrollbar.set)
        self.loyalty_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        control_frame = ttk.Frame(self.window)
        control_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(control_frame, text="Days to analyze:").pack(side="left", padx=5)
        self.days_var = tk.StringVar(value="30")
        days_combo = ttk.Combobox(control_frame, textvariable=self.days_var,
                                  values=["7", "14", "30", "60", "90"], width=5)
        days_combo.pack(side="left", padx=5)

        ttk.Button(control_frame, text="Refresh",
                   command=lambda: self.ui.refresh_analytics()).pack(side="left", padx=10)

        self.ui.days_var.set("30")
        self.ui.refresh_analytics()

    def refresh_analytics(self):
        self.ui.refresh_analytics()





if __name__ == "__main__":
    app = BarberApp()
    app.main_menu()
