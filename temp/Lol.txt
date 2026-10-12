import random
import pickle
import mysql.connector
import os
import datetime

con = mysql.connector.connect(
    host="localhost",
    user="root",
    password="moda",
    database="mydb"
)

if not con.is_connected():
    print("Could not connect to database!")
    exit(1)

cur = con.cursor()
PATH = os.path.dirname(__file__)
M31 = (1,3,5,7,8,10,12)


cur.execute(
    """CREATE TABLE IF NOT EXISTS tasks(
    id INT AUTO_INCREMENT PRIMARY KEY,
    task VARCHAR(100) NOT NULL,
    date DATE,
    due INT,
    category VARCHAR(20),
    recurring VARCHAR(10))"""
)
cur.execute(
    """CREATE TABLE IF NOT EXISTS completed_tasks(
    id INT AUTO_INCREMENT PRIMARY KEY,
    task VARCHAR(100) NOT NULL,
    completed_at DATE DEFAULT (CURRENT_DATE),
    category VARCHAR(20),
    recurring VARCHAR(10))"""
)
con.commit()


#HELPER FUNCTIONS
def today():
    return datetime.date.today().isoformat()

def motivate():
    try:
        f = open(PATH + r"\motivation.dat", 'rb')
        motivation = pickle.load(f)
        f.close()
        return random.choice(motivation)
    except Exception:
        return "Keep going, you're making great progress!"

def max_id():
    cur.execute("SELECT MAX(id) FROM tasks")
    n = cur.fetchall()[0][0]
    if not n:
        return 0
    return n

def get_ids():
    cur.execute("SELECT id FROM tasks")
    x = cur.fetchall()
    l = []
    for i in x:
        l.append(i[0])
    return l

def print_table(l, headers={'ID': 3, 'Task': 30, 'Date': 12, 'Due In(Days)': 13, 'Category': 15, 'Recurring': 10}):
    print('+', end='')
    for i in headers:
        print('-' * headers[i], end="+")
    print()

    print("|", end='')
    for i in headers:
        s = headers[i] - len(i)
        s1 = s // 2
        s2 = s - s1
        if s2 < 1:
            i = i[:headers[i] - 3] + '...'
        print(' ' * s1 + i + ' ' * s2, end='|')
    print()

    print('+', end='')
    for i in headers:
        print('-' * headers[i], end="+")
    print()

    m = list(headers.values())
    for row in l:
        print("|", end='')
        for i, item in enumerate(row):
            s = m[i] - len(str(item))
            s1 = s // 2
            s2 = s - s1
            if s2 < 0:
                item_str = str(item)[:m[i] - 3] + '...'
            else:
                item_str = str(item)
            print(' ' * s1 + item_str + ' ' * s2, end='|')
        print()

    print('+', end='')
    for i in headers:
        print('-' * headers[i], end="+")
    print()

import os
def clear_screen():
    os.system("cls")
    #for i in range(75):
    #    print("\n")


def is_leap_year(year):
    return year % 4 == 0

def days_in_month(month, year):
    if month in [1, 3, 5, 7, 8, 10, 12]:
        return 31
    elif month in [4, 6, 9, 11]:
        return 30
    elif month == 2:
        return 29 if is_leap_year(year) else 28
    return 0

def date_to_days(date_str):
    y, m, d = map(int, date_str.split('-'))
    total_days = 0
    for year in range(1, y):
        total_days += 366 if is_leap_year(year) else 365
    for month in range(1, m):
        total_days += days_in_month(month, y)
    total_days += d
    return total_days

def calculate_due(date1, date2):
    return date_to_days(date2) - date_to_days(date1)

def get_next_recurring_date(current_date_str, recurring_type):
    if not current_date_str:
        current_date_str = today()
    if recurring_type is None:
        return current_date_str

    y, m, d = map(int, current_date_str.split('-'))

    if recurring_type.upper() == 'DAILY':
        d += 1
        if d > days_in_month(m, y):
            d = 1
            m += 1
            if m > 12:
                m = 1
                y += 1
    elif recurring_type.upper() == 'WEEKLY':
        d += 7
        max_days = days_in_month(m, y)
        if d > max_days:
            d -= max_days
            m += 1
            if m > 12:
                m = 1
                y += 1
    elif recurring_type.upper() == 'MONTHLY':
        m += 1
        if m > 12:
            m = 1
            y += 1
        #month-end boundary condition(Jan 31 -> Feb 28)
        max_days = days_in_month(m, y)
        d = min(d, max_days)
    else:
        return current_date_str

    return "{}-{}-{}".format(y,m,d)

