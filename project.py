import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import sqlite3
from datetime import datetime, timedelta
import csv
from tkcalendar import DateEntry, Calendar
import time
import threading

class ToDoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("To-Do List")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)

        # Add timer related variables
        self.active_timer_id = None
        self.timer_running = False
        self.timer_thread = None
        self.timer_start_time = 0
        self.timer_accumulated_time = {}  # Store accumulated time for each task

        self.theme = "light"
        self.colors = {
            "light": {"bg": "#f0f4f7", "fg": "#000", "entry_bg": "#fff", "entry_fg": "#000",
                     "button_bg": "#dbe9f4", "listbox_bg": "#fff", "placeholder": "#999"},
            "dark": {"bg": "#121212", "fg": "#fff", "entry_bg": "#1f1f1f", "entry_fg": "#fff",
                    "button_bg": "#333", "listbox_bg": "#1f1f1f", "placeholder": "#aaa"}
        }

        self.conn = sqlite3.connect("todo.db")
        self.cursor = self.conn.cursor()
        
        # Create base table if it doesn't exist
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            deadline TEXT,
            priority TEXT,
            completed BOOLEAN
        )""")
        
        # Check if new columns exist and add them if they don't
        existing_columns = [col[1] for col in self.cursor.execute("PRAGMA table_info(tasks)").fetchall()]
        
        if "duration" not in existing_columns:
            self.cursor.execute("ALTER TABLE tasks ADD COLUMN duration INTEGER DEFAULT NULL")
        
        if "elapsed_time" not in existing_columns:
            self.cursor.execute("ALTER TABLE tasks ADD COLUMN elapsed_time INTEGER DEFAULT 0")
            
        self.conn.commit()

        self.task_var, self.deadline_var = tk.StringVar(), tk.StringVar()
        self.priority_var, self.search_var = tk.StringVar(value="Medium"), tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.load_tasks() if not self.search_is_placeholder else None)
        self.default_date = datetime.today().strftime("%d-%m-%Y")
        self.date_format = "%d-%m-%Y"
        self.displayed_task_ids = []
        self.legend_visible = False
        
        self.build_ui()
        self.apply_theme()
        self.load_tasks()
        self.root.after(1000, self.check_reminders)

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.columnconfigure(0, weight=1)

        theme_frame = ttk.Frame(self.main_frame)
        theme_frame.grid(row=0, column=0, pady=(0,5))
        self.theme_button = ttk.Button(theme_frame, text="🌙 Dark mode", command=self.toggle_theme)
        self.theme_button.pack()

        input_frame = ttk.Frame(self.main_frame, padding=5)
        input_frame.grid(row=1, column=0, pady=5, sticky="nsew")
        for i in range(4): input_frame.columnconfigure(i, weight=1 if i in [0,3] else 0)
        
        ttk.Label(input_frame, text="Task:", anchor="center", width=20).grid(row=0, column=1, pady=3)
        self.task_entry = ttk.Entry(input_frame, textvariable=self.task_var, width=40)
        self.task_entry.grid(row=0, column=2, pady=3)
        
        ttk.Label(input_frame, text="Deadline:", anchor="center", width=20).grid(row=1, column=1, pady=3)
        date_frame = ttk.Frame(input_frame)
        date_frame.grid(row=1, column=2, pady=3)
        self.deadline_entry = DateEntry(date_frame, width=38, 
                                     background='darkblue', foreground='white',
                                     borderwidth=2, date_pattern='dd-mm-yyyy',
                                     textvariable=self.deadline_var)
        self.deadline_entry.pack(fill='x')
        
        ttk.Label(input_frame, text="Priority:", anchor="center", width=20).grid(row=2, column=1, pady=3)
        self.priority_menu = tk.OptionMenu(input_frame, self.priority_var, "Low", "Medium", "High")
        self.priority_menu.config(width=36)
        self.priority_menu.grid(row=2, column=2, pady=3)

        add_task_frame = ttk.Frame(self.main_frame)
        add_task_frame.grid(row=3, column=0, pady=5)
        ttk.Button(add_task_frame, text="Add Task", command=self.add_task).pack()

        sort_frame = ttk.Frame(self.main_frame)
        sort_frame.grid(row=4, column=0, pady=5)
        ttk.Button(sort_frame, text="Sort by Color", command=self.sort_by_color).grid(row=0, column=0, padx=3)
        ttk.Button(sort_frame, text="Sort by Deadline", command=self.load_tasks).grid(row=0, column=1, padx=3)
        self.view_button = ttk.Button(sort_frame, text="Toggle Calendar View", command=self.toggle_view)
        self.view_button.grid(row=0, column=2, padx=3)

        self.search_frame = ttk.Frame(self.main_frame)
        self.search_frame.grid(row=5, column=0, sticky="we", pady=5)
        self.search_frame.columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var, width=40)
        self.search_entry.grid(row=0, column=0, sticky="we")
        self.search_is_placeholder = True
        self.search_entry.insert(0, "Search task...")
        self.search_entry.bind("<FocusIn>", lambda e: self.set_search_placeholder(False))
        self.search_entry.bind("<FocusOut>", lambda e: self.set_search_placeholder(True) if not self.search_var.get() else None)

        # Create both list and calendar views
        self.list_frame = ttk.Frame(self.main_frame)
        self.list_frame.grid(row=6, column=0, sticky="nsew", pady=5)
        self.list_frame.grid_remove()  # Initially hidden
        
        self.listbox = tk.Listbox(self.list_frame, height=10, font=("TkDefaultFont", 12))
        self.listbox.pack(fill=tk.BOTH, expand=True)
        
        # Calendar view
        self.calendar_frame = ttk.Frame(self.main_frame)
        self.calendar_frame.grid(row=6, column=0, sticky="nsew", pady=5)
        self.calendar = Calendar(self.calendar_frame, selectmode='none', date_pattern='dd-mm-yyyy')
        self.calendar.pack(fill=tk.BOTH, expand=True)
        
        self.current_view = "list"
        self.toggle_view()  # Initialize the view

        self.legend_text = "Color Legend:\nGray – Completed\nPurple – Deadline passed\nRed – Deadline today & priority High/Medium\n" + \
                         "Orange – Deadline today & Low OR tomorrow/the day after & High/Medium\n" + \
                         "Green – Tomorrow/the day after & Low OR after the day after & High/Medium\n" + \
                         "Black – All other cases"
        self.legend_label = ttk.Label(self.main_frame, text=self.legend_text, justify="left", anchor="w")
        self.legend_label.grid(row=7, column=0, sticky="w", pady=(5, 0))
        self.legend_label.grid_remove()
        self.legend_button = ttk.Button(self.main_frame, text="Show Color Legend", 
                                     command=lambda: self.toggle_widget(self.legend_label, self.legend_button))
        self.legend_button.grid(row=8, column=0, pady=5)

        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.grid(row=9, column=0, pady=5)
        actions = [
            ("Delete Task", self.delete_task),
            ("Task Completed", self.complete_task),
            ("Edit Task", self.edit_task),
            ("Edit Deadline", self.edit_deadline),
            ("Set Duration", self.set_task_duration),
            ("Start/Stop Timer", self.toggle_timer),
            ("Export CSV", self.export_csv),
            ("Import CSV", self.import_csv),
        ]
        for i, (text, cmd) in enumerate(actions):
            ttk.Button(btn_frame, text=text, command=cmd).grid(row=0, column=i, padx=5)

        # Add timer label
        self.timer_label = ttk.Label(self.main_frame, text="No active timer", font=("TkDefaultFont", 10))
        self.timer_label.grid(row=10, column=0, pady=5)

    def toggle_widget(self, widget, button):
        if widget.winfo_viewable():
            widget.grid_remove()
            button.config(text=button["text"].replace("Hide", "Show"))
        else:
            widget.grid()
            button.config(text=button["text"].replace("Show", "Hide"))

    def set_search_placeholder(self, show_placeholder):
        if show_placeholder and not self.search_var.get():
            self.search_is_placeholder = True
            self.search_var.set("Search task...")
        elif not show_placeholder and self.search_is_placeholder:
            self.search_is_placeholder = False
            self.search_var.set("")
        ttk.Style().configure("TEntry", foreground=self.colors[self.theme]["placeholder" if self.search_is_placeholder else "entry_fg"])

    def apply_theme(self):
        c = self.colors[self.theme]
        self.root.configure(bg=c["bg"])
        style = ttk.Style()
        style.theme_use("clam")
        for widget, props in {
            "TFrame": {"background": c["bg"]},
            "TLabel": {"background": c["bg"], "foreground": c["fg"]},
            "TEntry": {"fieldbackground": c["entry_bg"], "foreground": c["entry_fg"]},
            "TButton": {"background": c["button_bg"], "foreground": c["fg"]}
        }.items():
            style.configure(widget, **props)
        style.map("TButton", background=[("active", c["button_bg"])])
        
        self.deadline_entry.configure(
            background=c["entry_bg"] if self.theme == "light" else "#333",
            foreground=c["entry_fg"], selectbackground="#6aa6d6" if self.theme == "light" else "#555"
        )
        self.listbox.configure(bg=c["listbox_bg"], fg=c["fg"], 
                             selectbackground="#6aa6d6", selectforeground=c["entry_fg"])
        self.priority_menu.config(bg=c["entry_bg"], fg=c["entry_fg"], activebackground=c["button_bg"], 
                                activeforeground=c["fg"], highlightbackground=c["bg"], highlightthickness=1)
        self.theme_button.config(text="🌙 Dark mode" if self.theme == "light" else "☀ Light mode")
        
        if self.search_is_placeholder:
            style.configure("TEntry", foreground=c["placeholder"])

    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        self.apply_theme()

    def add_task(self):
        task = self.task_var.get().strip()
        deadline = self.deadline_var.get().strip()
        priority = self.priority_var.get()
        
        if not task:
            return messagebox.showwarning("ERROR", "Add a task!")
            
        try:
            deadline_date = datetime.strptime(deadline, self.date_format).date()
            if deadline_date < datetime.today().date():
                return messagebox.showerror("Invalid Date", "Deadline cannot be in the past!")
                
            self.cursor.execute(
                "INSERT INTO tasks (title, deadline, priority, completed) VALUES (?, ?, ?, ?)",
                (task, deadline, priority, False)
            )
            self.conn.commit()
            self.task_var.set("")
            self.deadline_entry.set_date(datetime.today())
            self.load_tasks()
        except ValueError as e:
            messagebox.showwarning("ERROR", f"Date format issue: {str(e)}")

    def get_task_color(self, task_info):
        task_id, title, deadline, priority, completed, duration, elapsed_time = task_info
        if completed: return "#888"
        
        try:
            deadline_date = datetime.strptime(deadline, self.date_format).date()
        except ValueError:
            deadline_date = datetime.today().date() + timedelta(days=999)

        today = datetime.today().date()
        tomorrow = today + timedelta(days=1)
        day_after = today + timedelta(days=2)
        
        if deadline_date < today:
            return "purple"
        elif deadline_date == today and priority in ("High", "Medium"):
            return "red"
        elif deadline_date == today and priority == "Low" or \
             deadline_date in [tomorrow, day_after] and priority in ("High", "Medium"):
            return "orange"
        elif deadline_date in [tomorrow, day_after] and priority == "Low" or \
             deadline_date > day_after and priority in ("High", "Medium"):
            return "green"
        return "black"

    def format_time(self, seconds):
        if seconds is None:
            return ""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}h{minutes:02d}m{secs:02d}s"
        elif minutes > 0:
            return f"{minutes}m{secs:02d}s"
        return f"{secs}s"

    def load_tasks(self):
        self.listbox.delete(0, tk.END)
        self.displayed_task_ids = []
        search_term = "" if self.search_is_placeholder else self.search_var.get().lower()

        self.cursor.execute("""
            SELECT id, title, deadline, priority, completed, duration, elapsed_time 
            FROM tasks ORDER BY deadline ASC, priority DESC
        """)
        tasks = self.cursor.fetchall()

        for task in tasks:
            task_id, title, deadline, priority, completed, duration, elapsed_time = task
            if search_term and search_term not in title.lower():
                continue
            
            status = "✔" if completed else "✘"
            time_info = ""
            if duration is not None:
                elapsed = elapsed_time or 0
                duration_str = self.format_time(duration)
                elapsed_str = self.format_time(elapsed)
                time_info = f", Duration: {duration_str}"
                if elapsed > 0:
                    percentage = min(100, int((elapsed / duration) * 100))
                    time_info += f" (Progress: {elapsed_str} - {percentage}%)"
                
            display_text = f"{status} {title} (Deadline: {deadline}, Priority: {priority}{time_info})"
            self.listbox.insert(tk.END, display_text)
            self.displayed_task_ids.append(task_id)
            self.listbox.itemconfig(len(self.displayed_task_ids) - 1, {'fg': self.get_task_color(task)})
            
        if self.current_view == "calendar":
            self.update_calendar_view()

    def sort_by_color(self):
        self.listbox.delete(0, tk.END)
        self.displayed_task_ids = []
        self.cursor.execute("SELECT id, title, deadline, priority, completed, duration, elapsed_time FROM tasks")
        tasks = self.cursor.fetchall()
        color_priority = {"purple": 0, "red": 1, "orange": 2, "green": 3, "black": 4, "#888": 5}
        sorted_tasks = sorted(tasks, key=lambda task: color_priority.get(self.get_task_color(task), 6))
        
        for task in sorted_tasks:
            task_id, title, deadline, priority, completed, duration, elapsed_time = task
            status = "✔" if completed else "✘"
            time_info = ""
            if duration is not None:
                elapsed = elapsed_time or 0
                if elapsed > 0:
                    hours = elapsed // 3600
                    minutes = (elapsed % 3600) // 60
                    time_info = f", Time: {hours}h{minutes}m"
                    if duration > 0:
                        percentage = min(100, int((elapsed / duration) * 100))
                        time_info += f" ({percentage}%)"
            display_text = f"{status} {title} (Deadline: {deadline}, Priority: {priority}{time_info})"
            self.listbox.insert(tk.END, display_text)
            self.displayed_task_ids.append(task_id)
            self.listbox.itemconfig(len(self.displayed_task_ids) - 1, {'fg': self.get_task_color(task)})

    def task_action(self, action_type):
        sel = self.listbox.curselection()
        if not sel:
            return messagebox.showwarning("ERROR", f"Select a task to {action_type}!")
        task_index = sel[0]
        if 0 <= task_index < len(self.displayed_task_ids):
            task_id = self.displayed_task_ids[task_index]
            if action_type == "delete":
                self.cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            elif action_type == "complete":
                self.cursor.execute("UPDATE tasks SET completed=1 WHERE id=?", (task_id,))
            elif action_type == "edit":
                self.cursor.execute("SELECT title FROM tasks WHERE id=?", (task_id,))
                current_title = self.cursor.fetchone()[0]
                new_title = simpledialog.askstring("Edit the task", "Modify the task:", initialvalue=current_title)
                if new_title:
                    self.cursor.execute("UPDATE tasks SET title=? WHERE id=?", (new_title, task_id))
            self.conn.commit()
            self.load_tasks()

    def delete_task(self): self.task_action("delete")
    def complete_task(self): self.task_action("complete")
    def edit_task(self): self.task_action("edit")

    def edit_deadline(self):
        sel = self.listbox.curselection()
        if not sel:
            return messagebox.showwarning("ERROR", "Select a task to edit deadline!")
        task_index = sel[0]
        if 0 <= task_index < len(self.displayed_task_ids):
            task_id = self.displayed_task_ids[task_index]
            
            # Create a top-level window for the date picker
            top = tk.Toplevel(self.root)
            top.title("Edit Deadline")
            top.geometry("300x150")
            
            # Add a date entry widget
            date_label = ttk.Label(top, text="Select new deadline:")
            date_label.pack(pady=10)
            date_picker = DateEntry(top, width=12, background='darkblue',
                                  foreground='white', borderwidth=2,
                                  date_pattern='dd-mm-yyyy')
            date_picker.pack(pady=10)
            
            def update_deadline():
                new_deadline = date_picker.get_date().strftime(self.date_format)
                if datetime.strptime(new_deadline, self.date_format).date() < datetime.today().date():
                    messagebox.showerror("Invalid Date", "Deadline cannot be in the past!")
                    return
                self.cursor.execute("UPDATE tasks SET deadline=? WHERE id=?", (new_deadline, task_id))
                self.conn.commit()
                self.load_tasks()
                top.destroy()
            
            # Add confirmation button
            ttk.Button(top, text="Update Deadline", command=update_deadline).pack(pady=10)
            
            # Center the window
            top.transient(self.root)
            top.grab_set()
            self.root.wait_window(top)

    def export_csv(self):
        with open("tasks.csv", "w", newline='') as f:
            w = csv.writer(f)
            w.writerow(["Title", "Deadline", "Priority", "Completed"])
            self.cursor.execute("SELECT title, deadline, priority, completed FROM tasks")
            w.writerows(self.cursor.fetchall())
        messagebox.showinfo("Success", "Exported successfully!")

    def import_csv(self):
        try:
            with open("tasks.csv", "r") as f:
                r = csv.reader(f)
                next(r)
                for row in r:
                    self.cursor.execute("INSERT INTO tasks (title, deadline, priority, completed) VALUES (?, ?, ?, ?)", row)
                self.conn.commit()
            self.load_tasks()
            messagebox.showinfo("Success", "Imported successfully!")
        except FileNotFoundError:
            messagebox.showerror("Error", "tasks.csv file not found")

    def check_reminders(self):
        self.cursor.execute("SELECT title, deadline FROM tasks WHERE completed=0")
        today = datetime.today().date()
        reminders = []
        for title, dl in self.cursor.fetchall():
            try:
                deadline_date = datetime.strptime(dl, self.date_format).date()
                if deadline_date == today:
                    reminders.append(f"Task '{title}' is due today!")
                elif deadline_date < today:
                    reminders.append(f"Missed deadline for task '{title}'!")
            except ValueError:
                pass
        if reminders: messagebox.showwarning("Reminders", "\n".join(reminders))
        self.root.after(3600000, self.check_reminders)

    def toggle_view(self):
        if self.current_view == "list":
            self.list_frame.grid_remove()
            self.calendar_frame.grid()
            self.current_view = "calendar"
            self.view_button.config(text="Show List View")
            self.update_calendar_view()
        else:
            self.calendar_frame.grid_remove()
            self.list_frame.grid()
            self.current_view = "list"
            self.view_button.config(text="Show Calendar View")
            self.load_tasks()
    
    def update_calendar_view(self):
        # Clear existing tags
        for tag in self.calendar.get_calevents():
            self.calendar.calevent_remove(tag)
            
        # Get all tasks for each date to determine highest priority
        self.cursor.execute("""
            SELECT deadline, GROUP_CONCAT(priority || ',' || completed || ',' || id) 
            FROM tasks 
            GROUP BY deadline
        """)
        date_tasks = self.cursor.fetchall()
        
        # Process each date's tasks
        for deadline, task_data in date_tasks:
            try:
                date = datetime.strptime(deadline, self.date_format).date()
                tasks = task_data.split(',')
                highest_priority = "Low"
                all_completed = True
                task_ids = []
                
                # Process tasks in groups of 3 (priority,completed,id)
                for i in range(0, len(tasks), 3):
                    priority = tasks[i]
                    completed = tasks[i+1] == "1"
                    task_id = tasks[i+2]
                    task_ids.append(task_id)
                    
                    if not completed:
                        all_completed = False
                        if priority == "High" or (priority == "Medium" and highest_priority == "Low"):
                            highest_priority = priority
                
                # Get task titles for this date
                task_id_list = ','.join(task_ids)
                self.cursor.execute(f"SELECT title FROM tasks WHERE id IN ({task_id_list})")
                titles = [row[0] for row in self.cursor.fetchall()]
                combined_title = "; ".join(titles)
                
                # Determine color based on highest priority task
                if all_completed:
                    color = "#888888"  # Gray for completed
                else:
                    # Use the same color logic as get_task_color
                    today = datetime.today().date()
                    tomorrow = today + timedelta(days=1)
                    day_after = today + timedelta(days=2)
                    
                    if date < today:
                        color = "purple"
                    elif date == today and highest_priority in ("High", "Medium"):
                        color = "red"
                    elif date == today and highest_priority == "Low" or \
                         date in [tomorrow, day_after] and highest_priority in ("High", "Medium"):
                        color = "orange"
                    elif date in [tomorrow, day_after] and highest_priority == "Low" or \
                         date > day_after and highest_priority in ("High", "Medium"):
                        color = "green"
                    else:
                        color = "black"
                
                # Create calendar event
                tag = f"date_{deadline}"
                self.calendar.calevent_create(
                    date,
                    combined_title,
                    tags=[tag]
                )
                # Configure tag with color
                self.calendar.tag_config(tag, background=color)
            except (ValueError, IndexError):
                continue

    def set_task_duration(self):
        sel = self.listbox.curselection()
        if not sel:
            return messagebox.showwarning("ERROR", "Select a task to set duration!")
        task_index = sel[0]
        if 0 <= task_index < len(self.displayed_task_ids):
            task_id = self.displayed_task_ids[task_index]
            
            # Create a top-level window for duration input
            top = tk.Toplevel(self.root)
            top.title("Set Task Duration")
            top.geometry("300x200")
            
            # Add input fields for hours, minutes, and seconds
            input_frame = ttk.Frame(top)
            input_frame.pack(pady=10)
            
            hours_var = tk.StringVar(value="0")
            minutes_var = tk.StringVar(value="0")
            seconds_var = tk.StringVar(value="0")
            
            # Hours
            ttk.Label(input_frame, text="Hours:").grid(row=0, column=0, padx=5)
            ttk.Entry(input_frame, textvariable=hours_var, width=10).grid(row=0, column=1, padx=5)
            
            # Minutes
            ttk.Label(input_frame, text="Minutes:").grid(row=1, column=0, padx=5, pady=5)
            ttk.Entry(input_frame, textvariable=minutes_var, width=10).grid(row=1, column=1, padx=5, pady=5)
            
            # Seconds
            ttk.Label(input_frame, text="Seconds:").grid(row=2, column=0, padx=5)
            ttk.Entry(input_frame, textvariable=seconds_var, width=10).grid(row=2, column=1, padx=5)
            
            def set_duration():
                try:
                    hours = int(hours_var.get())
                    minutes = int(minutes_var.get())
                    seconds = int(seconds_var.get())
                    
                    if hours < 0 or minutes < 0 or seconds < 0:
                        raise ValueError("Time values cannot be negative")
                    if minutes >= 60 or seconds >= 60:
                        raise ValueError("Minutes and seconds must be less than 60")
                        
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                    self.cursor.execute("UPDATE tasks SET duration=? WHERE id=?", (total_seconds, task_id))
                    self.conn.commit()
                    self.load_tasks()
                    top.destroy()
                except ValueError as e:
                    messagebox.showerror("Invalid Input", str(e))
            
            def set_unknown():
                self.cursor.execute("UPDATE tasks SET duration=NULL WHERE id=?", (task_id,))
                self.conn.commit()
                self.load_tasks()
                top.destroy()
            
            # Add buttons
            button_frame = ttk.Frame(top)
            button_frame.pack(pady=10)
            ttk.Button(button_frame, text="Set Duration", command=set_duration).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Unknown Duration", command=set_unknown).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=top.destroy).pack(side=tk.LEFT, padx=5)
            
            # Center the window
            top.transient(self.root)
            top.grab_set()
            self.root.wait_window(top)

    def toggle_timer(self):
        sel = self.listbox.curselection()
        if not sel:
            return messagebox.showwarning("ERROR", "Select a task to toggle timer!")
        
        task_index = sel[0]
        if 0 <= task_index < len(self.displayed_task_ids):
            task_id = self.displayed_task_ids[task_index]
            
            if self.timer_running and self.active_timer_id == task_id:
                # Stop timer
                self.timer_running = False
                current_time = time.time()
                elapsed = int(current_time - self.timer_start_time)
                self.timer_accumulated_time[task_id] = self.timer_accumulated_time.get(task_id, 0) + elapsed
                
                # Update database
                self.cursor.execute("UPDATE tasks SET elapsed_time=? WHERE id=?", 
                                 (self.timer_accumulated_time[task_id], task_id))
                self.conn.commit()
                
                self.timer_label.config(text="No active timer")
                self.active_timer_id = None
                
                # Refresh the task list to show updated time
                self.load_tasks()
                if self.current_view == "calendar":
                    self.update_calendar_view()
            else:
                # Stop any running timer first
                if self.timer_running:
                    self.toggle_timer()  # This will stop the current timer
                
                # Start new timer
                self.timer_running = True
                self.active_timer_id = task_id
                
                # Get existing elapsed time from database
                self.cursor.execute("SELECT elapsed_time FROM tasks WHERE id=?", (task_id,))
                elapsed_time = self.cursor.fetchone()[0] or 0
                self.timer_accumulated_time[task_id] = elapsed_time
                
                self.timer_start_time = time.time()
                self.update_timer()

    def update_timer(self):
        if not self.timer_running:
            return
            
        current_time = time.time()
        elapsed = int(current_time - self.timer_start_time)
        
        # Create a new connection for this thread
        thread_conn = sqlite3.connect("todo.db")
        thread_cursor = thread_conn.cursor()
        
        try:
            thread_cursor.execute("SELECT title, duration FROM tasks WHERE id=?", (self.active_timer_id,))
            task = thread_cursor.fetchone()
            if task:
                title, duration = task
                total_elapsed = self.timer_accumulated_time.get(self.active_timer_id, 0) + elapsed
                
                # Update elapsed time
                thread_cursor.execute("UPDATE tasks SET elapsed_time=? WHERE id=?", 
                                   (total_elapsed, self.active_timer_id))
                thread_conn.commit()
                
                # Format display text
                hours = total_elapsed // 3600
                minutes = (total_elapsed % 3600) // 60
                seconds = total_elapsed % 60
                timer_text = f"Timer for '{title}': {hours:02d}:{minutes:02d}:{seconds:02d}"
                
                if duration:
                    percentage = min(100, int((total_elapsed / duration) * 100))
                    timer_text += f" ({percentage}%)"
                    
                    # Show congratulations message when task is completed
                    if total_elapsed >= duration and self.timer_running:
                        self.timer_running = False
                        messagebox.showinfo("Congratulations!", f"You have completed the task: {title}!")
                        self.timer_label.config(text="No active timer")
                        self.active_timer_id = None
                        return
                
                self.timer_label.config(text=timer_text)
        finally:
            thread_cursor.close()
            thread_conn.close()
            
        if self.timer_running:
            self.root.after(1000, self.update_timer)

if __name__ == "__main__":
    root = tk.Tk()
    app = ToDoApp(root)
    root.mainloop()