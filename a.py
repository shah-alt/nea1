import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import random
from datetime import datetime, timedelta
import re


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
    def staff_check(self,Staff_Number):
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
            FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID) ON DELETE CASCADE,
            FOREIGN KEY (HaircutID) REFERENCES Haircut(HaircutID) ON DELETE CASCADE)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Staff (
            StaffID INTEGER PRIMARY KEY AUTOINCREMENT, 
            Email TEXT,
            Staff_Number TEXT)''')

    def check_table(self):
        self.cursor.execute("PRAGMA table_info(Customer);")
        ys = self.cursor.fetchall()
        print(ys)

    def insert_customer(self, surname, firstname, email, hashed_password, salt, date_of_birth):
        self.cursor.execute('''INSERT INTO Customer (Surname, FirstName, Email, 
        Hashed_Password, Salt, Date_Of_Birth) VALUES (?, ?, ?, ?, ?, ?)''', (surname, firstname, email,
                                                                             hashed_password, salt, date_of_birth))
        self.connection.commit()

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
        booked_slots = self.cursor.execute("SELECT Time FROM Booking WHERE Date = ?", (date,)).fetchall()
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

class UIManager:
    def __init__(self, app, db):
        self.db = db
        self.app = app
        self.auth = app.auth

    def back_button(self, widget):
        back_button = tk.Button(widget, text="Return",
                                command=lambda: [widget.destroy(), self.app.main_menu()])

    def main_menu(self):
        window = tk.Tk()
        window.title("Booking Interface")
        window.geometry("1280x1080")

        tk.Label(window, text="Login to continue", font=("Helvetica", 16)).place(x=500, y=200)

        tk.Button(window, text="Login", command=lambda: [window.destroy(), self.app.login()]).place(x=500, y=300)

        tk.Button(window, text="Register", command=lambda: [window.destroy(), self.app.register()]).place(x=500, y=400)

        window.mainloop()
    def show_database(self):
        def remove_selected_booking():
            selected_booking = booking_box.curselection()
            if not selected_booking:
                messagebox.showerror("Please select a booking to remove")
                return

            selected_booking_info = booking_box.get(selected_booking[0])

            BookingID = re.search(r"ID: (\d+)", selected_booking_info)
            if BookingID:
                BookingID = int(BookingID.group(1))
                self.db.remove_booking(BookingID)
                messagebox.showinfo("Success", f"Booking ID {BookingID} removed successfully.")
            else:
                messagebox.showerror("Error", "Booking ID could not be extracted.")

        def remove_selected_haircut():
                selected_haircut = haircut_box.curselection()
                if not selected_haircut:
                    messagebox.showerror("Please select a customer to remove")
                    return

                selected_haircut_info = haircut_box.get(selected_haircut[0])

                HaircutID = re.search(r"ID: (\d+)", selected_haircut_info)
                if HaircutID:
                    HaircutID = int(HaircutID.group(1))
                    self.db.remove_haircut(HaircutID)
                    messagebox.showinfo("Success", f"Haircut ID {HaircutID} removed successfully.")
                else:
                    messagebox.showerror("Error", "Haircut ID could not be extracted.")
        def remove_selected_customer():
            selected_customer = customer_list.curselection()
            if not selected_customer:
                messagebox.showerror("Please select a customer to remove")
                return

            selected_customer_info = customer_list.get(selected_customer[0])

            customerID = re.search(r"ID: (\d+)", selected_customer_info)
            if customerID:
                customerID = int(customerID.group(1))
                self.db.remove_customer(customerID)
                messagebox.showinfo("Success", f"Customer ID {customerID} removed successfully.")
            else:
                messagebox.showerror("Error", "Customer ID could not be extracted.")
        data = self.app.db.fetch_all_data()

        window = tk.Tk()
        window.title("Database Contents")
        window.geometry("1920x1080")

        tk.Label(window, text="Customers", font=("Helvetica", 12)).place(x=300, y=0)
        tk.Label(window, text="Haircuts", font=("Helvetica", 12)).place(x=900, y=0)
        tk.Label(window, text="Bookings", font=("Helvetica", 12)).place(x=1500, y=0)

        customer_list = tk.Listbox(window, width=50, height=30)
        customer_list.place(x=50, y=50)

        haircut_box = tk.Listbox(window, width=50, height=30)
        haircut_box.place(x=450, y=50)

        booking_box = tk.Listbox(window, width=50, height=30)
        booking_box.place(x=850, y=50)

        staff_box = tk.Listbox(window, width=50, height=30)
        staff_box.place(x=1250, y=50)

        for customer in data["customers"]:
            customer_list.insert(tk.END,
                                 f"ID: {customer[0]}, Name: {customer[1]} {customer[2]}, Email: {customer[3]}"
                                 f", Hashed_Password: {customer[4]}, Salt: {customer[5]}, Date Of Birth: {customer[6]}")

        for haircut in data["haircuts"]:
            haircut_box.insert(tk.END,
                               f"ID: {haircut[0]}, Name: {haircut[1]}, Price: ${haircut[2]}, Time: {haircut[3]}")

        for booking in data["bookings"]:
            booking_box.insert(tk.END,
                               f"BookingID: {booking[0]}, Date: {booking[1]}, Time: {booking[2]}")
        for staff in data["staff"]:
            staff_box.insert(tk.END,
                               f"StaffID: {staff[0]}, Email: {staff[1]}, Staff: {staff[2]}")

        close_button = tk.Button(window, text="Close", command=window.destroy)
        close_button.place(x=850, y=700)

        remove_customer = tk.Button(window, text="Remove Customer", command=remove_selected_customer)
        remove_customer.place(x=250, y=300)

        remove_haircut = tk.Button(window, text="Remove Haircut", command=remove_selected_haircut)
        remove_haircut.place(x=650, y=300)

        remove_booking = tk.Button(window, text="Remove Booking", command=remove_selected_booking)
        remove_booking.place(x=850, y=300)

        window.mainloop()

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

        register_widget = tk.Tk()
        register_widget.title("Register")
        register_widget.geometry("400x400")

        tk.Label(register_widget, text="Email").place(x=150, y=30)
        tk.Label(register_widget, text="Password").place(x=150, y=60)
        tk.Label(register_widget, text="Surname").place(x=150, y=90)
        tk.Label(register_widget, text="First Name").place(x=150, y=120)
        tk.Label(register_widget, text="Date Of Birth").place(x=150, y=150)

        email_entry = tk.Entry(register_widget)
        email_entry.place(x=250, y=30)

        password_entry = tk.Entry(register_widget)
        password_entry.place(x=250, y=60)

        surname_entry = tk.Entry(register_widget)
        surname_entry.place(x=250, y=90)

        firstname_entry = tk.Entry(register_widget)
        firstname_entry.place(x=250, y=120)

        dateofbirth_entry = tk.Entry(register_widget)
        dateofbirth_entry.insert(0, "DD/MM/YYYY")
        dateofbirth_entry.place(x=250, y=150)

        register_button = tk.Button(register_widget, text="Create", command=create)
        register_button.place(x=250, y=200)

        back_button = tk.Button(register_widget, text="Return",
                                command=lambda: [register_widget.destroy(), self.app.main_menu()])
        back_button.place(x=30, y=300)

        register_widget.mainloop()
    def staff_login(self):
        login_widget = tk.Tk()
        login_widget.title("Staff Login")
        login_widget.geometry("400x400")

        staffID_entry = tk.Entry(login_widget)
        tk.Label(login_widget, text="ID").place(x=150, y=50)
        login_button = tk.Button(login_widget, text="Login", command=self.auth.staff_login)
        login_button.place(x=250, y=150)
    def login(self):
        def attempt_login():
            email = email_entry.get()
            password = password_entry.get()
            if self.auth.login_check(email, password):
                messagebox.showinfo("Success", "Login successful!")
                login_widget.destroy()
                self.app.main_page()
            else:
                messagebox.showerror("Error", "Invalid email or password.")

        login_widget = tk.Tk()
        login_widget.title("Login")
        login_widget.geometry("400x400")

        tk.Label(login_widget, text="Email").place(x=150, y=50)
        tk.Label(login_widget, text="Password").place(x=150, y=100)

        email_entry = tk.Entry(login_widget)
        email_entry.place(x=250, y=50)
        password_entry = tk.Entry(login_widget, show="*")
        password_entry.place(x=250, y=100)

        login_button = tk.Button(login_widget, text="Login", command=attempt_login)
        login_button.place(x=250, y=150)

        back_button = tk.Button(login_widget, text="Return",
                                command=lambda: [login_widget.destroy(), self.app.main_menu()])
        back_button.place(x=30, y=300)

        login_widget.mainloop()

    def pricing(self):
        pricing_widget = tk.Tk()
        pricing_widget.title("Login")
        pricing_widget.geometry("800x800")

        pricing_widget.mainloop()

    def predictive_analytics(self):
        analytics_widget = tk.Tk()
        analytics_widget.title("Login")
        analytics_widget.geometry("800x800")

        analytics_widget.mainloop()

    def bookings(self):
        def on_date_select():
            selected_year = year_spinbox.get()
            selected_date = f"{selected_year}-{int(month_spinbox.get()):02d}-{int(day_spinbox.get()):02d}"
            available_slots = self.db.get_available_slots(selected_date)
            time_listbox.delete(0, tk.END)
            for time in available_slots:
                time_listbox.insert(tk.END, time)

        bookings_widget = tk.Tk()
        bookings_widget.title("Bookings")
        bookings_widget.geometry("800x800")

        ttk.Label(bookings_widget, text="Select a Date:").pack(pady=10)

        frame = ttk.Frame(bookings_widget)
        frame.pack(pady=10)

        ttk.Label(frame, text="Year:").grid(row=0, column=0)
        year_spinbox = ttk.Spinbox(frame, from_=2020, to=2025, width=6, wrap=True)
        year_spinbox.set(datetime.now().year)
        year_spinbox.grid(row=0, column=1)

        ttk.Label(frame, text="Month:").grid(row=0, column=2)
        month_spinbox = ttk.Spinbox(frame, from_=1, to=12, width=3, wrap=True)
        month_spinbox.set(datetime.now().month)
        month_spinbox.grid(row=0, column=3)

        ttk.Label(frame, text="Day:").grid(row=0, column=4)
        day_spinbox = ttk.Spinbox(frame, from_=1, to=31, width=3, wrap=True)
        day_spinbox.set(datetime.now().day)
        day_spinbox.grid(row=0, column=5)

        ttk.Button(bookings_widget, text="Check Availability", command=on_date_select).pack(pady=10)

        ttk.Label(bookings_widget, text="Available Times:").pack(pady=10)
        time_listbox = tk.Listbox(bookings_widget)
        time_listbox.pack(pady=10)

        bookings_widget.mainloop()


        bookings_widget = tk.Tk()
        bookings_widget.title("Bookings")
        bookings_widget.geometry("800x800")

    def staff_login(self):
        staff_login_widget = tk.Tk()
        staff_login_widget.title("Login")
        staff_login_widget.geometry("800x800")



        staff_login_widget.mainloop()

class BarberApp:
    def __init__(self):
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
        main_window = tk.Tk()
        main_window.title("Main Menu")
        main_window.geometry("1280x1080")

        tk.Button(main_window, text="Logout", width=10,
                  command=lambda: [main_window.destroy(), self.main_menu()]).place(x=50, y=450)
        tk.Label(main_window, text="Barber Bookings", font=("Helvetica", 18, "bold")).place(x=600, y=50)

        tk.Label(main_window, text="Bookings", font=("Helvetica", 12)).place(x=300, y=120)
        tk.Button(main_window, text="Continue", command=lambda: [main_window.destroy(), self.ui.bookings()]).place(x=300, y=175)

        tk.Label(main_window, text="Predictive Analytics", font=("Helvetica", 12)).place(x=600, y=120)
        tk.Button(main_window, text="Continue").place(x=600, y=175)

        tk.Label(main_window, text="View database", font=("Helvetica", 12)).place(x=900, y=120)
        tk.Button(main_window, text="View Database", command=self.ui.show_database).place(x=900, y=175)

        main_window.mainloop()


if __name__ == "__main__":
    app = BarberApp()
    app.main_menu()
