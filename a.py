import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import random
from datetime import datetime, timedelta
import re
import time

# ====================== STYLING CONSTANTS ======================
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

    def hash_password(self, password, salt="", rounds=5):
        salt_password = password + salt
        hash_value = 0
        for _ in range(rounds):
            for char in salt_password:
                hash_value = (hash_value << 5) ^ (hash_value + ord(char))
                hash_value &= 0xFFFFFFFF
        return hex(hash_value)[2:].zfill(8)

    def generate_salt(self, length=8):
        characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        return ''.join(random.choice(characters) for _ in range(length))

    def login_check(self, email, password):
        customer = self.db.fetch_customer_email(email)
        if customer:
            hashed_password = self.hash_password(password, salt=customer[5])
            return hashed_password == customer[4]
        return False

    def staff_check(self, Staff_Number):
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
            Estimated_Time TEXT)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Booking (
            BookingID INTEGER PRIMARY KEY AUTOINCREMENT,
            Date TEXT,
            Time TEXT,
            CustomerID INTEGER,
            HaircutID INTEGER,
            Locked BOOLEAN DEFAULT 0,
            FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID) ON DELETE CASCADE,
            FOREIGN KEY (HaircutID) REFERENCES Haircut(HaircutID) ON DELETE CASCADE)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Staff (
            StaffID INTEGER PRIMARY KEY AUTOINCREMENT, 
            Email TEXT,
            Staff_Number TEXT)''')

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

    def insert_customer(self, surname, firstname, email, hashed_password, salt, date_of_birth):
        self.cursor.execute('''INSERT INTO Customer (Surname, FirstName, Email, 
        Hashed_Password, Salt, Date_Of_Birth) VALUES (?, ?, ?, ?, ?, ?)''', (surname, firstname, email,
                                                                             hashed_password, salt, date_of_birth))
        self.connection.commit()

    def insert_haircut(self, haircutname, price, estimated_time):
        self.cursor.execute('''INSERT INTO Haircut (Haircut_Name, Price, Estimated_Time) VALUES (?,?,?)''',
                            (haircutname, price, estimated_time))

    def insert_booking(self, date, time, customerID, haircutID):
        self.cursor.execute('''INSERT INTO Booking (Date, Time, CustomerID, HaircutID) VALUES (?,?,?,?)''',
                            (date, time, customerID, haircutID))

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
        return {"customers": customers, "haircuts": haircuts, "bookings": bookings}

    def get_available_slots(self, date):
        booked_slots = self.cursor.execute("SELECT Time FROM Booking WHERE Date = ? AND Locked = 1", (date,)).fetchall()
        booked_times = [time[0] for time in booked_slots]
        times = [f"{hour:02d}:00" for hour in range(9, 18)]
        unbooked_slots = [time for time in times if time not in booked_times]
        return unbooked_slots

    def remove_customer(self, CustomerID):
        self.cursor.execute('''DELETE FROM Customer WHERE CustomerID = ?''', (CustomerID,))
        self.connection.commit()

    def remove_haircut(self, HaircutID):
        self.cursor.execute('''DELETE FROM Haircut WHERE HaircutID = ?''', (HaircutID,))
        self.connection.commit()

    def remove_booking(self, BookingID):
        self.cursor.execute('''DELETE FROM Booking WHERE BookingID = ?''', (BookingID,))
        self.connection.commit()

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

        return self.merge_lists(leftlist, rightlist, sort_index, ascending, sortby)

    def merge_lists(self, leftlist, rightlist, sort_index, ascending, sortby):
        sorted_list = []
        left_pointer = 0
        right_pointer = 0

        while left_pointer < len(leftlist) and right_pointer < len(rightlist):
            left_value = leftlist[left_pointer][sort_index]
            right_value = rightlist[right_pointer][sort_index]

            if sortby == 'date':  # New condition
                from datetime import datetime
                left_value = datetime.strptime(left_value, "%Y-%m-%d")
                right_value = datetime.strptime(right_value, "%Y-%m-%d")
            elif str(left_value).isdigit():
                left_value = int(left_value)
                right_value = int(right_value)

            if str(left_value).isdigit():
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
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background=BG_COLOR, font=FONT)
        style.configure('TButton', background=SECONDARY_COLOR, foreground='white')
        style.map('TButton', background=[('active', PRIMARY_COLOR)])
        style.configure('Header.TLabel', font=HEADER_FONT)
        style.configure('TEntry', **ENTRY_STYLE)

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
        def remove_selected_booking():
            selected_booking = booking_box.curselection()
            if not selected_booking:
                messagebox.showerror("Error", "Please select a booking to remove")
                return

            selected_booking_info = booking_box.get(selected_booking[0])
            BookingID = re.search(r"ID: (\d+)", selected_booking_info)
            if BookingID:
                BookingID = int(BookingID.group(1))
                self.db.remove_booking(BookingID)
                messagebox.showinfo("Success", f"Booking ID {BookingID} removed successfully.")
                booking_box.delete(selected_booking)
            else:
                messagebox.showerror("Error", "Booking ID could not be extracted.")

        def remove_selected_haircut():
            selected_haircut = haircut_box.curselection()
            if not selected_haircut:
                messagebox.showerror("Error", "Please select a haircut to remove")
                return

            selected_haircut_info = haircut_box.get(selected_haircut[0])
            HaircutID = re.search(r"ID: (\d+)", selected_haircut_info)
            if HaircutID:
                HaircutID = int(HaircutID.group(1))
                self.db.remove_haircut(HaircutID)
                messagebox.showinfo("Success", f"Haircut ID {HaircutID} removed successfully.")
                haircut_box.delete(selected_haircut)
            else:
                messagebox.showerror("Error", "Haircut ID could not be extracted.")

        def remove_selected_customer():
            selected_customer = customer_list.curselection()
            if not selected_customer:
                messagebox.showerror("Error", "Please select a customer to remove")
                return

            selected_customer_info = customer_list.get(selected_customer[0])
            customerID = re.search(r"ID: (\d+)", selected_customer_info)
            if customerID:
                customerID = int(customerID.group(1))
                self.db.remove_customer(customerID)
                messagebox.showinfo("Success", f"Customer ID {customerID} removed successfully.")
                customer_list.delete(selected_customer)
            else:
                messagebox.showerror("Error", "Customer ID could not be extracted.")

        data = self.app.db.fetch_all_data()
        window = self.create_window("Database Contents", "1200x800")

        notebook = ttk.Notebook(window)
        notebook.pack(fill='both', expand=True)

        # Customers tab
        cust_frame = ttk.Frame(notebook)
        notebook.add(cust_frame, text="Customers")
        customer_list = tk.Listbox(cust_frame, width=120, height=30, font=FONT)
        customer_list.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scroll_cust = ttk.Scrollbar(cust_frame, orient='vertical', command=customer_list.yview)
        scroll_cust.pack(side='right', fill='y')
        customer_list.config(yscrollcommand=scroll_cust.set)

        # Haircuts tab
        haircut_frame = ttk.Frame(notebook)
        notebook.add(haircut_frame, text="Haircuts")
        haircut_box = tk.Listbox(haircut_frame, width=120, height=30, font=FONT)
        haircut_box.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scroll_hair = ttk.Scrollbar(haircut_frame, orient='vertical', command=haircut_box.yview)
        scroll_hair.pack(side='right', fill='y')
        haircut_box.config(yscrollcommand=scroll_hair.set)

        # Bookings tab
        booking_frame = ttk.Frame(notebook)
        notebook.add(booking_frame, text="Bookings")
        booking_box = tk.Listbox(booking_frame, width=120, height=30, font=FONT)
        booking_box.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scroll_book = ttk.Scrollbar(booking_frame, orient='vertical', command=booking_box.yview)
        scroll_book.pack(side='right', fill='y')
        booking_box.config(yscrollcommand=scroll_book.set)

        # Staff tab
        staff_frame = ttk.Frame(notebook)
        notebook.add(staff_frame, text="Staff")
        staff_box = tk.Listbox(staff_frame, width=120, height=30, font=FONT)
        staff_box.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scroll_staff = ttk.Scrollbar(staff_frame, orient='vertical', command=staff_box.yview)
        scroll_staff.pack(side='right', fill='y')
        staff_box.config(yscrollcommand=scroll_staff.set)

        for customer in data["customers"]:
            customer_list.insert(tk.END,
                                 f"ID: {customer[0]}, Name: {customer[1]} {customer[2]}, Email: {customer[3]}, Hashed_Password: {customer[4]}, Salt: {customer[5]}, Date Of Birth: {customer[6]}")

        for haircut in data["haircuts"]:
            haircut_box.insert(tk.END,
                               f"ID: {haircut[0]}, Name: {haircut[1]}, Price: ${haircut[2]}, Time: {haircut[3]}")

        for booking in data["bookings"]:
            booking_box.insert(tk.END,
                               f"BookingID: {booking[0]}, Date: {booking[1]}, Time: {booking[2]}, Customer: {booking[3]}, Haircut: {booking[4]}, Locked: {booking[5]}")

        for staff in data["staff"]:
            staff_box.insert(tk.END, f"StaffID: {staff[0]}, Email: {staff[1]}, Staff: {staff[2]}")

        btn_frame = ttk.Frame(window)
        btn_frame.pack(fill='x', pady=10)

        ttk.Button(btn_frame, text="Remove Customer", command=remove_selected_customer).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Remove Haircut", command=remove_selected_haircut).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Remove Booking", command=remove_selected_booking).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Close", command=window.destroy).pack(side='right', padx=5)

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
            hashed_password = self.auth.hash_password(new_password, salt=salt)
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

        btn_frame = ttk.Frame(window)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="Login",
                   command=lambda: self.auth.staff_check(staffID_entry.get())).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Back",
                   command=window.destroy).pack(side='left', padx=5)

    def login(self):
        def attempt_login():
            email = email_entry.get()
            password = password_entry.get()
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
        if not self.validate_payment(card_number, card_cvc, expiry_date):
            return

        try:
            self.db.cursor.execute("SELECT HaircutID FROM Haircut WHERE Haircut_Name=?", (haircut_name,))
            haircut = self.db.cursor.fetchone()

            if not haircut:
                messagebox.showerror("Error", "Selected haircut not found")
                return

            haircut_id = haircut[0]
            customer_id = self.get_current_customer_id()

            if not customer_id:
                messagebox.showerror("Error", "No customer logged in")
                return

            booking_date = datetime.now().strftime("%Y-%m-%d")
            self.db.insert_booking(booking_date, selected_time, customer_id, haircut_id)
            messagebox.showinfo("Success", f"Booking confirmed for {selected_time}!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to create booking: {str(e)}")

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

        main_frame = ttk.Frame(window)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text=f"Selected Time: {selected_time}",
                  style='Header.TLabel').pack(pady=10)

        # Payment Details
        payment_frame = ttk.LabelFrame(main_frame, text="Payment Details")
        payment_frame.pack(fill='x', pady=10)

        ttk.Label(payment_frame, text="Card Number:").grid(row=0, column=0, pady=5, sticky='e')
        card_number = ttk.Entry(payment_frame)
        card_number.grid(row=0, column=1, pady=5, padx=5, sticky='ew')

        ttk.Label(payment_frame, text="CVC:").grid(row=1, column=0, pady=5, sticky='e')
        card_cvc = ttk.Entry(payment_frame)
        card_cvc.grid(row=1, column=1, pady=5, padx=5, sticky='ew')

        ttk.Label(payment_frame, text="Expiry (MM/YY):").grid(row=2, column=0, pady=5, sticky='e')
        expiry_date = ttk.Entry(payment_frame)
        expiry_date.grid(row=2, column=1, pady=5, padx=5, sticky='ew')

        # Haircut Selection
        haircut_frame = ttk.LabelFrame(main_frame, text="Select Haircut")
        haircut_frame.pack(fill='x', pady=10)

        self.db.cursor.execute('''SELECT Haircut_Name FROM Haircut''')
        haircut_choices = [row[0] for row in self.db.cursor.fetchall()] or ["No services available"]

        haircut_var = tk.StringVar(value=haircut_choices[0])
        haircut_menu = ttk.OptionMenu(haircut_frame, haircut_var, *haircut_choices)
        haircut_menu.pack(fill='x', padx=5, pady=5)

        # Confirm Button
        ttk.Button(main_frame, text="Confirm Booking",
                   command=lambda: [
                       self.process_booking(
                           selected_time,
                           haircut_var.get(),
                           card_number.get(),
                           card_cvc.get(),
                           expiry_date.get()
                       ),
                       window.destroy()
                   ]).pack(pady=15)

    def predictive_analytics(self):
        window = self.create_window("Predictive Analytics", "800x600")
        ttk.Label(window, text="Analytics Dashboard", style='Header.TLabel').pack(pady=20)

        # Placeholder for analytics content
        ttk.Label(window, text="Booking trends and predictions will appear here").pack()

        ttk.Button(window, text="Close", command=window.destroy).pack(pady=20)

    def bookings(self):
        def on_date_select():
            selected_year = year_spinbox.get()
            selected_date = f"{selected_year}-{int(month_spinbox.get()):02d}-{int(day_spinbox.get()):02d}"
            available_slots = self.db.get_available_slots(selected_date)
            time_listbox.delete(0, tk.END)
            for time in available_slots:
                time_listbox.insert(tk.END, time)

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

    def main_menu(self):
        self.ui.main_menu()

    def login(self):
        self.ui.login()

    def register(self):
        self.ui.register()

    def main_page(self):
        window = tk.Toplevel()
        window.title("Barber Booking System")
        window.geometry("800x600")
        window.configure(bg=BG_COLOR)

        header = ttk.Label(window, text="Main Menu", style='Header.TLabel')
        header.pack(pady=30)

        btn_frame = ttk.Frame(window)
        btn_frame.pack(pady=30)

        ttk.Button(btn_frame, text="Book Appointment", width=20,
                   command=lambda: [window.destroy(), self.ui.bookings()]).grid(row=0, column=0, padx=10, pady=10)

        ttk.Button(btn_frame, text="View Pricing", width=20,
                   command=self.ui.pricing).grid(row=0, column=1, padx=10, pady=10)

        ttk.Button(btn_frame, text="View Database", width=20,
                   command=self.ui.show_database).grid(row=1, column=0, padx=10, pady=10)

        ttk.Button(btn_frame, text="Analytics", width=20,
                   command=self.ui.predictive_analytics).grid(row=1, column=1, padx=10, pady=10)

        ttk.Button(window, text="Logout",
                   command=lambda: [window.destroy(), self.main_menu()]).pack(side='bottom', pady=20)

        window.mainloop()


class BookingManager:
    def __init__(self, db_connection):
        self.db = db_connection
        self.cursor = db_connection.cursor()

    def lock_time_slot(self, date, time):
        lock_duration = 10 * 60  # 10 minutes in seconds
        current_time = time.time()
        lock_end_time = current_time + lock_duration

        self.cursor.execute('''
            UPDATE Booking 
            SET Locked = 1, LockEndTime = ? 
            WHERE Date = ? AND Time = ?
        ''', (lock_end_time, date, time))
        self.db.connection.commit()

    def get_available_slots(self, date):
        booked_slots = self.cursor.execute("SELECT Time, Locked, LockEndTime FROM Booking WHERE Date = ?",
                                           (date,)).fetchall()
        booked_times = []
        current_time = time.time()

        for booked_time, locked, lock_end_time in booked_slots:
            if locked:
                if current_time > lock_end_time:
                    self.cursor.execute('''UPDATE Booking SET Locked = 0 WHERE Date = ? AND Time = ?''',
                                        (date, booked_time))
                    self.db.connection.commit()
                else:
                    booked_times.append(booked_time)
            else:
                booked_times.append(booked_time)

        times = [f"{hour:02d}:00" for hour in range(9, 18)]
        unbooked_slots = [time for time in times if time not in booked_times]
        return unbooked_slots

    def book_slot(self, date, time, customer_id, haircut_id):
        available_slots = self.get_available_slots(date)
        if time not in available_slots:
            raise Exception(f"The time slot {time} is not available.")

        self.cursor.execute('''
            INSERT INTO Booking (Date, Time, CustomerID, HaircutID, Locked) 
            VALUES (?, ?, ?, ?, 0)
        ''', (date, time, customer_id, haircut_id))
        self.db.connection.commit()
        return f"Booking successful for {time} on {date}."


if __name__ == "__main__":
    app = BarberApp()
    app.main_menu()
