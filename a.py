import tkinter as tk
from tkinter import messagebox
import sqlite3


class AuthManager:
    def __init__(self):
        self.email = []
        self.password = []

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
        return ''.join([chr(i) for i in range(length)])


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
            Password TEXT,
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

    def insert_customer(self, surname, firstname, email, password, dateofbirth):
        self.cursor.execute('''INSERT INTO Customer (Surname, FirstName, Email, 
        Password, DateOfBirth) VALUES (?, ?, ?, ?, ?)''', (surname, firstname, email, password, dateofbirth))
        self.connection.commit()

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


class UIManager:
    def __init__(self, app):
        self.app = app

    def main_menu(self):
        window = tk.Tk()
        window.title("Booking Interface")
        window.geometry("720x520")

        tk.Label(window, text="Login to continue", font=("Helvetica", 16)).grid(row=1, column=0, columnspan=3,
                                                                                pady=(40, 20))

        tk.Button(window, text="Login", command=lambda: [window.destroy(), self.app.login()]).grid(row=2, column=0,
                                                                                                   columnspan=3,
                                                                                                   pady=(0, 20))
        tk.Button(window, text="Register", command=lambda: [window.destroy(), self.app.register()]).grid(row=3,
                                                                                                         column=0,
                                                                                                         columnspan=3,
                                                                                                         pady=(0, 20))
        tk.Button(window, text="Staff Login", command=lambda: [window.destroy(), self.app.staff_login()]).grid(row=4,
                                                                                                               column=0,
                                                                                                               columnspan=3,
                                                                                                               pady=(0, 20))
        tk.Button(window, text="View Database", command=self.show_database).grid(row=5, column=0, columnspan=3, pady=(20, 20))

        window.mainloop()

    def show_database(self):
        data = self.app.db.fetch_all_data()

        window = tk.Tk()
        window.title("Database Contents")
        window.geometry("1920x1080")

        tk.Label(window, text="Customers", font=("Helvetica", 12)).grid(row=0, column=0, pady=10)
        tk.Label(window, text="Haircuts", font=("Helvetica", 12)).grid(row=0, column=1, pady=10)
        tk.Label(window, text="Bookings", font=("Helvetica", 12)).grid(row=0, column=2, pady=10)

        customer_list = tk.Listbox(window, width=100, height=30)
        customer_list.grid(row=1, column=0, padx=10, pady=10)

        haircut_box = tk.Listbox(window, width=100, height=30)
        haircut_box.grid(row=1, column=1, padx=10, pady=10)

        booking_box = tk.Listbox(window, width=100, height=30)
        booking_box.grid(row=1, column=2, padx=10, pady=10)

        for customer in data["customers"]:
            customer_list.insert(tk.END,
                                 f"ID: {customer[0]}, Name: {customer[1]} {customer[2]}, Email: {customer[3]}")

        for haircut in data["haircuts"]:
            haircut_box.insert(tk.END,
                               f"ID: {haircut[0]}, Name: {haircut[1]}, Price: ${haircut[2]}, Time: {haircut[3]}")

        for booking in data["bookings"]:
            booking_box.insert(tk.END,
                               f"BookingID: {booking[0]}, Date: {booking[1]}, Time: {booking[2]}")

        close_button = tk.Button(window, text="Close", command=window.destroy)
        close_button.grid(row=2, column=0, columnspan=3, pady=10)

        window.mainloop()

    def register(self):
        def create():
            new_email = email_entry.get()
            new_password = password_entry.get()
            if not new_email or not new_password:
                messagebox.showerror("Error", "Email and Password must be entered.")
                return
            self.app.db.insert_customer(new_email, new_password)
            self.app.auth.email.append(new_email)
            self.app.auth.password.append(new_password)
            register_widget.destroy()
            self.app.main_menu()

        register_widget = tk.Tk()
        register_widget.title("Register")
        register_widget.geometry("720x520")

        tk.Label(register_widget, text="Email").grid(row=0, column=0, padx=20, pady=(20, 10))
        tk.Label(register_widget, text="Password").grid(row=1, column=0, padx=20, pady=(20, 10))
        tk.Label(register_widget, text="Surname").grid(row=2, column=0, padx=20, pady=(20, 10))
        tk.Label(register_widget, text="First Name").grid(row=3, column=0, padx=20, pady=(20, 10))
        tk.Label(register_widget, text="Date Of Birth").grid(row=4, column=0, padx=20, pady=(20, 10))


        email_entry= tk.Entry(register_widget)
        email_entry.grid(row=0, column=1, padx=20, pady=(20, 10))
        password_entry = tk.Entry(register_widget)
        password_entry.grid(row=1, column=1, padx=20, pady=(0, 10))
        surname_entry= tk.Entry(register_widget)
        surname_entry.grid(row=2, column=1, padx=20, pady=(20, 10))
        firstname_entry= tk.Entry(register_widget)
        firstname_entry.grid(row=3, column=1, padx=20, pady=(20, 10))
        dateofbirth_entry= tk.Entry(register_widget)
        dateofbirth_entry.grid(row=4, column=1, padx=20, pady=(20, 10))

        register_button = tk.Button(register_widget, text="Create", command=create)
        register_button.grid(row=5, column=1, pady=(20, 20))

        back_button = tk.Button(register_widget, text="Return",
                                command=lambda: [register_widget.destroy(), self.app.main_menu()])
        back_button.place(x=30, y=450)

        register_widget.mainloop()

    def login(self):
        login_widget = tk.Tk()
        login_widget.title("Login")
        login_widget.geometry("720x520")

        tk.Label(login_widget, text="Email").grid(row=0, column=0, padx=20, pady=(20, 10))
        tk.Label(login_widget, text="Password").grid(row=1, column=0, padx=20, pady=(0, 10))

        e1 = tk.Entry(login_widget)
        e1.grid(row=0, column=1, padx=20, pady=(20, 10))
        e2 = tk.Entry(login_widget, show="*")
        e2.grid(row=1, column=1, padx=20, pady=(0, 10))

        login_button = tk.Button(login_widget, text="Login", command=lambda: [login_widget.destroy(), self.app.main_page()])
        login_button.grid(row=2, column=1, pady=(20, 20))

        login_widget.mainloop()


class BarberApp:
    def __init__(self):
        self.db = DatabaseManager()
        self.auth = AuthManager()
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
        main_window.geometry("720x520")

        tk.Button(main_window, text="Logout", width=10,
                  command=lambda: [main_window.destroy(), self.main_menu()]).place(x=50, y=450)
        tk.Label(main_window, text="Barber Bookings", font=("Helvetica", 18, "bold")).grid(row=1, column=0,
                                                                                           columnspan=3, pady=(20, 40))

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



