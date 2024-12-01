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

class GitEventManager:
    def __init__(self):
        print("Initializing GUI...")
        self.root = tk.Tk()
        print("GUI initialized successfully")
        
        # 设置窗口标题
        self.root.title("Git Event Manager")
        print("Window title set successfully")
        
        # 初始化路径变量 - 移除默认值
        self.repo_path = tk.StringVar()  # 移除 value=os.getcwd()
        
        # 初始化操作计数
        self.operation_count = 0
        
        # 初始化变量
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
        
        # 添加缓存变量
        self.cached_branches = []  # 缓存所有分支
        self.cached_tags = []      # 缓存所有标签
        self.cached_remote_branches = []  # 缓存远程分支
        
        # 添加操作控制变量
        self.enable_branch_creation = tk.BooleanVar(value=False)
        self.enable_merge = tk.BooleanVar(value=False)
        self.enable_tag_creation = tk.BooleanVar(value=False)
        
        # 初始化控件列表
        self.branch_controls = []
        self.merge_controls = []
        self.tag_controls = []
        
        print("Starting UI setup...")
        self.setup_ui()
        print("UI setup completed")

        # 移除自动初始化仓库
        # self.init_repo()
        
        # 检并设置Git用户信息
        self.check_git_config()

    def select_repo_path(self):
        """选择仓库路径"""
        path = filedialog.askdirectory(
            title="Select Git Repository",
            initialdir=os.getcwd()  # 使用当前目录作为初始目录
        )
        if path:
            self.repo_path.set(path)
            self.init_repo()  # 只在选择路径后初始化仓库
            self.log_operation(f"Selected repository path: {path}")
            self.update_status("Repository path selected", success=True)

    def init_repo(self):
        """初始化或更新Git仓库"""
        try:
            if not self.repo_path.get():
                self.log_operation("No repository path selected")
                self.update_status("Please select a repository path", success=False)
                return
            
            self.repo = git.Repo(self.repo_path.get())
            print("Git repository initialized successfully")
            
            # 初始化时加载所有信息到缓存
            self.refresh_repo_cache()
            
            # 更新所有相关显示
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
        """刷新仓库缓存信息"""
        try:
            # 获取远程仓库信息
            remote = self.repo.remote()
            remote.fetch()
            self.repo.git.fetch('--tags')
            
            # 更新分支缓存
            current = self.repo.active_branch.name
            self.cached_branches = [branch.name for branch in self.repo.heads if branch.name != current]
            
            # 更新远程分支缓存
            self.cached_remote_branches = []
            for ref in remote.refs:
                if ref.name == f"{remote.name}/HEAD":
                    continue
                branch_name = ref.name.split('/', 1)[1]
                if branch_name not in self.cached_branches and branch_name != current:
                    self.cached_remote_branches.append(branch_name)
            
            # 更新标签缓存
            self.cached_tags = [tag.name for tag in self.repo.tags]
            
            # 更新UI显示
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
        """创建日志和状态文本框"""
        # 创建日志文本框
        self.log_text = tk.Text(self.root, height=6, wrap=tk.WORD)
        self.log_text.configure(state='disabled')
        
        # 创建状态文本框
        self.status_text = tk.Text(self.root, height=3, wrap=tk.WORD)
        self.status_text.configure(state='disabled')

    def update_current_branch_labels(self):
        """新所有显示当前分支的标签"""
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
        """手动刷新分支名称"""
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
        """刷新合并项目列表（使用缓存）"""
        try:
            # 清空现有的复选框
            for widget in self.merge_inner_frame.winfo_children():
                widget.destroy()
            
            # 获分支
            current = self.repo.active_branch.name
            
            # 使用缓存的分支信息
            all_branches = sorted(set(self.cached_branches + self.cached_remote_branches))
            
            # 重新创选框
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
            
            # 更新画布滚动区域
            self.merge_inner_frame.update_idletasks()
            self.merge_canvas.configure(scrollregion=self.merge_canvas.bbox('all'))
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error refreshing merge items: {error_msg}")
            self.update_status(f"Failed to refresh merge items: {error_msg}", success=False)
    def refresh_tag_name(self):
        """动刷新签名称"""
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
        """更新最终分支名称"""
        try:
            # 果区域被禁用且不是初始化调用，则返回
            if not self.enable_branch_creation.get() and args:
                return
            
            prefix = self.branch_prefix.get()
            custom = self.branch_custom_suffix.get()
            date = self.branch_date_suffix.get()
            
            # 构建基础分支名称
            if prefix == 'custom':
                if not custom:
                    self.final_branch_name.set('')
                    return
                base_name = custom
            else:
                base_name = f"{prefix}_{date}"
                if custom:
                    base_name = f"{base_name}_{custom}"
            
            # 获取所有分支（包括远程分支）
            all_branches = [branch.name for branch in self.repo.heads]
            remote_branches = [ref.name.split('/')[-1] for ref in self.repo.remote().refs 
                             if not ref.name.endswith('/HEAD')]
            existing_branches = list(set(all_branches + remote_branches))
            
            # 如果名称已存在添加数字后缀
            if base_name in existing_branches:
                # 查找所有相似的分支名
                pattern = re.compile(f"^{re.escape(base_name)}(\\.\\d+)?$")
                similar_branches = [b for b in existing_branches if pattern.match(b)]
                
                if similar_branches:
                    # 找出最大的编号
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
                    
                    # 使用下一个编号
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
        """更新最终标签名称"""
        try:
            prefix = self.tag_prefix.get()
            custom = self.tag_custom_suffix.get()
            date = self.tag_date_suffix.get()
            
            # 构建基础标签名称
            if prefix == 'custom':
                if not custom:
                    self.final_tag_name.set('')
                return
                base_name = custom
            else:
                base_name = f"{prefix}_{date}"
                if custom:
                    base_name = f"{base_name}_{custom}"
            
            # 如果是强制检查，重新获取远程信息
            if force_check:
                self.repo.git.fetch('--tags')
            
            # 获取所有标签
            existing_tags = [tag.name for tag in self.repo.tags]
            
            # 如果名称已存在，添加数字后缀
            if base_name in existing_tags:
                # 查找所有相似的标签名
                pattern = re.compile(f"^{re.escape(base_name)}(\\.\\d+)?$")
                similar_tags = [t for t in existing_tags if pattern.match(t)]
                
                if similar_tags:
                    # 找出最大的编号
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
                    
                    # 使用下一个编号
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
        """记录操作日志"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_message = f"[{timestamp}] {message}\n"
            if details:
                log_message += f"Details:\n{details}\n"
            
            # 用日志文本框编辑
            self.log_text.configure(state='normal')
            
            # 插日志息日志文本框
            self.log_text.insert(tk.END, log_message)
            
            # 滚动到底部
            self.log_text.see(tk.END)
            
            # 禁用日志文本框编辑
            self.log_text.configure(state='disabled')
            
        except Exception as e:
            print(f"Error logging operation: {str(e)}")

    def update_status(self, message, success=True):
        """更状态栏"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            status_message = f"[{timestamp}] {'✓' if success else '✗'} Step {self.operation_count + 1}\n"
            status_message += f"{message}\n"
            status_message += "-" * 30 + "\n"
            
            # 启用状态文本框编辑
            self.status_text.configure(state='normal')
            
            # 插入状态消息到状态文本框
            self.status_text.insert(tk.END, status_message)
            
            # 滚动到底部
            self.status_text.see(tk.END)
            
            # 禁用状态文本框编辑
            self.status_text.configure(state='disabled')
            
            # 增加操作计数
            self.operation_count += 1
            
        except Exception as e:
            print(f"Error updating status: {str(e)}")
    def setup_ui(self):
        """设置用户界面"""
        # 1. 设置主窗口
        self.root.resizable(True, True)
        self.root.minsize(800, 600)
        
        # 2. 创建左右分割的主布局
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # 3. 先创建右侧面板（包含log和status文本框）
        right_panel = self.create_right_panel(main_paned)
        
        # 4. 创左侧面板
        left_panel = self.create_left_panel(main_paned)
        
        # 5. 将左右面板添加到主分割窗口
        main_paned.add(left_panel)
        main_paned.add(right_panel)
        
        # 6. 设置分割位置（左侧70%，右侧30%）
        self.root.update()
        main_paned.sashpos(0, int(self.root.winfo_width() * 0.7))

    def create_left_panel(self, parent):
        """创建左侧面板"""
        # 1. 创建左侧容器
        left_container = ttk.Frame(parent)
        
        # 2. 创建路径选择区域（新增）
        self.create_path_section(left_container)
        
        # 3. 创建画布和滚动条
        canvas = tk.Canvas(left_container)
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        
        # 4. 创滚动框架
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # 5. 在画布上创建窗口
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 6. 创建事件信息区域
        self.create_event_info_section(scrollable_frame)
        
        # 7. 创建Git操作区域
        self.create_git_operations_section(scrollable_frame)
        
        # 8. 创建工具栏（移除路径选择部分）
        self.create_toolbar(scrollable_frame)
        
        # 9. 布局画布和滚动条
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 10. 绑定鼠标滚轮
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        return left_container

    def create_path_section(self, parent):
        """建路径选择区域"""
        path_frame = ttk.LabelFrame(parent, text="Repository Path")
        path_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 创建内部框架
        inner_frame = ttk.Frame(path_frame)
        inner_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 路径输入框
        path_entry = ttk.Entry(inner_frame, textvariable=self.repo_path, state='readonly')
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # 刷新按钮
        refresh_btn = ttk.Button(inner_frame, text="↻", width=3, command=self.refresh_repo_cache)
        refresh_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # 浏览按钮
        select_path_btn = ttk.Button(inner_frame, text="Browse", command=self.select_repo_path)
        select_path_btn.pack(side=tk.RIGHT)

    def create_toolbar(self, parent):
        """创建工具栏"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        
        # 保存和历史按钮
        save_event_btn = ttk.Button(toolbar, text="Save Event", command=self.save_current_event)
        save_event_btn.pack(side=tk.RIGHT, padx=5)
        
        history_btn = ttk.Button(toolbar, text="View History", command=self.show_event_history)
        history_btn.pack(side=tk.RIGHT, padx=5)

    def create_right_panel(self, parent):
        """创建右侧面板"""
        right_frame = ttk.Frame(parent)
        
        # 1. 创建状态区域
        status_frame = ttk.LabelFrame(right_frame, text="Status")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建状态文本框容器
        status_container = ttk.Frame(status_frame)
        status_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建状态文本框 - 增加height值
        self.status_text = tk.Text(status_container, height=8, wrap=tk.WORD)  # 从height=3改为8
        self.status_text.configure(state='disabled')
        
        # 创建状态滚动条
        status_scrollbar = ttk.Scrollbar(status_container, orient="vertical", 
                                       command=self.status_text.yview)
        
        # 使grid布局管理器
        self.status_text.grid(row=0, column=0, sticky='nsew', padx=(0, 2))  # 添加右侧padding
        status_scrollbar.grid(row=0, column=1, sticky='ns')
        
        # 配置文本框的滚动
        self.status_text.configure(yscrollcommand=status_scrollbar.set)
        
        # 配置grid权重
        status_container.grid_columnconfigure(0, weight=1)
        status_container.grid_rowconfigure(0, weight=1)
        
        # 2. 创建日志区域
        log_frame = ttk.LabelFrame(right_frame, text="Operation Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建日志文本框容器
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建日志文本框
        self.log_text = tk.Text(log_container, height=15, wrap=tk.WORD)  # 调整height
        self.log_text.configure(state='disabled')
        
        # 创建日志滚动条
        log_scrollbar = ttk.Scrollbar(log_container, orient="vertical", 
                                    command=self.log_text.yview)
        
        # 使用grid布局管理器
        self.log_text.grid(row=0, column=0, sticky='nsew', padx=(0, 2))  # 添加右侧padding
        log_scrollbar.grid(row=0, column=1, sticky='ns')
        
        # 配置文本框的滚动
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # 配置grid权重
        log_container.grid_columnconfigure(0, weight=1)
        log_container.grid_rowconfigure(0, weight=1)
        
        # 配置右侧面板的权重，让Operation Log区域占据更多间
        right_frame.pack_configure(fill=tk.BOTH, expand=True)
        
        return right_frame

    def create_event_info_section(self, parent):
        """创建事件信息区域"""
        frame = ttk.LabelFrame(parent, text="Event Information")
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 事件标题
        ttk.Label(frame, text="Event Title:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.event_title).grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        
        # 事件描述
        ttk.Label(frame, text="Description:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.event_description).grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        
        # 事件备注
        ttk.Label(frame, text="Notes:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.event_notes).grid(row=2, column=1, sticky='ew', padx=5, pady=5)
        
        frame.grid_columnconfigure(1, weight=1)

    def create_git_operations_section(self, parent):
        """创建Git操作区域"""
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
        
        # 所有域创建完成后，更状态
        self.update_sections_state()

    def update_base_items(self, *args):
        """更新基础项目列表"""
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
                
            # 如果只有一个选项，自动选中它
            if self.base_items_listbox.size() == 1:
                self.base_items_listbox.select_set(0)
                self.base_items_listbox.event_generate('<<ListboxSelect>>')
                
        except Exception as e:
            self.log_operation(f"Error updating base items: {str(e)}")
            self.update_status("Failed to update base items", success=False)

    def create_branch(self):
        """创建新分支"""
        try:
            # 获取新分支名称
            new_branch_name = self.final_branch_name.get()
            if not new_branch_name:
                messagebox.showerror("Error", "Branch name cannot be empty")
                return
            
            # 获取基础项目（从 Listbox 获取选中项）
            selections = self.base_items_listbox.curselection()
            if not selections:  # 修改这里的检查逻辑
                # 如果没有选择基础项目，但有自动生成的分支名称，则使用当前分支作为基础
                current_branch = self.repo.active_branch.name
                base_item = current_branch
                self.log_operation(f"No base item selected, using current branch: {current_branch}")
            else:
                base_item = self.base_items_listbox.get(selections[0])
                # 如果是远程分支，去掉 "(remote)" 后缀
                if "(remote)" in base_item:
                    base_item = base_item.split(" (remote)")[0]
            
            # 记录操作
            self.log_operation(f"Creating new branch: {new_branch_name}", 
                             f"Base {self.base_type.get()}: {base_item}")
            
            # 切换到基础项目
            if self.base_type.get() == "branch":
                self.repo.git.checkout(base_item)
            else:
                self.repo.git.checkout(base_item)
            
            # 创建新分支
            self.repo.git.checkout('-b', new_branch_name)
            
            # 更新状态
            self.update_status(f"Created new branch: {new_branch_name}")
            
            # 更新基础项目列表
            self.update_base_items()
            
            # 更新当前分支显示
            self.update_current_branch_labels()
            
            # 显示成功消息
            messagebox.showinfo("Success", f"Branch '{new_branch_name}' created successfully")
            
            # 创建分支成功后更新 Push 区域显示
            self.update_push_labels()
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error creating branch: {error_msg}")
            self.update_status(f"Failed to create branch: {error_msg}", success=False)
            messagebox.showerror("Error", f"Failed to create branch: {error_msg}")

    def merge_branches(self):
        """合并选中的分支和标签"""
        try:
            # 获取选中的分支和标签
            selected_branches = [branch for branch, var in self.merge_vars['branch'].items() 
                               if var.get()]
            selected_tags = [tag for tag, var in self.merge_vars['tag'].items() 
                           if var.get()]
            
            if not selected_branches and not selected_tags:
                messagebox.showwarning("Warning", "Please select at least one branch or tag")
                return
            
            # 记录操作
            self.log_operation("Starting merge operation", 
                             f"Selected branches: {selected_branches}\n"
                             f"Selected tags: {selected_tags}")
            
            merged_info = []  # 存储合并信息
            
            # 合并分支
            for branch in selected_branches:
                try:
                    self.log_operation(f"Merging branch: {branch}")
                    
                    # 获取分支的最新提交信息
                    if '(remote)' in branch:
                        branch_name = branch.split(' (remote)')[0]
                        commit = self.repo.remote().refs[branch_name].commit
                    else:
                        commit = self.repo.heads[branch].commit
                    
                    # 记录分支信息
                    branch_info = {
                        'name': branch,
                        'commit_id': commit.hexsha[:8],  # 只取前8位
                        'commit_message': commit.message.strip(),
                        'commit_author': commit.author.name,
                        'commit_date': datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # 执行合并
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
            
            # 合并标签
            for tag in selected_tags:
                try:
                    self.log_operation(f"Merging tag: {tag}")
                    
                    # 获取签的提交信息
                    tag_obj = self.repo.tags[tag]
                    commit = tag_obj.commit
                    
                    # 记录标签信息
                    tag_info = {
                        'name': f"tag:{tag}",
                        'commit_id': commit.hexsha[:8],
                        'commit_message': commit.message.strip(),
                        'commit_author': commit.author.name,
                        'commit_date': datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # 执行合并
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
            
            # 刷新合并项目列表
            self.refresh_merge_items()
            
            # 返回合并信息
            return merged_info
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error during merge operation: {error_msg}")
            self.update_status("Merge operation failed", success=False)
            messagebox.showerror("Error", f"Merge operation failed: {error_msg}")
            return None

    def create_tag(self):
        """创建新标签"""
        try:
            # 获取新标签名
            new_tag_name = self.final_tag_name.get()
            if not new_tag_name:
                messagebox.showerror("Error", "Tag name cannot be empty")
                return
            
            # 记录操作
            self.log_operation(f"Creating new tag: {new_tag_name}")
            
            # 创建新标签
            self.repo.create_tag(new_tag_name)
            
            # 推送标签到程
            self.repo.remote().push(new_tag_name)
            
            # 更新状态
            self.update_status(f"Created new tag: {new_tag_name}")
            
            # 刷新合并项目列表
            self.refresh_merge_items()
            
            # 显示成功消息
            messagebox.showinfo("Success", f"Tag '{new_tag_name}' created successfully")
            
            # 更新Push区域显示
            self.update_push_labels()
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error creating tag: {error_msg}")
            self.update_status(f"Failed to create tag: {error_msg}", success=False)
            messagebox.showerror("Error", f"Failed to create tag: {error_msg}")

    def run(self):
        """运行应用程序"""
        self.root.mainloop()

    def save_current_event(self):
        """保存当前事件，包含更详细的合并信息"""
        try:
            if not self.event_title.get():
                messagebox.showwarning("Warning", "请输入事件标题")
                return
            
            event = GitEvent()
            event.title = self.event_title.get()
            event.date = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
            event.description = self.event_description.get()
            event.created_branch = self.final_branch_name.get()
            event.created_tag = self.final_tag_name.get()
            event.notes = self.event_notes.get()
            
            # 使用执行操作时保存的合并信息
            if hasattr(self, 'last_merged_info') and self.last_merged_info:
                event.merged_branches_info = self.last_merged_info
                event.merged_branches = [info['name'] for info in self.last_merged_info]
            
            self.events.append(event)
            self.save_events_to_file()
            
            # 显示成功消息
            messagebox.showinfo("Success", "事件保存成功")
            
            # 清空输入框
            self.event_title.set("")
            self.event_description.set("")
            self.event_notes.set("")
            self.last_merged_info = None  # 空合并信息
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"保存事件时出错: {error_msg}")
            self.update_status("保存事件失败", success=False)
            messagebox.showerror("Error", f"保存事件失败: {error_msg}")

    def save_events_to_file(self):
        """将事件保存到文件，包含详细的合并信息"""
        events_data = []
        for event in self.events:
            event_dict = {
                'title': event.title,
                'date': event.date,
                'description': event.description,
                'created_branch': event.created_branch,
                'merged_branches': event.merged_branches,
                'merged_branches_info': event.merged_branches_info,  # 新增：保存详细的合并信息
                'created_tag': event.created_tag,
                'notes': event.notes
            }
            events_data.append(event_dict)
            
        with open('git_events.json', 'w', encoding='utf-8') as f:
            json.dump(events_data, f, ensure_ascii=False, indent=2)
            
    def load_events_from_file(self):
        """从文件加载事件，包含详细的合并信息"""
        try:
            with open('git_events.json', 'r', encoding='utf-8') as f:
                events_data = json.load(f)
                
            self.events = []
            for event_dict in events_data:
                event = GitEvent()
                event.title = event_dict['title']
                event.date = event_dict['date']
                event.description = event_dict['description']
                event.created_branch = event_dict['created_branch']
                event.merged_branches = event_dict['merged_branches']
                event.merged_branches_info = event_dict.get('merged_branches_info', [])  # 兼容旧数据
                event.created_tag = event_dict['created_tag']
                event.notes = event_dict['notes']
                self.events.append(event)
        except FileNotFoundError:
            pass
            
    def show_event_history(self):
        """显示更详细的事件历史"""
        history_window = tk.Toplevel(self.root)
        history_window.title("事件历史")
        history_window.geometry("800x600")
        
        # 创建树形视图
        tree = ttk.Treeview(history_window, columns=(
            'Date', 'Title', 'Branch', 'Tag', 'Description'
        ), show='headings')
        
        tree.heading('Date', text='日期')
        tree.heading('Title', text='标题')
        tree.heading('Branch', text='创建分支')
        tree.heading('Tag', text='创建标签')
        tree.heading('Description', text='描述')
        
        # 设置列宽
        tree.column('Date', width=150)
        tree.column('Title', width=150)
        tree.column('Branch', width=150)
        tree.column('Tag', width=100)
        tree.column('Description', width=200)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(history_window, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # 添加数据
        for event in reversed(self.events):  # 最新的事件显示在最上面
            tree.insert('', 'end', values=(
                event.date,
                event.title,
                event.created_branch,
                event.created_tag,
                event.description
            ))
        
        def show_details(event):
            """显示事件详细信息"""
            item = tree.selection()[0]
            event_data = self.events[len(self.events) - 1 - tree.index(item)]  # 反向索引
            
            details_window = tk.Toplevel(history_window)
            details_window.title("事件详细信息")
            details_window.geometry("600x400")
            
            # 使用Text控件显示详细信息
            text = tk.Text(details_window, wrap=tk.WORD, padx=10, pady=10)
            text.pack(fill=tk.BOTH, expand=True)
            
            # 添加详细信息
            details = f"标题: {event_data.title}\n"
            details += f"日期: {event_data.date}\n"
            details += f"描述: {event_data.description}\n"
            if event_data.created_branch:
                details += f"创建分支: {event_data.created_branch}\n"
            if event_data.created_tag:
                details += f"创建标签: {event_data.created_tag}\n"
            if event_data.merged_branches_info:
                details += "\n合并的分支信息:\n"
                for branch_info in event_data.merged_branches_info:
                    details += f"\n分支: {branch_info['name']}\n"
                    details += f"提交ID: {branch_info['commit_id']}\n"
                    details += f"提交信息: {branch_info['commit_message']}\n"
                    details += f"提交作者: {branch_info['commit_author']}\n"
                    details += f"提交时间: {branch_info['commit_date']}\n"
            if event_data.notes:
                details += f"\n备注: {event_data.notes}\n"
            
            text.insert('1.0', details)
            text.configure(state='disabled')
        
        # 绑定双击事件
        tree.bind('<Double-1>', show_details)
        
        # 布局
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_toolbar(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        history_btn = ttk.Button(toolbar, text="View History", command=self.show_event_history)
        history_btn.pack(side=tk.RIGHT, padx=5)

    def on_base_item_selected(self, event):
        """基础项目选择事件处理"""
        try:
            if not self.enable_branch_creation.get():
                return
            
            if not self.base_items_listbox.curselection():
                return
            
            selected = self.base_items_listbox.get(self.base_items_listbox.curselection())
            if selected:
                # 如果是远程分支，去掉 "(remote)" 后缀
                branch_name = selected.split(' (remote)')[0]
                self.branch_prefix.set(branch_name)
                self.update_branch_name()
                
        except Exception as e:
            self.log_operation(f"Error in base item selection: {str(e)}")
            self.update_status("Failed to handle base item selection", success=False)

    def create_branch_section(self, parent):
        """创建分支操作区域"""
        branch_frame = ttk.LabelFrame(parent, text="1. Create Branch")
        branch_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 添加启用复选框
        enable_frame = ttk.Frame(branch_frame)
        enable_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Checkbutton(enable_frame, text="Enable Branch Creation", 
                        variable=self.enable_branch_creation,
                        command=self.update_sections_state).pack(side=tk.LEFT)
        
        # 当前分支信息
        current_branch_frame = ttk.Frame(branch_frame)
        current_branch_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(current_branch_frame, text="Current Branch:").pack(side=tk.LEFT, padx=(0,5))
        self.current_branch_label = ttk.Label(current_branch_frame, text="", 
                                            font=('TkDefaultFont', 9, 'bold'))
        self.current_branch_label.pack(side=tk.LEFT)
        
        # 基础类型选择
        base_type_frame = ttk.Frame(branch_frame)
        base_type_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(base_type_frame, text="Base Type:").pack(side=tk.LEFT)
        branch_radio = ttk.Radiobutton(base_type_frame, text="Branch", value="branch", 
                                      variable=self.base_type, command=self.update_base_items)
        branch_radio.pack(side=tk.LEFT, padx=5)
        tag_radio = ttk.Radiobutton(base_type_frame, text="Tag", value="tag", 
                                   variable=self.base_type, command=self.update_base_items)
        tag_radio.pack(side=tk.LEFT)
        
        # 基础项目选择 - 添加搜索功能
        base_items_frame = ttk.Frame(branch_frame)
        base_items_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(base_items_frame, text="Base Item:").pack(side=tk.LEFT)
        
        # 添加搜索框
        self.base_search_var = tk.StringVar()
        search_entry = ttk.Entry(base_items_frame, textvariable=self.base_search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 创建列表框
        listbox_frame = ttk.Frame(base_items_frame)
        listbox_frame.pack(fill=tk.X, expand=True, padx=5)
        
        self.base_items_listbox = tk.Listbox(listbox_frame, height=5, selectmode=tk.SINGLE)
        self.base_items_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 添加滚动条
        base_scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", 
                                     command=self.base_items_listbox.yview)
        base_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.base_items_listbox.configure(yscrollcommand=base_scrollbar.set)
        
        # 绑定搜索事件
        self.base_search_var.trace_add("write", self.update_base_items)
        
        # 绑定选择事件
        self.base_items_listbox.bind('<<ListboxSelect>>', self.on_base_item_selected)
        
        # 分支前缀选择
        prefix_frame = ttk.Frame(branch_frame)
        prefix_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(prefix_frame, text="Prefix:").pack(side=tk.LEFT)
        prefix_combo = ttk.Combobox(prefix_frame, textvariable=self.branch_prefix, 
                                   values=['feature', 'bugfix', 'hotfix', 'release', 'custom'])
        prefix_combo.pack(side=tk.LEFT, padx=5)
        prefix_combo.bind('<<ComboboxSelected>>', self.update_branch_name)
        
        # 自定义后缀
        custom_suffix_frame = ttk.Frame(branch_frame)
        custom_suffix_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(custom_suffix_frame, text="Custom Suffix:").pack(side=tk.LEFT)
        custom_entry = ttk.Entry(custom_suffix_frame, textvariable=self.branch_custom_suffix)
        custom_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        custom_entry.bind('<KeyRelease>', self.update_branch_name)
        
        # 日期后缀
        date_suffix_frame = ttk.Frame(branch_frame)
        date_suffix_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(date_suffix_frame, text="Date Suffix:").pack(side=tk.LEFT)
        date_entry = ttk.Entry(date_suffix_frame, textvariable=self.branch_date_suffix)
        date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        date_entry.bind('<KeyRelease>', self.update_branch_name)
        
        # 分支名称预览
        preview_frame = ttk.Frame(branch_frame)
        preview_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(preview_frame, text="Final Branch Name:").pack(side=tk.LEFT)
        ttk.Entry(preview_frame, textvariable=self.final_branch_name, 
                  state='readonly').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 刷新按钮
        ttk.Button(preview_frame, text="↻", width=3, 
                   command=self.refresh_branch_name).pack(side=tk.RIGHT)

    def create_merge_section(self, parent):
        """创建合并操作区域"""
        merge_frame = ttk.LabelFrame(parent, text="2. Merge Branches/Tags")
        merge_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 添加启用复选框
        enable_frame = ttk.Frame(merge_frame)
        enable_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Checkbutton(enable_frame, text="Enable Merge Operation", 
                        variable=self.enable_merge,
                        command=self.update_sections_state).pack(side=tk.LEFT)
        
        # 添加搜索框
        search_frame = ttk.Frame(merge_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.merge_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.merge_search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 创建滚动框架
        scroll_frame = ttk.Frame(merge_frame)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建画布和滚动条
        self.merge_canvas = tk.Canvas(scroll_frame, height=150)
        scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", 
                                 command=self.merge_canvas.yview)
        
        # 创建内部框架
        self.merge_inner_frame = ttk.Frame(self.merge_canvas)
        
        # 配置画布
        self.merge_canvas.configure(yscrollcommand=scrollbar.set)
        self.merge_canvas_window = self.merge_canvas.create_window(
            (0, 0), window=self.merge_inner_frame, anchor="nw"
        )
        
        # 布局画布和滚动条
        self.merge_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建分支和标签的字典来存储 Checkbutton
        self.branch_checkbuttons = {}
        self.tag_checkbuttons = {}
        
        def update_merge_items():
            """更新合并项目的显示"""
            search_text = self.merge_search_var.get().lower()
            
            # 清空内部框架
            for widget in self.merge_inner_frame.winfo_children():
                widget.destroy()
            
            # 创建分支区域
            branch_frame = ttk.LabelFrame(self.merge_inner_frame, text="Branches")
            branch_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
            
            # 显示分支
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
            
            # 创建标签区域
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
            
            # 更新画布滚动区域
            self.merge_inner_frame.update_idletasks()
            self.merge_canvas.configure(scrollregion=self.merge_canvas.bbox("all"))
        
        # 绑定事件以更新滚动区域
        def on_frame_configure(event):
            self.merge_canvas.configure(scrollregion=self.merge_canvas.bbox("all"))
        
        def on_canvas_configure(event):
            width = event.width - 4
            self.merge_canvas.itemconfig(self.merge_canvas_window, width=width)
        
        self.merge_inner_frame.bind("<Configure>", on_frame_configure)
        self.merge_canvas.bind("<Configure>", on_canvas_configure)
        
        # 绑定搜索事件
        self.merge_search_var.trace_add("write", lambda *args: update_merge_items())
        
        # 绑定鼠标滚轮事件
        def on_mousewheel(event):
            self.merge_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        self.merge_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # 初始显示所有项目
        update_merge_items()

    def create_tag_section(self, parent):
        """创建标签操作区域"""
        tag_frame = ttk.LabelFrame(parent, text="3. Create Tag")
        tag_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 添启用复选框
        enable_frame = ttk.Frame(tag_frame)
        enable_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Checkbutton(enable_frame, text="Enable Tag Creation", 
                        variable=self.enable_tag_creation,
                        command=self.update_sections_state).pack(side=tk.LEFT)
        
        # 标签前缀
        prefix_frame = ttk.Frame(tag_frame)
        prefix_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(prefix_frame, text="Tag Prefix:").pack(side=tk.LEFT)
        prefix_entry = ttk.Entry(prefix_frame, textvariable=self.tag_prefix)
        prefix_entry.pack(fill=tk.X, expand=True, padx=5)
        self.tag_controls.append(prefix_entry)
        
        # 自定义后缀
        custom_frame = ttk.Frame(tag_frame)
        custom_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(custom_frame, text="Custom Suffix:").pack(side=tk.LEFT)
        custom_entry = ttk.Entry(custom_frame, textvariable=self.tag_custom_suffix)
        custom_entry.pack(fill=tk.X, expand=True, padx=5)
        self.tag_controls.append(custom_entry)
        
        # 日期选择
        date_frame = ttk.Frame(tag_frame)
        date_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(date_frame, text="Date:").pack(side=tk.LEFT)
        date_entry = ttk.Entry(date_frame, textvariable=self.tag_date_suffix)
        date_entry.pack(fill=tk.X, expand=True, padx=5)
        self.tag_controls.append(date_entry)
        
        # 最终标签名称
        final_frame = ttk.Frame(tag_frame)
        final_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(final_frame, text="Final Name:").pack(side=tk.LEFT)
        final_entry = ttk.Entry(final_frame, textvariable=self.final_tag_name, 
                               state='readonly')
        final_entry.pack(fill=tk.X, expand=True, padx=5)
        
        # 添加事件绑定
        self.tag_prefix.trace_add("write", self.update_tag_name)
        self.tag_custom_suffix.trace_add("write", self.update_tag_name)
        self.tag_date_suffix.trace_add("write", self.update_tag_name)

    def create_execute_section(self, parent):
        """创建统一执行区域"""
        execute_frame = ttk.LabelFrame(parent, text="Execute Operations")
        execute_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建执行按钮
        execute_btn = ttk.Button(execute_frame, text="Execute Selected Operations", 
                                command=self.execute_operations)
        execute_btn.pack(fill=tk.X, padx=5, pady=5)

    def update_sections_state(self):
        """更新所有域的状态"""
        # 更新分支创建区域
        state = 'normal' if self.enable_branch_creation.get() else 'disabled'
        for widget in self.branch_controls:
            if isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Button, ttk.Radiobutton)):
                widget.configure(state=state)
        
        # 更新合并区域
        state = 'normal' if self.enable_merge.get() else 'disabled'
        for widget in self.merge_controls:
            if isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Button, ttk.Checkbutton)):
                widget.configure(state=state)
        
        # 更新标签创建区域
        state = 'normal' if self.enable_tag_creation.get() else 'disabled'
        for widget in self.tag_controls:
            if isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Button)):
                widget.configure(state=state)

    def execute_operations(self):
        """执行所有选中的操作"""
        try:
            operations_executed = []
            any_operation_enabled = False
            self.last_merged_info = None  # 添加类属性来存储最近的合并信息
            
            # 1. 创建分支
            if self.enable_branch_creation.get():
                any_operation_enabled = True
                branch_name = self.final_branch_name.get()
                if branch_name:
                    self.create_branch()
                    operations_executed.append(f"Created branch '{branch_name}'")
            
            # 2. 执行合并
            if self.enable_merge.get():
                any_operation_enabled = True
                self.last_merged_info = self.merge_branches()  # 保存合并信息
                if self.last_merged_info:
                    operations_executed.append(f"Merged {len(self.last_merged_info)} items")
            
            # 3. 创建标签
            if self.enable_tag_creation.get():
                any_operation_enabled = True
                tag_name = self.final_tag_name.get()
                if tag_name:
                    self.create_tag()
                    operations_executed.append(f"Created tag '{tag_name}'")
            
            # 检查是否有操作被启用
            if not any_operation_enabled:
                messagebox.showwarning("Warning", "No operations were selected")
                return
            
            # 显示执行结果
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
        """创建Push操作区域"""
        push_frame = ttk.LabelFrame(parent, text="4. Push to Remote")
        push_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建复选框变量
        self.push_branch_var = tk.BooleanVar()
        self.push_tag_var = tk.BooleanVar()
        
        # 显示当前分支和标签
        current_info_frame = ttk.Frame(push_frame)
        current_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 分支信息
        branch_frame = ttk.Frame(current_info_frame)
        branch_frame.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(branch_frame, text="Current Branch:", 
                        variable=self.push_branch_var).pack(side=tk.LEFT)
        self.push_branch_label = ttk.Label(branch_frame, text="", font=('TkDefaultFont', 9, 'bold'))
        self.push_branch_label.pack(side=tk.LEFT, padx=5)
        
        # 标签信息
        tag_frame = ttk.Frame(current_info_frame)
        tag_frame.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(tag_frame, text="Current Tag:", 
                        variable=self.push_tag_var).pack(side=tk.LEFT)
        self.push_tag_label = ttk.Label(tag_frame, text="", font=('TkDefaultFont', 9, 'bold'))
        self.push_tag_label.pack(side=tk.LEFT, padx=5)
        
        # Push按钮
        ttk.Button(push_frame, text="Push Selected to Remote", 
                   command=self.push_to_remote).pack(fill=tk.X, padx=5, pady=5)

    def update_push_labels(self):
        """更新Push区域的标签显示"""
        try:
            # 更新分支标签 - 使用当前实际分支名称
            current_branch = self.repo.active_branch.name
            self.push_branch_label.config(text=current_branch)
            self.push_branch_var.set(True)
            
            # 更新标签标签
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
        """推送选中的分支和标签到远程"""
        try:
            remote = self.repo.remote()
            pushed_items = []
            
            # 推送分支
            if self.push_branch_var.get():
                current_branch = self.repo.active_branch.name
                try:
                    # 使用 --set-upstream 推送当前分支
                    self.repo.git.push('--set-upstream', remote.name, current_branch)
                    pushed_items.append(f"branch '{current_branch}'")
                    self.log_operation(f"Pushed branch {current_branch} to remote with upstream")
                except Exception as branch_error:
                    self.log_operation(f"Error pushing branch: {str(branch_error)}")
                    messagebox.showerror("Branch Push Error", f"Failed to push branch: {str(branch_error)}")
            
            # 推送标签
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
                
                # 推送成功后刷新库缓存
                self.refresh_repo_cache()
            else:
                messagebox.showwarning("Warning", "No items selected for push")
            
        except Exception as e:
            error_msg = str(e)
            self.log_operation(f"Error pushing to remote: {error_msg}")
            self.update_status("Failed to push to remote", success=False)
            messagebox.showerror("Error", f"Failed to push to remote: {error_msg}")

    def check_git_config(self):
        """检查并设置Git用户信息"""
        try:
            # 使用 git.Git() 而不是 self.repo.git
            git_cmd = git.Git()
            
            # 检查是否已配置用户信息
            try:
                user_name = git_cmd.config('--get', 'user.name')
                user_email = git_cmd.config('--get', 'user.email')
            except git.exc.GitCommandError:
                user_name = ''
                user_email = ''
            
            # 如果没有配置，弹出配置对话框
            if not user_name or not user_email:
                self.configure_git_user()
            
        except Exception as e:
            self.log_operation(f"检查git配置时出错: {str(e)}")
            self.update_status("检查git配置失败", success=False)

    def configure_git_user(self):
        """配置Git用户信息对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Configure Git User")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 用户名
        name_frame = ttk.Frame(dialog)
        name_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(name_frame, text="User Name:").pack(side=tk.LEFT)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=name_var)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 邮箱
        email_frame = ttk.Frame(dialog)
        email_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(email_frame, text="User Email:").pack(side=tk.LEFT)
        email_var = tk.StringVar()
        email_entry = ttk.Entry(email_frame, textvariable=email_var)
        email_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        def save_config():
            """保存Git用户配置"""
            name = name_var.get().strip()
            email = email_var.get().strip()
            
            if not name or not email:
                messagebox.showwarning("Warning", "Please enter both name and email")
                return
            
            try:
                # 使用 git.Git() 而不是 self.repo.git
                git_cmd = git.Git()
                
                # 设置全局Git配置
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
        
        # 按钮
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Save", command=save_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
        
        # 设置焦点
        name_entry.focus()

if __name__ == "__main__":
    app = GitEventManager()
    app.run()            