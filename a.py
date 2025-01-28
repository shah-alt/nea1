import tkinter as tk
from tkinter import messagebox
import sqlite3

connection = sqlite3.connect("barberdb.db")
cursor = connection.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS Customer (CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
             Surname TEXT,
             FirstName TEXT,
             Email TEXT,
             Password TEXT,
             Date Of Birth TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS Haircut (HaircutID INTEGER PRIMARY KEY AUTOINCREMENT,
             Haircut Name TEXT,
             Price REAL,
             Estimated Time TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS Booking (BookingID INTEGER PRIMARY KEY AUTOINCREMENT,
             Date TEXT,
             Time TEXT,
             CustomerID INTEGER,
             HaircutID INTEGER,
             FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID) ON DELETE CASCADE,
             FOREIGN KEY (HaircutID) REFERENCES Haircut(HaircutID) ON DELETE CASCADE)''')

email = []
password = []
staff_ID = []




def financials():
   def graphs():
       financials_widget.destroy()
       graph_widget = tk.Tk()
       graph_widget.title("Graphs")
       graph_widget.geometry = ("720x520")


   financials_widget = tk.Tk()
   financials_widget.title("Financials")
   financials_widget.geometry("720x520")


   graph = tk.Button(financials_widget, text="Graphs", command=graphs)
   graph.place(x=50,y=20)




def valid_email(e1):
   new_email = e1.get()
   for i in email:
       if i == new_email:
           return True
       return False


def valid_password(e2):
   new_password = e2.get()
   for i in password:
       if i == new_password:
           return True
       return False




def valid_staff(e1):
   entered_ID = e1.get()
   for i in staff_ID:
       if i == entered_ID:
           return True
       return False


def staff_login():
   staff_widget = tk.Tk()
   staff_widget.title("Staff Login")
   staff_widget.geometry("720x520")


   tk.Label(staff_widget, text="Staff ID").grid(row=0, column=0, padx=20, pady=(20, 10))
   e1 = tk.Entry(staff_widget)
   e1.grid(row=0, column=1, padx=20, pady=(20, 10))


   back_button = tk.Button(staff_widget, text="Return", command=lambda: [staff_widget.destroy(), main_menu()])
   back_button.place(x=30, y=450)


   if valid_staff(e1) == True:
       staff_widget.destroy()
       staff_page()


   login_button = tk.Button(staff_widget, text="Login", command=lambda: [staff_widget.destroy(), staff_page()])
   login_button.grid(row=2, column=1, pady=(20, 20))


def register():
   def create():
       new_email = e1.get()
       new_password = e2.get()
       if not new_email or not new_password:
           messagebox.showerror("Username and Password must be entered.")
           return
       connection = sqlite3.connect("barberdb.db")
       cursor = connection.cursor()
       try:
           cursor.execute()
       email.append(new_email)
       password.append(new_password)
       register_widget.destroy()
       main_menu()
   register_widget = tk.Tk()
   register_widget.title("Login")
   register_widget.geometry("720x520")


   tk.Label(register_widget, text="Email").grid(row=0, column=0, padx=20, pady=(20, 10))
   tk.Label(register_widget, text="Password").grid(row=1, column=0, padx=20, pady=(0, 10))


   e1 = tk.Entry(register_widget)
   e1.grid(row=0, column=1, padx=20, pady=(20, 10))
   e2 = tk.Entry(register_widget, show="*")
   e2.grid(row=1, column=1, padx=20, pady=(0, 10))


   register_button = tk.Button(register_widget, text="Create", command=create)
   register_button.grid(row=2, column=1, pady=(20, 20))


   back_button = tk.Button(register_widget, text="Return", command=lambda: [register_widget.destroy(), main_menu()])
   back_button.place(x=30, y=450)


   register_widget.grid_columnconfigure((0, 1), weight=1)
   register_widget.mainloop()


def login():
  login_widget = tk.Tk()
  login_widget.title("Login")
  login_widget.geometry("720x520")

  tk.Label(login_widget, text="Email").grid(row=0, column=0, padx=20, pady=(20, 10))
  tk.Label(login_widget, text="Password").grid(row=1, column=0, padx=20, pady=(0, 10))

  e1 = tk.Entry(login_widget)
  e1.grid(row=0, column=1, padx=20, pady=(20, 10))
  e2 = tk.Entry(login_widget, show="*")
  e2.grid(row=1, column=1, padx=20, pady=(0, 10))


  def check():
      if valid_email(e1) and valid_password(e2):
          login_widget.destroy()
          main_page()


  login_button = tk.Button(login_widget, text="Login", command=check)
  login_button.grid(row=2, column=1, pady=(20, 20))


  back_button = tk.Button(login_widget, text="Return", command=lambda: [login_widget.destroy(), main_menu()])
  back_button.place(x=30,y=450)


  login_widget.grid_columnconfigure((0, 1), weight=1)
  login_widget.mainloop()




def main_menu():
  window = tk.Tk()
  window.title("Booking Interface")
  window.geometry("720x520")


  login_label = tk.Label(window, text="Login to continue", font=("Helvetica", 16))
  login_label.grid(row=1, column=0, columnspan=3, pady=(40, 20))




  button = tk.Button(window, text="Login", command=lambda: [window.destroy(), login()])
  button.grid(row=2, column=0, columnspan=3, pady=(0, 20))


  button = tk.Button(window, text="Register", command=lambda: [window.destroy(), register()])
  button.grid(row=3, column=0, columnspan=3, pady=(0, 20))


  button = tk.Button(window, text="Staff Login", command=lambda: [window.destroy(), staff_login()])
  button.grid(row=4, column=0, columnspan=3, pady=(0, 20))


  window.grid_columnconfigure(0, weight=1)
  window.grid_columnconfigure(1, weight=0)
  window.grid_columnconfigure(2, weight=0)
  window.mainloop()




def main_page():
  MainWindow = tk.Tk()
  MainWindow.title("Main Menu")
  MainWindow.geometry("720x520")


  logout_button = tk.Button(MainWindow, text="Logout", width=10, command=lambda: [MainWindow.destroy(), main_menu()])
  logout_button.place(x=50,y=450)


  title = tk.Label(MainWindow, text="Barber Bookings", font=("Helvetica", 18, "bold"))
  title.grid(row=1, column=0, columnspan=3, pady=(20, 40))




  booking_label = tk.Label(MainWindow, text="Bookings", font=("Helvetica", 12))
  booking_label.place(x=50,y=120)
  booking_button = tk.Button(MainWindow, text="Continue")
  booking_button.place(x=50,y=175)




  analytics_label = tk.Label(MainWindow, text="Predictive Analytics", font=("Helvetica", 12))
  analytics_label.place(x=200,y=120)
  analytics_button = tk.Button(MainWindow, text="Continue")
  analytics_button.place(x=200,y=175)


  pricing_label = tk.Label(MainWindow, text="Pricing", font=("Helvetica", 12))
  pricing_label.place(x=400,y=120)
  pricing_button = tk.Button(MainWindow, text="Continue")
  pricing_button.place(x=400,y=175)




  MainWindow.grid_columnconfigure(0, weight=1)
  MainWindow.grid_columnconfigure(1, weight=0)
  MainWindow.grid_columnconfigure(2, weight=0)
  MainWindow.mainloop()


def staff_page():
  MainWindow = tk.Tk()
  MainWindow.title("Main Menu")
  MainWindow.geometry("720x520")


  logout_button = tk.Button(MainWindow, text="Logout", width=10,command=lambda: [MainWindow.destroy(), main_menu()])
  logout_button.place(x=50, y=450)


  title = tk.Label(MainWindow, text="Barber Bookings", font=("Helvetica", 18, "bold"))
  title.grid(row=1, column=0, columnspan=3, pady=(20, 40))


  booking_label = tk.Label(MainWindow, text="Bookings", font=("Helvetica", 12))
  booking_label.place(x=50, y=120)
  booking_button = tk.Button(MainWindow, text="Continue")
  booking_button.place(x=50, y=175)


  analytics_label = tk.Label(MainWindow, text="Predictive Analytics", font=("Helvetica", 12))
  analytics_label.place(x=200, y=120)
  analytics_button = tk.Button(MainWindow, text="Continue")
  analytics_button.place(x=200, y=175)


  pricing_label = tk.Label(MainWindow, text="Pricing", font=("Helvetica", 12))
  pricing_label.place(x=400, y=120)
  pricing_button = tk.Button(MainWindow, text="Continue")
  pricing_button.place(x=400, y=175)


  financials_label = tk.Label(MainWindow, text="Financials", font=("Helvetica", 12))
  financials_label.place(x=50, y=250)
  financials_button = tk.Button(MainWindow, text="Continue", font=("Helvetica", 12),command=lambda: [MainWindow.destroy(), financials()])
  financials_button.place(x=50,y=300)


  predictions_label = tk.Label(MainWindow, text="Predictions", font=("Helvetica", 12))
  predictions_label.place(x=50, y=250)
  predictions_button = tk.Button(MainWindow, text="Continue", font=("Helvetica", 12),command=lambda: [MainWindow.destroy(), financials()])
  predictions_button.place(x=50,y=300)




  MainWindow.mainloop()




main_menu()
