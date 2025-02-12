import tkinter as tk
from tkinter import messagebox
import sqlite3
import random
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
            "Haircut Name" TEXT,
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

    def fetch_all_customers(self):
        self.cursor.execute("SELECT * FROM Customer")
        return self.cursor.fetchall()

    def fetch_all_haircuts(self):
        self.cursor.execute("SELECT * FROM Haircut")
        return self.cursor.fetchall()

    def fetch_all_bookings(self):
        self.cursor.execute("SELECT * FROM Booking")
        return self.cursor.fetchall()

    def fetch_all_data(self):
        customers = self.fetch_all_customers()
        haircuts = self.fetch_all_haircuts()
        bookings = self.fetch_all_bookings()
        return {"customers": customers, "haircuts": haircuts, "bookings": bookings}

    def remove_customer(self, CustomerID):
        self.cursor.execute('''DELETE FROM Customer WHERE CustomerID = ?''', (CustomerID,))
        self.connection.commit()


class UIManager:
    def __init__(self, app):
        self.app = app
        self.auth = app.auth

    def main_menu(self):
        window = tk.Tk()
        window.title("Booking Interface")
        window.geometry("1280x1080")

        tk.Label(window, text="Login to continue", font=("Helvetica", 16)).place(x=500, y=200)
        
        tk.Button(window, text="Login", command=lambda: [window.destroy(), self.app.login()]).place(x=500, y=300)
        
        tk.Button(window, text="Register", command=lambda: [window.destroy(), self.app.register()]).place(x=500, y=400)
                                                                                                         
        tk.Button(window, text="Staff Login", command=lambda: [window.destroy(), self.app.staff_login()]).place(x=500, y=500)
                                                                                                                                                                                                                              
        tk.Button(window, text="View Database", command=self.show_database).place(x=500, y=600)

        window.mainloop()

    def show_database(self):
        data = self.app.db.fetch_all_data()

        window = tk.Tk()
        window.title("Database Contents")
        window.geometry("1920x1080")

        tk.Label(window, text="Customers", font=("Helvetica", 12)).place(x=600, y=100)
        tk.Label(window, text="Haircuts", font=("Helvetica", 12)).place(x=1200, y=100)
        tk.Label(window, text="Bookings", font=("Helvetica", 12)).place(x=1800, y=100)

        customer_list = tk.Listbox(window, width=90, height=30)
        customer_list.place(x=0, y=0)

        haircut_box = tk.Listbox(window, width=90, height=30)
        haircut_box.place(x=600, y=0)

        booking_box = tk.Listbox(window, width=90, height=30)
        booking_box.place(x=1200, y=0)

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

        close_button = tk.Button(window, text="Close", command=window.destroy)
        close_button.place(x=800, y=600)

        remove_customer = tk.Button(window, text="Remove Customer",command=self.db.remove_customer())
        remove_customer.place(x=250, y=600)

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

    def login(self):
        def attempt_login():
            email = e1.get()
            password = e2.get()
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

        e1 = tk.Entry(login_widget)
        e1.place(x=250, y=50)
        e2 = tk.Entry(login_widget, show="*")
        e2.place(x=250, y=100)

        login_button = tk.Button(login_widget, text="Login", command=attempt_login)
        login_button.place(x=250, y=150)

        back_button = tk.Button(login_widget, text="Return",
                                command=lambda: [login_widget.destroy(), self.app.main_menu()])
        back_button.place(x=30, y=300)

        login_widget.mainloop()


class BarberApp:
    def __init__(self):
        self.db = DatabaseManager()
        self.auth = AuthManager(self.db)
        self.ui = UIManager(self)

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
        tk.Label(main_window, text="Barber Bookings", font=("Helvetica", 18, "bold")).place(x=1, y=0)

        tk.Label(main_window, text="Bookings", font=("Helvetica", 12)).place(x=50, y=120)
        tk.Button(main_window, text="Continue").place(x=50, y=175)

        tk.Label(main_window, text="Predictive Analytics", font=("Helvetica", 12)).place(x=200, y=120)
        tk.Button(main_window, text="Continue").place(x=200, y=175)

        tk.Label(main_window, text="Pricing", font=("Helvetica", 12)).place(x=400, y=120)
        tk.Button(main_window, text="Continue").place(x=400, y=175)

        main_window.mainloop()


if __name__ == "__main__":
    app = BarberApp()
    app.main_menu()
