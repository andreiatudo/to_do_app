import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import sqlite3
from datetime import datetime, timedelta
import csv
from tkcalendar import DateEntry

class ToDoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("To-Do List")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)

        self.theme = "light"
        self.colors = {
            "light": {"bg": "#f0f4f7", "fg": "#000", "entry_bg": "#fff", "entry_fg": "#000",
                     "button_bg": "#dbe9f4", "listbox_bg": "#fff", "placeholder": "#999"},
            "dark": {"bg": "#121212", "fg": "#fff", "entry_bg": "#1f1f1f", "entry_fg": "#fff",
                    "button_bg": "#333", "listbox_bg": "#1f1f1f", "placeholder": "#aaa"}
        }

        self.conn = sqlite3.connect("todo.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, deadline TEXT,
            priority TEXT, completed BOOLEAN)""")
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
        self.task_entry.grid(row=0, column=2, pady=3, padx=1)
        
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
        add_task_frame.grid(row=2, column=0, pady=5)
        ttk.Button(add_task_frame, text="Add Task", command=self.add_task).pack()

        sort_frame = ttk.Frame(self.main_frame)
        sort_frame.grid(row=3, column=0, pady=5)
        ttk.Button(sort_frame, text="Sort by Color", command=self.sort_by_color).grid(row=0, column=0, padx=3)
        ttk.Button(sort_frame, text="Sort by Deadline", command=self.load_tasks).grid(row=0, column=1, padx=3)

        self.search_frame = ttk.Frame(self.main_frame)
        self.search_frame.grid(row=4, column=0, sticky="we", pady=5)
        self.search_frame.columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var, width=40)
        self.search_entry.grid(row=0, column=0, sticky="we")
        self.search_is_placeholder = True
        self.search_entry.insert(0, "Search task...")
        self.search_entry.bind("<FocusIn>", lambda e: self.set_search_placeholder(False))
        self.search_entry.bind("<FocusOut>", lambda e: self.set_search_placeholder(True) if not self.search_var.get() else None)

        self.listbox = tk.Listbox(self.main_frame, height=10, font=12)
        self.listbox.grid(row=5, column=0, sticky="nsew", pady=5)
        self.main_frame.rowconfigure(5, weight=1)

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
        btn_frame.grid(row=6, column=0, pady=5)
        actions = [
            ("Delete Task", self.delete_task),
            ("Task Completed", self.complete_task),
            ("Edit Task", self.edit_task),
            ("Export CSV", self.export_csv),
            ("Import CSV", self.import_csv),
        ]
        for i, (text, cmd) in enumerate(actions):
            ttk.Button(btn_frame, text=text, command=cmd).grid(row=0, column=i, padx=5)

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
        task_id, title, deadline, priority, completed = task_info
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

    def load_tasks(self):
        self.listbox.delete(0, tk.END)
        self.displayed_task_ids = []
        search_term = "" if self.search_is_placeholder else self.search_var.get().lower()

        self.cursor.execute("SELECT id, title, deadline, priority, completed FROM tasks ORDER BY deadline ASC, priority DESC")
        tasks = self.cursor.fetchall()

        for task in tasks:
            task_id, title, deadline, priority, completed = task
            if search_term and search_term not in title.lower():
                continue
            status = "✔" if completed else "✘"
            display_text = f"{status} {title} (Deadline: {deadline}, Priority: {priority})"
            self.listbox.insert(tk.END, display_text)
            self.displayed_task_ids.append(task_id)
            self.listbox.itemconfig(len(self.displayed_task_ids) - 1, {'fg': self.get_task_color(task)})

    def sort_by_color(self):
        self.listbox.delete(0, tk.END)
        self.displayed_task_ids = []
        self.cursor.execute("SELECT id, title, deadline, priority, completed FROM tasks")
        tasks = self.cursor.fetchall()
        color_priority = {"purple": 0, "red": 1, "orange": 2, "green": 3, "black": 4, "#888": 5}
        sorted_tasks = sorted(tasks, key=lambda task: color_priority.get(self.get_task_color(task), 6))
        
        for task in sorted_tasks:
            task_id, title, deadline, priority, completed = task
            status = "✔" if completed else "✘"
            display_text = f"{status} {title} (Deadline: {deadline}, Priority: {priority})"
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

if __name__ == "__main__":
    root = tk.Tk()
    app = ToDoApp(root)
    root.mainloop()