import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import git
import os
from datetime import datetime
import re
import queue
import json

class GitEvent:
    def __init__(self):
        self.title = ""
        self.date = ""
        self.description = ""
        self.created_branch = ""
        self.merged_branches = []
        self.merged_branches_info = []
        self.created_tag = ""
        self.notes = ""
        self.base_branch = ""

class GitEventManager:
    def __init__(self):
        print("Initializing GUI...")
        self.root = tk.Tk()
        print("GUI initialized successfully")
        
        # Set window title
        self.root.title("Git Event Manager")
        print("Window title set successfully")
        
        # Initialize path variable
        self.repo_path = tk.StringVar()  # Remove value=os.getcwd()
        
        # Set event storage path - move here
        self.events_base_path = os.path.expanduser("~/git_branch_manager/git_events")
        self.events_path = tk.StringVar(value=self.events_base_path)
        
        # Ensure base directory exists
        os.makedirs(self.events_base_path, exist_ok=True)
        
        # Initialize event storage related variables
        self.current_event_file = None
        self.events_by_date = {}  # Events organized by date
        self.events_by_branch = {}  # Events organized by branch
        
        # Initialize operation count
        self.operation_count = 0
        
        # Initialize variables
        self.base_type = tk.StringVar(value="branch")
        self.branch_prefix = tk.StringVar()
        self.branch_custom_suffix = tk.StringVar()
        self.branch_date_suffix = tk.StringVar(value=datetime.now().strftime('%Y.%m.%d'))
        self.final_branch_name = tk.StringVar()
        
        self.tag_prefix = tk.StringVar()
        self.tag_custom_suffix = tk.StringVar()
        self.tag_date_suffix = tk.StringVar(value=datetime.now().strftime('%Y.%m.%d'))
        self.final_tag_name = tk.StringVar()
        
        self.event_title = tk.StringVar()
        self.event_description = tk.StringVar()
        self.event_notes = tk.StringVar()
        
        self.merge_vars = {'branch': {}, 'tag': {}}
        self.events = []
        
        # Add cache variables
        self.cached_branches = []  # Cache all branches
        self.cached_tags = []      # Cache all tags
        self.cached_remote_branches = []  # Cache remote branches
        
        # Add operation control variables
        self.enable_branch_creation = tk.BooleanVar(value=False)
        self.enable_merge = tk.BooleanVar(value=False)
        self.enable_tag_creation = tk.BooleanVar(value=False)
        
        # Initialize control lists
        self.branch_controls = []
        self.merge_controls = []
        self.tag_controls = []
        
        print("Starting UI setup...")
        self.setup_ui()
        print("UI setup completed")
        
        # Check and set Git user information
        self.check_git_config()
        
        # Load all event files
        self.load_all_events()

    def select_repo_path(self):
        """Select repository path"""
        path = filedialog.askdirectory(
            title="Select Git Repository",
            initialdir=os.getcwd()  # Use current directory as initial directory
        )
        if path:
            self.repo_path.set(path)
            self.init_repo()  # Only initialize repository after path selection
            self.log_operation(f"Selected repository path: {path}")
            self.update_status("Repository path selected", success=True)

    def init_repo(self):
        """Initialize or update Git repository"""
        try:
            if not self.repo_path.get():
                self.log_operation("No repository path selected")
                self.update_status("Please select a repository path", success=False)
                return
            
            self.repo = git.Repo(self.repo_path.get())
            print("Git repository initialized successfully")
            
            # Initialize all information to cache
            self.refresh_repo_cache()
            
            # Update all related displays
            self.update_current_branch_labels()
            self.refresh_merge_items()
            self.update_base_items()
            self.log_operation("Repository initialized successfully")
            self.update_status("Repository loaded successfully")
        except Exception as e:
            error_msg = str(e)
            print(f"Error initializing repository: {error_msg}")
            self.log_operation(f"Error initializing repository: {error_msg}")
            self.update_status("Failed to initialize repository", success=False)
            messagebox.showerror("Error", f"Failed to initialize repository: {error_msg}")

    def refresh_repo_cache(self):
        """Refresh repository cache information"""
        try:
            # Get remote repository information
            remote = self.repo.remote()
            remote.fetch()
            self.repo.git.fetch('--tags')
            
            # Update branch cache
            current = self.repo.active_branch.name
            self.cached_branches = [branch.name for branch in self.repo.heads if branch.name != current]
            
            # Update remote branch cache
            self.cached_remote_branches = []
            for ref in remote.refs:
                if ref.name == f"{remote.name}/HEAD":
                    continue
                branch_name = ref.name.split('/', 1)[1]
                if branch_name not in self.cached_branches and branch_name != current:
                    self.cached_remote_branches.append(branch_name)
            
            # Update tag cache
            self.cached_tags = [tag.name for tag in self.repo.tags]
            
            # Update UI display
            self.update_current_branch_labels()
            self.refresh_merge_items()
            self.update_base_items()
            
            self.log_operation("Repository cache refreshed")
            self.update_status("Repository cache refreshed successfully")
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error refreshing repository cache: {error_msg}")
            self.update_status("Failed to refresh repository cache", success=False)

    def create_log_widgets(self):
        """Create log and status text widgets"""
        # Create log text widget
        self.log_text = tk.Text(self.root, height=6, wrap=tk.WORD)
        self.log_text.configure(state='disabled')
        
        # Create status text widget
        self.status_text = tk.Text(self.root, height=3, wrap=tk.WORD)
        self.status_text.configure(state='disabled')

    def update_current_branch_labels(self):
        """Update all display current branch labels"""
        try:
            current = self.repo.active_branch.name
            branch_text = f"{current}"
            
            if hasattr(self, 'current_branch_label'):
                self.current_branch_label.config(text=branch_text)
            
            if hasattr(self, 'tag_branch_label'):
                self.tag_branch_label.config(text=branch_text)
            
        except Exception as e:
            print(f"Error updating branch labels: {str(e)}")

    def refresh_branch_name(self):
        """Manually refresh branch name"""
        try:
            remote = self.repo.remote()
            self.log_operation("Fetching remote branches...")
            remote.fetch()
            self.update_branch_name(force_check=True)
            self.update_current_branch_labels()
            self.log_operation("Refreshed branch name")
            self.update_status("Branch name refreshed successfully")
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error refreshing branch name: {error_msg}")
            self.update_status("Failed to refresh branch name", success=False)

    def refresh_merge_items(self):
        """Refresh merge project list (using cache)"""
        try:
            # Clear existing checkboxes
            for widget in self.merge_inner_frame.winfo_children():
                widget.destroy()
            
            # Get branches
            current = self.repo.active_branch.name
            
            # Use cached branch information
            all_branches = sorted(set(self.cached_branches + self.cached_remote_branches))
            
            # Recreate checkboxes
            row = 0
            if all_branches:
                ttk.Label(self.merge_inner_frame, text="Branches:").grid(
                    row=row, column=0, sticky='w', padx=5, pady=2)
                row += 1
                for branch in all_branches:
                    self.merge_vars['branch'][branch] = tk.BooleanVar()
                    display_name = f"{branch} (remote)" if branch in self.cached_remote_branches else branch
                    ttk.Checkbutton(self.merge_inner_frame, text=display_name, 
                                  variable=self.merge_vars['branch'][branch]).grid(
                        row=row, column=0, sticky='w', padx=20, pady=2)
                    row += 1
            
            if self.cached_tags:
                ttk.Label(self.merge_inner_frame, text="Tags:").grid(
                    row=row, column=0, sticky='w', padx=5, pady=2)
                row += 1
                for tag in sorted(self.cached_tags):
                    self.merge_vars['tag'][tag] = tk.BooleanVar()
                    ttk.Checkbutton(self.merge_inner_frame, text=tag, 
                                  variable=self.merge_vars['tag'][tag]).grid(
                        row=row, column=0, sticky='w', padx=20, pady=2)
                    row += 1
            
            # Update canvas scroll region
            self.merge_inner_frame.update_idletasks()
            self.merge_canvas.configure(scrollregion=self.merge_canvas.bbox('all'))
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error refreshing merge items: {error_msg}")
            self.update_status(f"Failed to refresh merge items: {error_msg}", success=False)
    def refresh_tag_name(self):
        """Refresh tag name"""
        try:
            self.log_operation("Fetching remote tags...")
            self.repo.git.fetch('--tags')
            self.update_tag_name(force_check=True)
            self.update_current_branch_labels()
            self.log_operation("Refreshed tag name")
            self.update_status("Tag name refreshed successfully")
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error refreshing tag name: {error_msg}")
            self.update_status("Failed to refresh tag name", success=False)

    def update_branch_name(self, *args):
        """Update final branch name"""
        try:
            # If the domain is disabled and not the initial call, return
            if not self.enable_branch_creation.get() and args:
                return
            
            prefix = self.branch_prefix.get()
            custom = self.branch_custom_suffix.get()
            date = self.branch_date_suffix.get()
            
            # Build base branch name
            if prefix == 'custom':
                if not custom:
                    self.final_branch_name.set('')
                    return
                base_name = custom
            else:
                base_name = f"{prefix}_{date}"
                if custom:
                    base_name = f"{base_name}_{custom}"
            
            # Get all branches (including remote branches)
            all_branches = [branch.name for branch in self.repo.heads]
            remote_branches = [ref.name.split('/')[-1] for ref in self.repo.remote().refs 
                             if not ref.name.endswith('/HEAD')]
            existing_branches = list(set(all_branches + remote_branches))
            
            # If the name already exists, add a number suffix
            if base_name in existing_branches:
                # Find all similar branch names
                pattern = re.compile(f"^{re.escape(base_name)}(\\.\\d+)?$")
                similar_branches = [b for b in existing_branches if pattern.match(b)]
                
                if similar_branches:
                    # Find the largest number
                    max_number = 0
                    for branch in similar_branches:
                        if branch == base_name:
                            max_number = max(max_number, 0)
                        else:
                            try:
                                suffix = branch.split('.')[-1]
                                if suffix.isdigit():
                                    max_number = max(max_number, int(suffix))
                            except (IndexError, ValueError):
                                continue
                    
                    # Use the next number
                    final_name = f"{base_name}.{max_number + 1}"
                else:
                    final_name = f"{base_name}.1"
            else:
                final_name = base_name
            
            self.final_branch_name.set(final_name)
            
        except Exception as e:
            print(f"Error updating branch name: {str(e)}")
            self.final_branch_name.set('')

    def update_tag_name(self, *args, force_check=False):
        """Update final tag name"""
        try:
            prefix = self.tag_prefix.get()
            custom = self.tag_custom_suffix.get()
            date = self.tag_date_suffix.get()
            
            # Build base tag name
            if prefix == 'custom':
                if not custom:
                    self.final_tag_name.set('')
                return
                base_name = custom
            else:
                base_name = f"{prefix}_{date}"
                if custom:
                    base_name = f"{base_name}_{custom}"
            
            # If it's a forced check, re-fetch remote information
            if force_check:
                self.repo.git.fetch('--tags')
            
            # Get all tags
            existing_tags = [tag.name for tag in self.repo.tags]
            
            # If the name already exists, add a number suffix
            if base_name in existing_tags:
                # Find all similar tag names
                pattern = re.compile(f"^{re.escape(base_name)}(\\.\\d+)?$")
                similar_tags = [t for t in existing_tags if pattern.match(t)]
                
                if similar_tags:
                    # Find the largest number
                    max_number = 0
                    for tag in similar_tags:
                        if tag == base_name:
                            max_number = max(max_number, 0)
                        else:
                            try:
                                suffix = tag.split('.')[-1]
                                if suffix.isdigit():
                                    max_number = max(max_number, int(suffix))
                            except (IndexError, ValueError):
                                continue
                    
                    # Use the next number
                    final_name = f"{base_name}.{max_number + 1}"
                else:
                    final_name = f"{base_name}.1"
            else:
                final_name = base_name
            
            self.final_tag_name.set(final_name)
                
        except Exception as e:
            print(f"Error updating tag name: {str(e)}")
            self.final_tag_name.set('')

    def log_operation(self, message, details=""):
        """Record operation log"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_message = f"[{timestamp}] {message}\n"
            if details:
                log_message += f"Details:\n{details}\n"
            
            # Use log text widget for editing
            self.log_text.configure(state='normal')
            
            # Insert log message into log text widget
            self.log_text.insert(tk.END, log_message)
            
            # Scroll to the bottom
            self.log_text.see(tk.END)
            
            # Disable log text widget editing
            self.log_text.configure(state='disabled')
            
        except Exception as e:
            print(f"Error logging operation: {str(e)}")

    def update_status(self, message, success=True):
        """Update status bar"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            status_message = f"[{timestamp}] {'✓' if success else '✗'} Step {self.operation_count + 1}\n"
            status_message += f"{message}\n"
            status_message += "-" * 30 + "\n"
            
            # Enable status text widget for editing
            self.status_text.configure(state='normal')
            
            # Insert status message into status text widget
            self.status_text.insert(tk.END, status_message)
            
            # Scroll to the bottom
            self.status_text.see(tk.END)
            
            # Disable status text widget editing
            self.status_text.configure(state='disabled')
            
            # Increase operation count
            self.operation_count += 1
            
        except Exception as e:
            print(f"Error updating status: {str(e)}")
    def setup_ui(self):
        """Set up user interface"""
        # 1. Set main window
        self.root.resizable(True, True)
        self.root.minsize(800, 600)
        
        # 2. Create main layout (left and right panes)
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # 3. First create right panel (contains log and status text widgets)
        right_panel = self.create_right_panel(main_paned)
        
        # 4. Create left panel
        left_panel = self.create_left_panel(main_paned)
        self.create_events_path_section(left_panel)
        
        # 5. Add left and right panels to the main split window
        main_paned.add(left_panel)
        main_paned.add(right_panel)
        
        # 6. Set split position (left 70%, right 30%)
        self.root.update()
        main_paned.sashpos(0, int(self.root.winfo_width() * 0.7))

    def create_left_panel(self, parent):
        """Create left panel"""
        # 1. Create left container
        left_container = ttk.Frame(parent)
        
        # 2. Create path selection area (new)
        self.create_path_section(left_container)
        
        # 3. Create canvas and scrollbar
        canvas = tk.Canvas(left_container)
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        
        # 4. Create scrollable frame
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # 5. Create window on canvas
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 6. Create event information area
        self.create_event_info_section(scrollable_frame)
        
        # 7. Create Git operations area
        self.create_git_operations_section(scrollable_frame)
        
        # 8. Create toolbar (remove path selection part)
        self.create_toolbar(scrollable_frame)
        
        # 9. Layout canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 10. Bind mouse wheel
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        return left_container

    def create_path_section(self, parent):
        """Create path selection area"""
        path_frame = ttk.LabelFrame(parent, text="Repository Path")
        path_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create inner frame
        inner_frame = ttk.Frame(path_frame)
        inner_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Path entry
        path_entry = ttk.Entry(inner_frame, textvariable=self.repo_path, state='readonly')
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Refresh button
        refresh_btn = ttk.Button(inner_frame, text="↻", width=3, command=self.refresh_repo_cache)
        refresh_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Browse button
        select_path_btn = ttk.Button(inner_frame, text="Browse", command=self.select_repo_path)
        select_path_btn.pack(side=tk.RIGHT)

    def create_toolbar(self, parent):
        """Create toolbar"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        
        # Save and history buttons
        save_event_btn = ttk.Button(toolbar, text="Save Event", command=self.save_current_event)
        save_event_btn.pack(side=tk.RIGHT, padx=5)
        
        history_btn = ttk.Button(toolbar, text="View History", command=self.show_event_history)
        history_btn.pack(side=tk.RIGHT, padx=5)

    def create_right_panel(self, parent):
        """Create right panel"""
        right_frame = ttk.Frame(parent)
        
        # 1. Create status area
        status_frame = ttk.LabelFrame(right_frame, text="Status")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create status text widget container
        status_container = ttk.Frame(status_frame)
        status_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create status text widget - increase height value
        self.status_text = tk.Text(status_container, height=8, wrap=tk.WORD)  # Changed from height=3 to 8
        self.status_text.configure(state='disabled')
        
        # Create status scrollbar
        status_scrollbar = ttk.Scrollbar(status_container, orient="vertical", 
                                       command=self.status_text.yview)
        
        # Use grid layout manager
        self.status_text.grid(row=0, column=0, sticky='nsew', padx=(0, 2))  # Added right padding
        status_scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Configure text widget scrolling
        self.status_text.configure(yscrollcommand=status_scrollbar.set)
        
        # Configure grid weights
        status_container.grid_columnconfigure(0, weight=1)
        status_container.grid_rowconfigure(0, weight=1)
        
        # 2. Create log area
        log_frame = ttk.LabelFrame(right_frame, text="Operation Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create log text widget container
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create log text widget
        self.log_text = tk.Text(log_container, height=15, wrap=tk.WORD)  # Changed height
        self.log_text.configure(state='disabled')
        
        # Create log scrollbar
        log_scrollbar = ttk.Scrollbar(log_container, orient="vertical", 
                                    command=self.log_text.yview)
        
        # Use grid layout manager
        self.log_text.grid(row=0, column=0, sticky='nsew', padx=(0, 2))  # Added right padding
        log_scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Configure text widget scrolling
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # Configure grid weights
        log_container.grid_columnconfigure(0, weight=1)
        log_container.grid_rowconfigure(0, weight=1)
        
        # Configure right panel weights, let Operation Log area occupy more space
        right_frame.pack_configure(fill=tk.BOTH, expand=True)
        
        return right_frame

    def create_event_info_section(self, parent):
        """Create event information area"""
        frame = ttk.LabelFrame(parent, text="Event Information")
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Event title
        ttk.Label(frame, text="Event Title:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.event_title).grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        
        # Event description
        ttk.Label(frame, text="Description:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.event_description).grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        
        # Event notes
        ttk.Label(frame, text="Notes:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.event_notes).grid(row=2, column=1, sticky='ew', padx=5, pady=5)
        
        frame.grid_columnconfigure(1, weight=1)

    def create_git_operations_section(self, parent):
        """Create Git operations area"""
        frame = ttk.LabelFrame(parent, text="Git Operations")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 1. Branch Creation
        self.create_branch_section(frame)
        
        # 2. Merge Configuration
        self.create_merge_section(frame)
        
        # 3. Tag Creation
        self.create_tag_section(frame)
        
        # 4. Execute Operations
        self.create_execute_section(frame)
        
        # 5. Push Section
        self.create_push_section(frame)
        
        # All domains created, update state
        self.update_sections_state()

    def update_base_items(self, *args):
        """Update base item list"""
        try:
            search_text = self.base_search_var.get().lower()
            self.base_items_listbox.delete(0, tk.END)
            
            if self.base_type.get() == "branch":
                local_branches = self.cached_branches
                remote_branches = [f"{branch} (remote)" for branch in self.cached_remote_branches]
                items = sorted(set(local_branches + remote_branches))
            else:
                items = sorted(self.cached_tags)
            
            for item in items:
                if search_text in item.lower():
                    self.base_items_listbox.insert(tk.END, item)
                
            # If there's only one option, automatically select it
            if self.base_items_listbox.size() == 1:
                self.base_items_listbox.select_set(0)
                self.base_items_listbox.event_generate('<<ListboxSelect>>')
                
        except Exception as e:
            self.log_operation(f"Error updating base items: {str(e)}")
            self.update_status("Failed to update base items", success=False)

    def create_branch(self):
        """Create new branch"""
        try:
            # Get new branch name
            new_branch_name = self.final_branch_name.get()
            if not new_branch_name:
                messagebox.showerror("Error", "Branch name cannot be empty")
                return
            
            # Get base item (from Listbox, get selected item)
            selections = self.base_items_listbox.curselection()
            if not selections:
                # If no base item is selected, but there's a generated branch name, use the current branch as the base
                current_branch = self.repo.active_branch.name
                base_item = current_branch
                self.log_operation(f"No base item selected, using current branch: {current_branch}")
            else:
                base_item = self.base_items_listbox.get(selections[0])
                # If it's a remote branch, remove "(remote)" suffix
                if "(remote)" in base_item:
                    base_item = base_item.split(" (remote)")[0]
            
            # Save base branch name for later use
            self.current_base_branch = base_item
            
            # Record operation
            self.log_operation(f"Creating new branch: {new_branch_name}", 
                             f"Base {self.base_type.get()}: {base_item}")
            
            # Check out base item
            if self.base_type.get() == "branch":
                self.repo.git.checkout(base_item)
            else:
                self.repo.git.checkout(base_item)
            
            # Create new branch
            self.repo.git.checkout('-b', new_branch_name)
            
            # Update status
            self.update_status(f"Created new branch: {new_branch_name}")
            
            # Update base item list
            self.update_base_items()
            
            # Update current branch display
            self.update_current_branch_labels()
            
            # Show success message
            messagebox.showinfo("Success", f"Branch '{new_branch_name}' created successfully")
            
            # Update Push area display after branch creation is successful
            self.update_push_labels()
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error creating branch: {error_msg}")
            self.update_status(f"Failed to create branch: {error_msg}", success=False)
            messagebox.showerror("Error", f"Failed to create branch: {error_msg}")

    def merge_branches(self):
        """Merge selected branches and tags"""
        try:
            # Get selected branches and tags
            selected_branches = [branch for branch, var in self.merge_vars['branch'].items() 
                               if var.get()]
            selected_tags = [tag for tag, var in self.merge_vars['tag'].items() 
                           if var.get()]
            
            if not selected_branches and not selected_tags:
                messagebox.showwarning("Warning", "Please select at least one branch or tag")
                return
            
            # Record operation
            self.log_operation("Starting merge operation", 
                             f"Selected branches: {selected_branches}\n"
                             f"Selected tags: {selected_tags}")
            
            merged_info = []  # Store merge information
            
            # Merge branches
            for branch in selected_branches:
                try:
                    self.log_operation(f"Merging branch: {branch}")
                    
                    # Get the latest commit information of the branch
                    if '(remote)' in branch:
                        branch_name = branch.split(' (remote)')[0]
                        commit = self.repo.remote().refs[branch_name].commit
                    else:
                        commit = self.repo.heads[branch].commit
                    
                    # Record branch information
                    branch_info = {
                        'name': branch,
                        'commit_id': commit.hexsha[:8],  # Only take the first 8 digits
                        'commit_message': commit.message.strip(),
                        'commit_author': commit.author.name,
                        'commit_date': datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # Execute merge
                    self.repo.git.merge(branch, '--no-ff')
                    merged_info.append(branch_info)
                    
                    self.update_status(f"Merged branch: {branch}")
                    
                except Exception as e:
                    error_msg = str(e)
                    self.log_operation(f"Error merging branch {branch}: {error_msg}")
                    self.update_status(f"Failed to merge branch {branch}", success=False)
                    if messagebox.askyesno("Error", 
                                         f"Failed to merge branch {branch}. Continue with remaining items?"):
                        self.repo.git.merge('--abort')
                        continue
                    else:
                        self.repo.git.merge('--abort')
                        return
            
            # Merge tags
            for tag in selected_tags:
                try:
                    self.log_operation(f"Merging tag: {tag}")
                    
                    # Get commit information of the tag
                    tag_obj = self.repo.tags[tag]
                    commit = tag_obj.commit
                    
                    # Record tag information
                    tag_info = {
                        'name': f"tag:{tag}",
                        'commit_id': commit.hexsha[:8],
                        'commit_message': commit.message.strip(),
                        'commit_author': commit.author.name,
                        'commit_date': datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # Execute merge
                    self.repo.git.merge(tag, '--no-ff')
                    merged_info.append(tag_info)
                    
                    self.update_status(f"Merged tag: {tag}")
                    
                except Exception as e:
                    error_msg = str(e)
                    self.log_operation(f"Error merging tag {tag}: {error_msg}")
                    self.update_status(f"Failed to merge tag {tag}", success=False)
                    if messagebox.askyesno("Error", 
                                         f"Failed to merge tag {tag}. Continue with remaining items?"):
                        self.repo.git.merge('--abort')
                        continue
                    else:
                        self.repo.git.merge('--abort')
                        return
            
            # Refresh merge project list
            self.refresh_merge_items()
            
            # Return merge information
            return merged_info
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error during merge operation: {error_msg}")
            self.update_status("Merge operation failed", success=False)
            messagebox.showerror("Error", f"Merge operation failed: {error_msg}")
            return None

    def create_tag(self):
        """Create new tag"""
        try:
            # Get new tag name
            new_tag_name = self.final_tag_name.get()
            if not new_tag_name:
                messagebox.showerror("Error", "Tag name cannot be empty")
                return
            
            # Record operation
            self.log_operation(f"Creating new tag: {new_tag_name}")
            
            # Create new tag
            self.repo.create_tag(new_tag_name)
            
            # Push tag to remote
            self.repo.remote().push(new_tag_name)
            
            # Update status
            self.update_status(f"Created new tag: {new_tag_name}")
            
            # Refresh merge project list
            self.refresh_merge_items()
            
            # Show success message
            messagebox.showinfo("Success", f"Tag '{new_tag_name}' created successfully")
            
            # Update Push area display
            self.update_push_labels()
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error creating tag: {error_msg}")
            self.update_status(f"Failed to create tag: {error_msg}", success=False)
            messagebox.showerror("Error", f"Failed to create tag: {error_msg}")

    def run(self):
        """Run the application"""
        self.root.mainloop()

    def save_current_event(self):
        """Save current event"""
        try:
            if not self.event_title.get():
                messagebox.showwarning("Warning", "Please enter event title")
                return
            
            event = GitEvent()
            event.title = self.event_title.get()
            event.date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            event.description = self.event_description.get()
            event.created_branch = self.final_branch_name.get()
            event.created_tag = self.final_tag_name.get()
            event.notes = self.event_notes.get()
            
            # Use the saved base branch name
            event.base_branch = getattr(self, 'current_base_branch', self.repo.active_branch.name)
            
            # Use merge information saved during operation execution
            if hasattr(self, 'last_merged_info') and self.last_merged_info:
                event.merged_branches_info = self.last_merged_info
                event.merged_branches = [info['name'] for info in self.last_merged_info]
            
            # Create date directory
            date_dir = os.path.join(self.events_path.get(), 
                                   datetime.now().strftime('%Y-%m-%d'))
            os.makedirs(date_dir, exist_ok=True)
            
            # Create file name (using timestamp and branch name)
            timestamp = datetime.now().strftime('%H%M%S')
            branch_name = self.repo.active_branch.name.replace('/', '_')
            filename = f"{timestamp}_{branch_name}.json"
            
            # Full file path
            file_path = os.path.join(date_dir, filename)
            
            # Save event
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(event.__dict__, f, ensure_ascii=False, indent=2)
            
            # Update event cache
            self.load_all_events()
            
            # Show success message
            messagebox.showinfo("Success", "Event saved successfully")
            
            # Clear input fields
            self.event_title.set("")
            self.event_description.set("")
            self.event_notes.set("")
            self.last_merged_info = None
            self.current_base_branch = None  # Clear base branch record
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error saving event: {error_msg}")
            self.update_status("Failed to save event", success=False)
            messagebox.showerror("Error", f"Failed to save event: {error_msg}")

    def load_all_events(self):
        """Load all event files"""
        try:
            self.events_by_date = {}
            self.events_by_branch = {}
            
            # Iterate over event directories
            for root, dirs, files in os.walk(self.events_path.get()):
                for file in files:
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            event_data = json.load(f)
                            
                            # Create event object
                            event = GitEvent()
                            for key, value in event_data.items():
                                setattr(event, key, value)
                            
                            # Organize by date
                            date = event.date.split()[0]
                            if date not in self.events_by_date:
                                self.events_by_date[date] = []
                            self.events_by_date[date].append(event)
                            
                            # Organize by branch
                            branch = event.base_branch
                            if branch not in self.events_by_branch:
                                self.events_by_branch[branch] = []
                            self.events_by_branch[branch].append(event)
            
        except Exception as e:
            self.log_operation(f"Error loading events: {str(e)}")
            self.update_status("Failed to load events", success=False)

    def show_event_history(self):
        """Show event history"""
        history_window = tk.Toplevel(self.root)
        history_window.title("Event History")
        history_window.geometry("1000x600")
        
        # Create left and right split panels
        paned = ttk.PanedWindow(history_window, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left filter panel
        filter_frame = ttk.Frame(paned)
        paned.add(filter_frame)
        
        # Create filter options
        ttk.Label(filter_frame, text="View:").pack(pady=5)
        view_var = tk.StringVar(value="date")
        ttk.Radiobutton(filter_frame, text="By Date", variable=view_var, 
                        value="date", command=lambda: update_tree("date")).pack()
        ttk.Radiobutton(filter_frame, text="By Branch", variable=view_var, 
                        value="branch", command=lambda: update_tree("branch")).pack()
        
        # Search box
        ttk.Label(filter_frame, text="Search:").pack(pady=(10,0))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=search_var)
        search_entry.pack(pady=5)
        
        # Right event display area
        right_frame = ttk.Frame(paned)
        paned.add(right_frame)
        
        # Create tree view
        tree = ttk.Treeview(right_frame, columns=(
            'Time', 'Title', 'Branch', 'Tag', 'Description'
        ), show='headings')
        
        tree.heading('Time', text='Time')
        tree.heading('Title', text='Title')
        tree.heading('Branch', text='Created Branch')
        tree.heading('Tag', text='Created Tag')
        tree.heading('Description', text='Description')
        
        # Set column widths - increase Time column width to accommodate full date
        tree.column('Time', width=180)  # Increased from 150
        tree.column('Title', width=150)
        tree.column('Branch', width=150)
        tree.column('Tag', width=100)
        tree.column('Description', width=200)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Layout
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def update_tree(view_type):
            """Update tree view"""
            tree.delete(*tree.get_children())
            search_text = search_var.get().lower()
            
            if view_type == "date":
                data = self.events_by_date
            else:
                data = self.events_by_branch
            
            for key in sorted(data.keys(), reverse=True):
                parent = tree.insert('', 'end', text=key, open=True)
                for event in sorted(data[key], key=lambda x: x.date, reverse=True):
                    if (search_text in event.title.lower() or 
                        search_text in event.description.lower() or
                        search_text in event.created_branch.lower()):
                        tree.insert(parent, 'end', values=(
                            event.date,  # Show full date and time instead of just time
                            event.title,
                            event.created_branch,
                            event.created_tag,
                            event.description
                        ))
        
        def on_search(*args):
            """Search event processing"""
            update_tree(view_var.get())
        
        # Bind search event
        search_var.trace_add("write", on_search)
        
        # Show event details
        def show_details(event):
            """Show event details"""
            item = tree.selection()[0]
            if tree.parent(item):  # Ensure the selected item is an event, not a group
                values = tree.item(item)['values']
                if values:
                    details_window = tk.Toplevel(history_window)
                    details_window.title("Event Details")
                    details_window.geometry("600x400")
                    
                    text = tk.Text(details_window, wrap=tk.WORD, padx=10, pady=10)
                    text.pack(fill=tk.BOTH, expand=True)
                    
                    # Find the complete event information
                    event_date = values[0]  # Now using the full date-time string
                    event_data = None
                    
                    # Search through all events to find the matching one
                    for events in self.events_by_date.values():
                        for e in events:
                            if e.date == event_date and e.title == values[1]:
                                event_data = e
                                break
                        if event_data:
                            break
                    
                    if event_data:
                        details = f"Title: {event_data.title}\n"
                        details += f"Date: {event_data.date}\n"
                        details += f"Description: {event_data.description}\n"
                        details += f"Base Branch: {event_data.base_branch}\n"
                        if event_data.created_branch:
                            details += f"Created Branch: {event_data.created_branch}\n"
                        if event_data.created_tag:
                            details += f"Created Tag: {event_data.created_tag}\n"
                        if hasattr(event_data, 'merged_branches_info') and event_data.merged_branches_info:
                            details += "\nMerged branch information:\n"
                            for branch_info in event_data.merged_branches_info:
                                details += f"\nBranch: {branch_info['name']}\n"
                                details += f"Commit ID: {branch_info['commit_id']}\n"
                                details += f"Commit message: {branch_info['commit_message']}\n"
                                details += f"Commit author: {branch_info['commit_author']}\n"
                                details += f"Commit date: {branch_info['commit_date']}\n"
                        if event_data.notes:
                            details += f"\nNotes: {event_data.notes}\n"
                        
                        text.insert('1.0', details)
                        text.configure(state='disabled')
        
        # Bind double-click event
        tree.bind('<Double-1>', show_details)
        
        # Initial display
        update_tree("date")

    def setup_toolbar(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        history_btn = ttk.Button(toolbar, text="View History", command=self.show_event_history)
        history_btn.pack(side=tk.RIGHT, padx=5)

    def on_base_item_selected(self, event):
        """Base item selection event processing"""
        try:
            if not self.enable_branch_creation.get():
                return
            
            if not self.base_items_listbox.curselection():
                return
            
            selected = self.base_items_listbox.get(self.base_items_listbox.curselection())
            if selected:
                # If it's a remote branch, remove "(remote)" suffix
                branch_name = selected.split(' (remote)')[0]
                self.branch_prefix.set(branch_name)
                self.update_branch_name()
                
        except Exception as e:
            self.log_operation(f"Error in base item selection: {str(e)}")
            self.update_status("Failed to handle base item selection", success=False)

    def create_branch_section(self, parent):
        """Create branch operations area"""
        branch_frame = ttk.LabelFrame(parent, text="1. Create Branch")
        branch_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add enable checkbox
        enable_frame = ttk.Frame(branch_frame)
        enable_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Checkbutton(enable_frame, text="Enable Branch Creation", 
                        variable=self.enable_branch_creation,
                        command=self.update_sections_state).pack(side=tk.LEFT)
        
        # Current branch information
        current_branch_frame = ttk.Frame(branch_frame)
        current_branch_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(current_branch_frame, text="Current Branch:").pack(side=tk.LEFT, padx=(0,5))
        self.current_branch_label = ttk.Label(current_branch_frame, text="", 
                                            font=('TkDefaultFont', 9, 'bold'))
        self.current_branch_label.pack(side=tk.LEFT)
        
        # Base type selection
        base_type_frame = ttk.Frame(branch_frame)
        base_type_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(base_type_frame, text="Base Type:").pack(side=tk.LEFT)
        branch_radio = ttk.Radiobutton(base_type_frame, text="Branch", value="branch", 
                                      variable=self.base_type, command=self.update_base_items)
        branch_radio.pack(side=tk.LEFT, padx=5)
        tag_radio = ttk.Radiobutton(base_type_frame, text="Tag", value="tag", 
                                   variable=self.base_type, command=self.update_base_items)
        tag_radio.pack(side=tk.LEFT)
        
        # Base item selection - add search functionality
        base_items_frame = ttk.Frame(branch_frame)
        base_items_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(base_items_frame, text="Base Item:").pack(side=tk.LEFT)
        
        # Add search box
        self.base_search_var = tk.StringVar()
        search_entry = ttk.Entry(base_items_frame, textvariable=self.base_search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Create listbox
        listbox_frame = ttk.Frame(base_items_frame)
        listbox_frame.pack(fill=tk.X, expand=True, padx=5)
        
        self.base_items_listbox = tk.Listbox(listbox_frame, height=5, selectmode=tk.SINGLE)
        self.base_items_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Add scrollbar
        base_scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", 
                                     command=self.base_items_listbox.yview)
        base_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.base_items_listbox.configure(yscrollcommand=base_scrollbar.set)
        
        # Bind search event
        self.base_search_var.trace_add("write", self.update_base_items)
        
        # Bind selection event
        self.base_items_listbox.bind('<<ListboxSelect>>', self.on_base_item_selected)
        
        # Branch prefix selection
        prefix_frame = ttk.Frame(branch_frame)
        prefix_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(prefix_frame, text="Prefix:").pack(side=tk.LEFT)
        prefix_combo = ttk.Combobox(prefix_frame, textvariable=self.branch_prefix, 
                                   values=['feature', 'bugfix', 'hotfix', 'release', 'custom'])
        prefix_combo.pack(side=tk.LEFT, padx=5)
        prefix_combo.bind('<<ComboboxSelected>>', self.update_branch_name)
        
        # Custom suffix
        custom_suffix_frame = ttk.Frame(branch_frame)
        custom_suffix_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(custom_suffix_frame, text="Custom Suffix:").pack(side=tk.LEFT)
        custom_entry = ttk.Entry(custom_suffix_frame, textvariable=self.branch_custom_suffix)
        custom_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        custom_entry.bind('<KeyRelease>', self.update_branch_name)
        
        # Date suffix
        date_suffix_frame = ttk.Frame(branch_frame)
        date_suffix_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(date_suffix_frame, text="Date Suffix:").pack(side=tk.LEFT)
        date_entry = ttk.Entry(date_suffix_frame, textvariable=self.branch_date_suffix)
        date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        date_entry.bind('<KeyRelease>', self.update_branch_name)
        
        # Branch name preview
        preview_frame = ttk.Frame(branch_frame)
        preview_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(preview_frame, text="Final Branch Name:").pack(side=tk.LEFT)
        ttk.Entry(preview_frame, textvariable=self.final_branch_name, 
                  state='readonly').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Refresh button
        ttk.Button(preview_frame, text="↻", width=3, 
                   command=self.refresh_branch_name).pack(side=tk.RIGHT)

    def create_merge_section(self, parent):
        """Create merge operations area"""
        merge_frame = ttk.LabelFrame(parent, text="2. Merge Branches/Tags")
        merge_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add enable checkbox
        enable_frame = ttk.Frame(merge_frame)
        enable_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Checkbutton(enable_frame, text="Enable Merge Operation", 
                        variable=self.enable_merge,
                        command=self.update_sections_state).pack(side=tk.LEFT)
        
        # Add search box
        search_frame = ttk.Frame(merge_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.merge_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.merge_search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Create scrollable frame
        scroll_frame = ttk.Frame(merge_frame)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create canvas and scrollbar
        self.merge_canvas = tk.Canvas(scroll_frame, height=150)
        scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", 
                                 command=self.merge_canvas.yview)
        
        # Create internal frame
        self.merge_inner_frame = ttk.Frame(self.merge_canvas)
        
        # Configure canvas
        self.merge_canvas.configure(yscrollcommand=scrollbar.set)
        self.merge_canvas_window = self.merge_canvas.create_window(
            (0, 0), window=self.merge_inner_frame, anchor="nw"
        )
        
        # Layout canvas and scrollbar
        self.merge_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create dictionaries to store Checkbutton for branches and tags
        self.branch_checkbuttons = {}
        self.tag_checkbuttons = {}
        
        def update_merge_items():
            """Update display of merge items"""
            search_text = self.merge_search_var.get().lower()
            
            # Clear internal frame
            for widget in self.merge_inner_frame.winfo_children():
                widget.destroy()
            
            # Create branch area
            branch_frame = ttk.LabelFrame(self.merge_inner_frame, text="Branches")
            branch_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
            
            # Display branches
            all_branches = sorted(set(self.cached_branches + 
                                    [f"{b} (remote)" for b in self.cached_remote_branches]))
            
            for branch in all_branches:
                if search_text in branch.lower():
                    if branch not in self.merge_vars['branch']:
                        self.merge_vars['branch'][branch] = tk.BooleanVar()
                    checkbox = ttk.Checkbutton(
                        branch_frame,
                        text=branch,
                        variable=self.merge_vars['branch'][branch]
                    )
                    checkbox.pack(anchor='w', padx=20, pady=2)
                    self.branch_checkbuttons[branch] = checkbox
            
            # Create tag area
            if self.cached_tags:
                tag_frame = ttk.LabelFrame(self.merge_inner_frame, text="Tags")
                tag_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
                
                for tag in sorted(self.cached_tags):
                    if search_text in tag.lower():
                        if tag not in self.merge_vars['tag']:
                            self.merge_vars['tag'][tag] = tk.BooleanVar()
                        checkbox = ttk.Checkbutton(
                            tag_frame,
                            text=tag,
                            variable=self.merge_vars['tag'][tag]
                        )
                        checkbox.pack(anchor='w', padx=20, pady=2)
                        self.tag_checkbuttons[tag] = checkbox
            
            # Update canvas scroll region
            self.merge_inner_frame.update_idletasks()
            self.merge_canvas.configure(scrollregion=self.merge_canvas.bbox("all"))
        
        # Bind event to update scroll region
        def on_frame_configure(event):
            self.merge_canvas.configure(scrollregion=self.merge_canvas.bbox("all"))
        
        def on_canvas_configure(event):
            width = event.width - 4
            self.merge_canvas.itemconfig(self.merge_canvas_window, width=width)
        
        self.merge_inner_frame.bind("<Configure>", on_frame_configure)
        self.merge_canvas.bind("<Configure>", on_canvas_configure)
        
        # Bind search event
        self.merge_search_var.trace_add("write", lambda *args: update_merge_items())
        
        # Bind mouse wheel event
        def on_mousewheel(event):
            self.merge_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        self.merge_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Initial display all items
        update_merge_items()

    def create_tag_section(self, parent):
        """Create tag operations area"""
        tag_frame = ttk.LabelFrame(parent, text="3. Create Tag")
        tag_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add enable checkbox
        enable_frame = ttk.Frame(tag_frame)
        enable_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Checkbutton(enable_frame, text="Enable Tag Creation", 
                        variable=self.enable_tag_creation,
                        command=self.update_sections_state).pack(side=tk.LEFT)
        
        # Tag prefix
        prefix_frame = ttk.Frame(tag_frame)
        prefix_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(prefix_frame, text="Tag Prefix:").pack(side=tk.LEFT)
        prefix_entry = ttk.Entry(prefix_frame, textvariable=self.tag_prefix)
        prefix_entry.pack(fill=tk.X, expand=True, padx=5)
        self.tag_controls.append(prefix_entry)
        
        # Custom suffix
        custom_frame = ttk.Frame(tag_frame)
        custom_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(custom_frame, text="Custom Suffix:").pack(side=tk.LEFT)
        custom_entry = ttk.Entry(custom_frame, textvariable=self.tag_custom_suffix)
        custom_entry.pack(fill=tk.X, expand=True, padx=5)
        self.tag_controls.append(custom_entry)
        
        # Date selection
        date_frame = ttk.Frame(tag_frame)
        date_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(date_frame, text="Date:").pack(side=tk.LEFT)
        date_entry = ttk.Entry(date_frame, textvariable=self.tag_date_suffix)
        date_entry.pack(fill=tk.X, expand=True, padx=5)
        self.tag_controls.append(date_entry)
        
        # Final tag name
        final_frame = ttk.Frame(tag_frame)
        final_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(final_frame, text="Final Name:").pack(side=tk.LEFT)
        final_entry = ttk.Entry(final_frame, textvariable=self.final_tag_name, 
                               state='readonly')
        final_entry.pack(fill=tk.X, expand=True, padx=5)
        
        # Add event bindings
        self.tag_prefix.trace_add("write", self.update_tag_name)
        self.tag_custom_suffix.trace_add("write", self.update_tag_name)
        self.tag_date_suffix.trace_add("write", self.update_tag_name)

    def create_execute_section(self, parent):
        """Create unified execution area"""
        execute_frame = ttk.LabelFrame(parent, text="Execute Operations")
        execute_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create execute button
        execute_btn = ttk.Button(execute_frame, text="Execute Selected Operations", 
                                command=self.execute_operations)
        execute_btn.pack(fill=tk.X, padx=5, pady=5)

    def update_sections_state(self):
        """Update state of all domains"""
        # Update branch creation area
        state = 'normal' if self.enable_branch_creation.get() else 'disabled'
        for widget in self.branch_controls:
            if isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Button, ttk.Radiobutton)):
                widget.configure(state=state)
        
        # Update merge area
        state = 'normal' if self.enable_merge.get() else 'disabled'
        for widget in self.merge_controls:
            if isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Button, ttk.Checkbutton)):
                widget.configure(state=state)
        
        # Update tag creation area
        state = 'normal' if self.enable_tag_creation.get() else 'disabled'
        for widget in self.tag_controls:
            if isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Button)):
                widget.configure(state=state)

    def execute_operations(self):
        """Execute all selected operations"""
        try:
            operations_executed = []
            any_operation_enabled = False
            self.last_merged_info = None  # Add class attribute to store the latest merge information
            
            # 1. Create branch
            if self.enable_branch_creation.get():
                any_operation_enabled = True
                branch_name = self.final_branch_name.get()
                if branch_name:
                    self.create_branch()
                    operations_executed.append(f"Created branch '{branch_name}'")
            
            # 2. Execute merge
            if self.enable_merge.get():
                any_operation_enabled = True
                self.last_merged_info = self.merge_branches()  # Save merge information
                if self.last_merged_info:
                    operations_executed.append(f"Merged {len(self.last_merged_info)} items")
            
            # 3. Create tag
            if self.enable_tag_creation.get():
                any_operation_enabled = True
                tag_name = self.final_tag_name.get()
                if tag_name:
                    self.create_tag()
                    operations_executed.append(f"Created tag '{tag_name}'")
            
            # Check if any operation is enabled
            if not any_operation_enabled:
                messagebox.showwarning("Warning", "No operations were selected")
                return
            
            # Show execution result
            if operations_executed:
                success_message = "\n".join(operations_executed)
                self.log_operation("Executed operations:\n" + success_message)
                self.update_status("All selected operations completed successfully", success=True)
                messagebox.showinfo("Success", "Operations completed successfully")
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error executing operations: {error_msg}")
            self.update_status("Failed to execute operations", success=False)
            messagebox.showerror("Error", f"Failed to execute operations: {error_msg}")

    def create_push_section(self, parent):
        """Create Push operations area"""
        push_frame = ttk.LabelFrame(parent, text="4. Push to Remote")
        push_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create checkbox variables
        self.push_branch_var = tk.BooleanVar()
        self.push_tag_var = tk.BooleanVar()
        
        # Display current branch and tag
        current_info_frame = ttk.Frame(push_frame)
        current_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Branch information
        branch_frame = ttk.Frame(current_info_frame)
        branch_frame.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(branch_frame, text="Current Branch:", 
                        variable=self.push_branch_var).pack(side=tk.LEFT)
        self.push_branch_label = ttk.Label(branch_frame, text="", font=('TkDefaultFont', 9, 'bold'))
        self.push_branch_label.pack(side=tk.LEFT, padx=5)
        
        # Tag information
        tag_frame = ttk.Frame(current_info_frame)
        tag_frame.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(tag_frame, text="Current Tag:", 
                        variable=self.push_tag_var).pack(side=tk.LEFT)
        self.push_tag_label = ttk.Label(tag_frame, text="", font=('TkDefaultFont', 9, 'bold'))
        self.push_tag_label.pack(side=tk.LEFT, padx=5)
        
        # Push button
        ttk.Button(push_frame, text="Push Selected to Remote", 
                   command=self.push_to_remote).pack(fill=tk.X, padx=5, pady=5)

    def update_push_labels(self):
        """Update Push area labels"""
        try:
            # Update branch label - use the actual current branch name
            current_branch = self.repo.active_branch.name
            self.push_branch_label.config(text=current_branch)
            self.push_branch_var.set(True)
            
            # Update tag label
            tag_name = self.final_tag_name.get()
            if tag_name:
                self.push_tag_label.config(text=tag_name)
                self.push_tag_var.set(True)
            else:
                self.push_tag_label.config(text="No tag created")
                self.push_tag_var.set(False)
                
        except Exception as e:
            self.log_operation(f"Error updating push labels: {str(e)}")
            self.update_status("Failed to update push labels", success=False)

    def push_to_remote(self):
        """Push selected branches and tags to remote"""
        try:
            remote = self.repo.remote()
            pushed_items = []
            
            # Push branch
            if self.push_branch_var.get():
                current_branch = self.repo.active_branch.name
                try:
                    # Use --set-upstream to push the current branch
                    self.repo.git.push('--set-upstream', remote.name, current_branch)
                    pushed_items.append(f"branch '{current_branch}'")
                    self.log_operation(f"Pushed branch {current_branch} to remote with upstream")
                except Exception as branch_error:
                    self.log_operation(f"Error pushing branch: {str(branch_error)}")
                    messagebox.showerror("Branch Push Error", f"Failed to push branch: {str(branch_error)}")
            
            # Push tag
            if self.push_tag_var.get():
                tag_name = self.final_tag_name.get()
                if tag_name:
                    try:
                        remote.push(tag_name)
                        pushed_items.append(f"tag '{tag_name}'")
                        self.log_operation(f"Pushed tag {tag_name} to remote")
                    except Exception as tag_error:
                        self.log_operation(f"Error pushing tag: {str(tag_error)}")
                        messagebox.showerror("Tag Push Error", f"Failed to push tag: {str(tag_error)}")
            
            if pushed_items:
                items_str = " and ".join(pushed_items)
                self.update_status(f"Successfully pushed {items_str} to remote", success=True)
                messagebox.showinfo("Success", f"Successfully pushed {items_str} to remote")
                
                # Refresh repository cache after push is successful
                self.refresh_repo_cache()
            else:
                messagebox.showwarning("Warning", "No items selected for push")
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error pushing to remote: {error_msg}")
            self.update_status("Failed to push to remote", success=False)
            messagebox.showerror("Error", f"Failed to push to remote: {error_msg}")

    def check_git_config(self):
        """Check and set Git user information"""
        try:
            # Use git.Git() instead of self.repo.git
            git_cmd = git.Git()
            
            # Check if user information is configured
            try:
                user_name = git_cmd.config('--get', 'user.name')
                user_email = git_cmd.config('--get', 'user.email')
            except git.exc.GitCommandError:
                user_name = ''
                user_email = ''
            
            # If not configured, show configuration dialog
            if not user_name or not user_email:
                self.configure_git_user()
            
        except Exception as e:
            self.log_operation(f"Error checking git configuration: {str(e)}")
            self.update_status("Failed to check git configuration", success=False)

    def configure_git_user(self):
        """Configure Git user information dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Configure Git User")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # User name
        name_frame = ttk.Frame(dialog)
        name_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(name_frame, text="User Name:").pack(side=tk.LEFT)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=name_var)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Email
        email_frame = ttk.Frame(dialog)
        email_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(email_frame, text="User Email:").pack(side=tk.LEFT)
        email_var = tk.StringVar()
        email_entry = ttk.Entry(email_frame, textvariable=email_var)
        email_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        def save_config():
            """Save Git user configuration"""
            name = name_var.get().strip()
            email = email_var.get().strip()
            
            if not name or not email:
                messagebox.showwarning("Warning", "Please enter both name and email")
                return
            
            try:
                # Use git.Git() instead of self.repo.git
                git_cmd = git.Git()
                
                # Set global Git configuration
                git_cmd.config('--global', 'user.name', name)
                git_cmd.config('--global', 'user.email', email)
                
                self.log_operation(f"Git user configured - Name: {name}, Email: {email}")
                self.update_status("Git user configuration updated successfully", success=True)
                messagebox.showinfo("Success", "Git user configuration updated successfully")
                dialog.destroy()
                
            except Exception as e:
                error_msg = str(e)
                self.log_operation(f"Error configuring git user: {error_msg}")
                self.update_status("Failed to configure git user", success=False)
                messagebox.showerror("Error", f"Failed to configure git user: {error_msg}")
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Save", command=save_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
        
        # Set focus
        name_entry.focus()

    def create_events_path_section(self, parent):
        """Create event storage path selection area"""
        events_frame = ttk.LabelFrame(parent, text="Events Storage")
        events_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create inner frame
        inner_frame = ttk.Frame(events_frame)
        inner_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Path entry
        path_entry = ttk.Entry(inner_frame, textvariable=self.events_path, state='readonly')
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Browse button
        select_path_btn = ttk.Button(inner_frame, text="Browse", command=self.select_events_path)
        select_path_btn.pack(side=tk.RIGHT)

    def select_events_path(self):
        """Select event storage path"""
        path = filedialog.askdirectory(
            title="Select Events Storage Directory",
            initialdir=self.events_path.get()
        )
        if path:
            self.events_path.set(path)
            self.load_all_events()  # Reload events

if __name__ == "__main__":
    app = GitEventManager()
    app.run()            