# To-Do List Application

A task management application built with Python and Tkinter that helps you organize, track, and complete your tasks efficiently.

## Features

### Task Management
- **Add Tasks**: Create new tasks with title, deadline, and priority level (Low/Medium/High)
- **Edit Tasks**: Modify task titles and deadlines after creation
- **Delete Tasks**: Remove tasks you no longer need
- **Mark as Complete**: Check off tasks when they're done
- **Search Tasks**: Quickly find tasks using the search bar

### Task Organization
- **Priority Levels**: Assign Low, Medium, or High priority to tasks
- **Deadline Management**: Set deadlines in DD-MM-YYYY format
- **Sort Options**: 
  - Sort by deadline
  - Sort by color (priority and deadline-based)

### Time Tracking
- **Duration Setting**: Set expected duration for tasks with:
  - Hours
  - Minutes
  - Seconds
- **Timer Functionality**:
  - Start/Stop timer for active tasks
  - Track elapsed time
  - Resume timer from where you left off
  - Progress percentage display
- **Completion Tracking**:
  - Automatic progress calculation
  - Congratulations message when task is completed

### Visual Organization
- **Dual View Modes**:
  1. List View:
     - Comprehensive task details
     - Color-coded priorities
     - Progress information
  2. Calendar View:
     - Monthly overview
     - Color-coded dates based on task priorities
     - Multiple tasks per day support

### Color Coding System
Tasks are color-coded based on their status, deadline, and priority:
- **Gray**: Completed tasks
- **Purple**: Past deadline
- **Red**: Due today with High/Medium priority
- **Orange**: Due today with Low priority OR due tomorrow/day after with High/Medium priority
- **Green**: Due tomorrow/day after with Low priority OR due later with High/Medium priority
- **Black**: All other cases

### Data Management
- **Export to CSV**: Save your tasks to a CSV file
- **Import from CSV**: Load tasks from a CSV file
- **Persistent Storage**: All tasks are automatically saved to a local database

### User Interface
- **Dark/Light Mode**: Toggle between dark and light themes
- **Color Legend**: Quick reference for the color coding system
- **Real-time Updates**: Task list updates automatically when:
  - Adding/editing tasks
  - Starting/stopping timers
  - Marking tasks as complete

## Technical Requirements
- Python 3.x
- Required packages:
  - tkinter
  - tkcalendar
  - sqlite3

## Getting Started
1. Ensure Python 3.x is installed on your system
2. Install required packages:
   ```bash
   pip install tkcalendar
   ```
3. Run the application:
   ```bash
   python project.py
   ```

## Usage Tips
1. **Adding Tasks**:
   - Fill in the task title
   - Select a deadline using the date picker
   - Choose a priority level
   - Click "Add Task"

2. **Time Tracking**:
   - Select a task
   - Click "Set Duration" to set expected completion time
   - Use "Start/Stop Timer" to track your progress
   - Timer continues from where you left off if interrupted

3. **Task Organization**:
   - Use the search bar to filter tasks
   - Toggle between list and calendar views
   - Sort tasks by deadline or priority colors
   - Check the color legend for quick priority reference

4. **Data Management**:
   - Export your tasks regularly using the CSV export feature
   - Import tasks from other sources using CSV import
   - All changes are automatically saved to the database

## Notes
- The application automatically saves all changes
- Tasks can't be scheduled in the past
- Timer progress is preserved between application restarts
- Multiple tasks can share the same deadline
- The calendar view shows the highest priority color for dates with multiple tasks 