def sync_due_dates():
    today = datetime.date.today()
    cur.execute("SELECT id, date FROM tasks WHERE date IS NOT NULL")
    records = cur.fetchall()

    for task_id, task_date in records:
        days_remaining = (task_date - today).days
        cur.execute("UPDATE tasks SET due = {} WHERE id = {}".format(days_remaining, task_id))

    con.commit()

def format_centered(text, width):
    text_str = str(text)
    length = len(text_str)
    if length >= width:
        return text_str[:width]
    total_padding = width - length
    left_padding = total_padding // 2
    right_padding = total_padding - left_padding
    return (" " * left_padding) + text_str + (" " * right_padding)

def get_day_of_week(year, month, day=1):
    t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
    if month < 3:
        year -= 1
    #Sakamoto's formula(0 for Sunday, 1 for Monday, etc.)
    dow_sun0 = (year + year // 4 - year // 100 + year // 400 + t[month - 1] + day) % 7
    return (dow_sun0 + 6) % 7


#INPUT FUNCTIONS
def pick_date():
    c = 1
    while c < 4:
        try:
            if c == 1:
                yr = input("Enter Year(Press Enter to Skip): ")
                if not yr:
                    return None
                yr = int(yr)
                if yr < 2026 or yr > 2099:
                    print("Year must be between 2026 and 2099")
                    continue
                c += 1
            if c == 2:
                mon = input("Enter Month(Press Enter to Skip): ")
                if not mon:
                    return None
                mon = int(mon)
                if mon < 1 or mon > 12:
                    print("Invalid Month!")
                    continue
                c += 1
            if c == 3:
                day = input("Enter Day(Press Enter to Skip): ")
                if not day:
                    return None
                day = int(day)
                if (mon in M31) and (day < 1 or day > 31):
                    print("Invalid Date for 31-day month")
                    continue
                elif (mon == 2) and (yr % 4 == 0) and (day < 1 or day > 29):
                    print("Leap Year cannot have more than 29 days in Feb")
                    continue
                elif (mon == 2) and (yr % 4 != 0) and (day < 1 or day > 28):
                    print("Non-Leap Year Feb cannot have more than 28 days")
                    continue
                elif (mon not in M31) and (day < 1 or day > 30):
                    print("Invalid Date for 30-day month")
                    continue
                c += 1
        except ValueError:
            print("Invalid Datatype, please enter only Integers.")
            continue
    return f"{yr}-{mon:02d}-{day:02d}"

def pick_recurring():
    print(
        """Select Recurrence Interval:
        - 1 None (Default)
        - 2 Daily
        - 3 Weekly
        - 4 Monthly"""
    )
    choice = input("Enter Choice (Press Enter to Skip): ")
    if choice == '2':
        return 'DAILY'
    elif choice == '3':
        return 'WEEKLY'
    elif choice == '4':
        return 'MONTHLY'
    return None


#MAIN FUNCTIONS
def add_task():
    while True:
        task = input("Enter Task Name: ")
        if not task:
            print("Please enter a non-empty task name")
            continue
        break
    date = pick_date()
    category = input("Enter Category(Press Enter to skip): ")
    recurring = pick_recurring()

    q = "INSERT INTO tasks (task,date,due,category,recurring) VALUES({})"
    #q= q.format(str(id))
    q= q.format("'" + task + "'{}")
    q = q.format(",'" + date + "'," + str(calculate_due(datetime.date.today().isoformat(), date)) + "{}" ) if date else q.format(",NULL,NULL{}")
    q = q.format(",'" + category.upper() + "'{}") if category else q.format(",NULL{}")
    q = q.format(",'" + recurring + "'") if recurring else q.format(",NULL{}")

    #print(q.format(''))
    cur.execute(q.format(''))
    con.commit()

    clear_screen()
    print("="*15+"TASK ADDED:"+"="*15)
    cur.execute("SELECT * FROM tasks WHERE id=" + str(max_id()))
    print_table(l=cur.fetchall())


def print_tasks():
    error=None
    while True:
        print(
            f"""SORT BY: 
            - 1 for Due Date (Default)
            - 2 for Category
            - 3 for Name
            {"\n"+error if error else ""}
            """
        )
        c = input()
        sync_due_dates()
        clear_screen()

        if not c:
            c=1
        try:
            c = int(c)
        except ValueError:
            error = "Please Enter a valid Integer"
            continue
        if c == 1:
            cur.execute("SELECT * FROM tasks ORDER BY due")
            print_table(l=cur.fetchall())
        elif c == 2:
            cur.execute("SELECT DISTINCT category FROM tasks")
            cats = cur.fetchall()
            d = {}
            flag = False
            for cat in cats:
                cat = cat[0]
                if cat is None:
                    flag = True
                    continue
                q = "SELECT * FROM tasks WHERE category='{}'".format(cat)
                cur.execute(q)
                d[cat] = cur.fetchall()
            if flag:
                cur.execute("SELECT * FROM tasks WHERE category IS NULL")
                d['NONE'] = cur.fetchall()
            for cat in d:
                print()
                print("="*15+"CATEGORY: "+cat+"="*15)
                print_table(l=d[cat])
        elif c == 3:
            cur.execute("SELECT * FROM tasks ORDER BY task")
            print_table(l=cur.fetchall())
        else:
            error = "Invalid Choice!"
            continue
        break


def delete_task():
    while True:
        id = input("Enter Task ID to Delete(press enter to cancel): ")
        if not id:
            break

        try:
            id = int(id)
        except ValueError:
            print("Please Enter a valid Integer.")
            continue

        if id not in get_ids():
            print("Task ID not found: ", id)
            continue

        clear_screen()
        cur.execute("SELECT * FROM tasks WHERE id=" + str(id))
        print("="*15+"SELECTED TASK: "+"="*15)
        print_table(l=cur.fetchall())
        print("\n")
        c = input("Are you sure?[y/n]: ").lower()
        if c == 'y':
            cur.execute("DELETE FROM tasks WHERE ID=" + str(id))
            con.commit()
            print("Task Deleted Successfully!")
            break
        elif c == 'n':
            print("User Cancelled!")
            continue


def modify_task():
    error=None

    while True:
        id = input("Enter Task ID to Modify(press enter to cancel): ")
        if not id:
            return

        try:
            id = int(id)
        except ValueError:
            print("Please Enter a valid Integer.")
            continue

        if id not in get_ids():
            print("Task ID not found: ", id)
            continue

        break

    while True:
        clear_screen()
        cur.execute("SELECT * FROM tasks WHERE id=" + str(id))
        clear_screen()
        print("="*15+"SELECTED TASK: "+"="*15)
        print_table(l=cur.fetchall())
        print()
        print(
            f"""Modify:
            - 0 Cancel Edit (Default)
            - 1 Name
            - 2 Category
            - 3 Date
            - 4 Recurring Interval
            {"\n"+error if error else ""}"""
        )
        error=None

        c = input()
        if not c:
            break

        try:
            c = int(c)
        except ValueError:
            error = "Please Enter a valid Integer."
            continue

        if c == 1:
            while True:
                name = input("Enter New Name: ")
                if not name:
                    print("Enter a Non-Empty Name")
                    continue
                break
            cur.execute("UPDATE tasks SET task='{}' WHERE ID={}".format(name, id))
            con.commit()
        elif c == 2:
            cat = input("Enter New Category(press enter to remove category): ")
            if cat:
                cur.execute("UPDATE tasks SET category='{}' WHERE ID={}".format(cat.upper(), id))
            else:
                cur.execute("UPDATE tasks SET category=NULL WHERE ID={}".format(id))
            con.commit()
        elif c == 3:
            date = pick_date()
            if date:
                due = calculate_due(datetime.date.today().isoformat(), date)
                cur.execute("UPDATE tasks SET date='{}', due={} WHERE ID={}".format(date, due, id))
            else:
                cur.execute("UPDATE tasks SET date=NULL, due=NULL WHERE ID={}".format(id))
            con.commit()
        elif c == 4:
            rec = pick_recurring()
            cur.execute("UPDATE tasks SET recurring='{}' WHERE ID={}".format(rec, id))
            con.commit()
        else:
            error = "Invalid Choice!"
            continue

        clear_screen()
        sync_due_dates()
        print("="*15+"Task Updated successfully!"+"="*15)
        cur.execute("SELECT * FROM tasks WHERE id={}".format(id))
        print_table(l=cur.fetchall())
        break


def toggle_complete():
    while True:
        id = input("Enter Task ID to Toggle Completion State(press enter to cancel): ")
        if not id:
            break

        try:
            id = int(id)
        except ValueError:
            print("Please Enter a valid Integer.")
            continue

        if id not in get_ids():
            print("Task ID not found: ", id)
            continue

        cur.execute("SELECT * FROM tasks WHERE id={}".format(id))
        row = cur.fetchall()[0]

        val = ""
        for i,item in enumerate(row):
            if i in (0,2,3):
                continue
            if item is None:
                val += "NULL,"
            elif isinstance(item, int):
                val += str(item) + ","
            else:
                val += "'" + str(item) + "',"
        val = val[:-1]
        cur.execute("INSERT INTO completed_tasks (task,category,recurring) VALUES({})".format(val))

        task_id, task_name, date_val, due_val, category_val, recurring_val = row
        if recurring_val and date_val:
            next_date = get_next_recurring_date(str(date_val), recurring_val)
            next_due = calculate_due(datetime.date.today().isoformat(), next_date)
            cur.execute(
                "UPDATE tasks SET date='{}', due={} WHERE id={}".format(next_date, next_due, id)
            )
            print("Recurring Task completed! Advanced next due date to: {}".format(next_date))
        else:
            cur.execute("DELETE FROM tasks WHERE id={}".format(id))
            print("Task Completed! Great Job, keep it up.")

        con.commit()
        break


def search_task():
    while True:
        keyword = input("Type to Search(press enter to return to main menu): ")
        sync_due_dates()
        if not keyword:
            break
        clear_screen()
        q = "SELECT * FROM tasks WHERE task LIKE '%{}%'".format(keyword)
        cur.execute(q)
        print("="*15+f"RESULTS FOR: {keyword}"+"="*15)
        print_table(l=cur.fetchall())


def view_completed_history():
    cur.execute("SELECT * FROM completed_tasks")
    completed = cur.fetchall()
    print("--- Completed Tasks Archive ---")
    if not completed:
        print("No completed tasks yet.")
        return

    print_table(l=completed,headers={'ID': 3, 'Task': 30, 'Completed At': 13, 'Category': 15, 'Recurring': 10})
    print(f"\nTotal tasks completed: {len(completed)}")


def view_overdue_tasks():
    sync_due_dates()
    cur.execute("SELECT * FROM tasks WHERE due < 0")
    overdue = cur.fetchall()

    if overdue:
        print("OVERDUE TASKS: ")
        print_table(l=overdue)
    else:
        print("No overdue tasks! You're all caught up.")


def print_monthly_calendar():
    import datetime
    while True:
        yr = input("Enter Year (Default Current Year): ")
        if not yr:
            yr = datetime.datetime.now().year
            break
        try:
            yr = int(yr)
        except ValueError:
            print("Please enter valid numeric integers for year and month.")
            continue
        break

    while True:
        mon = input("Enter Month (Default Current Month): ")
        if not mon:
            mon = datetime.datetime.now().month
            break
        try:
            mon = int(mon)
        except ValueError:
            print("Please enter valid numeric integers for year and month.")
            continue
        if mon < 1 or mon > 12:
            print("Invalid month! Must be between 1 and 12.")
            continue
        break
    
    clear_screen()

    total_days = days_in_month(mon, yr)

    start_date = "{:04d}-{:02d}-01".format(yr, mon)
    end_date = "{:04d}-{:02d}-{:02d}".format(yr, mon, total_days)

    cur.execute(
        "SELECT id, DAY(date) FROM tasks WHERE date BETWEEN %s AND %s",
        (start_date, end_date)
    )
    task_rows = cur.fetchall()

    tasks_by_day = {}
    for task_id, day_num in task_rows:
        if day_num not in tasks_by_day:
            tasks_by_day[day_num] = []
        tasks_by_day[day_num].append(str(task_id))

    month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    title = "{} {}".format(month_names[mon], yr)
    print("\n" + ("=" * 85))
    print(format_centered(title, 85))
    print("=" * 85)

    days_hdr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hdr_cells = []
    for h in days_hdr:
        hdr_cells.append(format_centered(h, 11))
    print("|" + "|".join(hdr_cells) + "|")

    divider_cells = []
    for _ in range(7):
        divider_cells.append("-" * 11)
    grid_divider = "+" + "+".join(divider_cells) + "+"
    print(grid_divider)

    start_weekday = get_day_of_week(yr, mon, 1)

    weeks = []
    current_week = [0] * start_weekday

    for day in range(1, total_days + 1):
        current_week.append(day)
        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []

    if current_week:
        while len(current_week) < 7:
            current_week.append(0)
        weeks.append(current_week)

    for week in weeks:
        date_line = "|"
        for day in week:
            if day == 0:
                date_line += (" " * 11) + "|"
            else:
                day_str = " {:<2}".format(day)
                pad_len = 11 - len(day_str)
                date_line += (" " * pad_len) + day_str + "|"
        print(date_line)

        task_line = "|"
        for day in week:
            if day == 0 or day not in tasks_by_day:
                task_line += (" " * 11) + "|"
            else:
                ids_str = "ID:" + ",".join(tasks_by_day[day])
                if len(ids_str) > 10:
                    ids_str = ids_str[:8] + ".."
                task_line += format_centered(ids_str, 11) + "|"
        print(task_line)

        print(grid_divider)
    print()


# MAIN LOOP
clear_screen()
error = None
while True:
    sync_due_dates()
    print(
        f"""Main Menu: 
        - 0 Exit
        - 1 View Tasks (Default)
        - 2 View Overdue Tasks
        - 3 Add Task
        - 4 Complete Task
        - 5 Search Task
        - 6 Modify Task
        - 7 Delete Task
        - 8 View Completed Tasks Archive
        - 9 Print Monthly Calender
        {"\n"+error if error else ""}"""
    )
    error = None
    c=input()
    clear_screen()

    if c=="":
        c = 1
    try:
        c = int(c)
    except ValueError:
        error = "Enter a valid Integer."
        continue

    if c == 0:
        while True:
            c = input("Are you sure you want to exit?[y/n]: ").lower()
            if 'y' in c:
                e=True
            elif 'n' in c:
                e=False
            else:
                print("Invalid Choice.")
                continue
            break
        if e:
            break
        else:
            continue
    elif c == 1:
        print_tasks()
        input("Press Enter to Continue...")
        clear_screen()
    elif c == 2:
        view_overdue_tasks()
        input("Press Enter to Continue...")
        clear_screen()
    elif c == 3:
        add_task()
        input("Press Enter to Continue...")
        clear_screen()
    elif c == 4:
        toggle_complete()
        print(motivate())
        input("Press Enter to Continue...")
        clear_screen()
    elif c == 5:
        search_task()
        clear_screen()
    elif c == 6:
        modify_task()
        input("Press Enter to Continue...")
        clear_screen()
    elif c == 7:
        delete_task()
        input("Press Enter to Continue...")
        clear_screen()
    elif c == 8:
        view_completed_history()
        input("Press Enter to Continue...")
        clear_screen()
    elif c == 9:
        print_monthly_calendar()
        input("Press Enter to Continue...")
        clear_screen()
    else:
        error = "Invalid Choice."
        clear_screen()
        continue

clear_screen()
print("Exiting...")
#exit(0)
