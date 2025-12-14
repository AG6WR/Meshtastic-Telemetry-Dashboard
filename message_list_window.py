"""
Message List Window - Central messaging hub

Shows all messages in tabbed interface:
- Inbox: Unread messages only
- All Messages: All non-archived messages
- Archived: Archived messages

Double-click message to open MessageViewer.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Dict, Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class MessageListWindow:
    """Modal window for viewing message list with tabs"""
    
    def __init__(self, parent, message_manager, 
                 on_view_message: Optional[Callable] = None,
                 on_send_message: Optional[Callable] = None):
        """Initialize message list window
        
        Args:
            parent: Parent window
            message_manager: MessageManager instance
            on_view_message: Callback when message double-clicked - receives (message_id)
            on_send_message: Callback when compose clicked - receives (node_id)
        """
        self.parent = parent
        self.message_manager = message_manager
        self.on_view_message_callback = on_view_message
        self.on_send_message_callback = on_send_message
        
        # Get colors from parent (dark theme)
        self.colors = getattr(parent, 'colors', {
            'bg_frame': '#2b2b2b',
            'bg_main': '#1e1e1e',
            'fg_normal': '#e0e0e0',
            'fg_secondary': '#b0b0b0',
            'fg_good': '#228B22',
            'fg_warning': '#FFA500',
            'fg_bad': '#FF6B9D'
        })
        
        # Create dialog window
        self.window = tk.Toplevel(parent)
        self.window.title("Messages")
        self.window.geometry("630x600")
        self.window.resizable(True, True)
        self.window.transient(parent)
        self.window.configure(bg=self.colors['bg_frame'])
        
        # Position relative to parent (50px down and right)
        self.window.update_idletasks()
        x = parent.winfo_x() + 50
        y = parent.winfo_y() + 50
        self.window.geometry(f"+{x}+{y}")
        
        # Create widgets
        self._create_widgets()
        
        # Load initial data
        self._refresh_all_tabs()
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_widgets(self):
        """Create window widgets"""
        # Title bar
        title_frame = tk.Frame(self.window, bg=self.colors['bg_frame'])
        title_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        tk.Label(title_frame, text="Message Center", 
                font=("Liberation Sans", 16, "bold"),
                bg=self.colors['bg_frame'], fg=self.colors['fg_normal']).pack(side="left")
        
        # Close button (rightmost)
        close_btn = tk.Button(title_frame, text="✕ Close", 
                             command=self._on_close,
                             bg='#424242', fg='white',
                             width=10, height=2,
                             font=("Liberation Sans", 12))
        close_btn.pack(side="right", padx=(5, 0))
        
        # Refresh button
        refresh_btn = tk.Button(title_frame, text="🔄 Refresh", 
                               command=self._refresh_all_tabs,
                               bg='#404040', fg='white',
                               width=10, height=2,
                               font=("Liberation Sans", 12))
        refresh_btn.pack(side="right", padx=(5, 0))
        
        # Compose button
        compose_btn = tk.Button(title_frame, text="✉ Compose", 
                               command=self._on_compose,
                               bg='#2e7d32', fg='white',
                               width=10, height=2,
                               font=("Liberation Sans", 12))
        compose_btn.pack(side="right")
        
        # Tab notebook
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background=self.colors['bg_frame'], borderwidth=0)
        style.configure('TNotebook.Tab', background=self.colors['bg_main'], 
                       foreground=self.colors['fg_normal'], padding=[10, 5],
                       font=("Liberation Sans", 12))
        style.map('TNotebook.Tab', background=[('selected', self.colors['bg_frame'])])
        
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        
        # Create tabs
        self.inbox_frame = self._create_tab("Inbox")
        self.sent_frame = self._create_tab("Sent")
        self.archived_frame = self._create_tab("Archived")
        
        self.notebook.add(self.inbox_frame, text="Inbox")
        self.notebook.add(self.sent_frame, text="Sent")
        self.notebook.add(self.archived_frame, text="Archived")
        
        # Action buttons at bottom
        action_frame = tk.Frame(self.window, bg=self.colors['bg_frame'])
        action_frame.pack(fill="x", padx=10, pady=10)
        
        # Left side buttons
        left_frame = tk.Frame(action_frame, bg=self.colors['bg_frame'])
        left_frame.pack(side="left")
        
        tk.Button(left_frame, text="View", command=self._on_view_selected,
                 bg='#0d47a1', fg='white', width=10, height=2,
                 font=("Liberation Sans", 12)).pack(side="left", padx=(0, 5))
        
        tk.Button(left_frame, text="Reply", command=self._on_reply_selected,
                 bg='#2e7d32', fg='white', width=10, height=2,
                 font=("Liberation Sans", 12)).pack(side="left", padx=(0, 5))
        
        tk.Button(left_frame, text="Archive", command=self._on_archive_selected,
                 bg='#f57c00', fg='white', width=10, height=2,
                 font=("Liberation Sans", 12)).pack(side="left", padx=(0, 5))
        
        tk.Button(left_frame, text="Delete", command=self._on_delete_selected,
                 bg='#c62828', fg='white', width=10, height=2,
                 font=("Liberation Sans", 12)).pack(side="left")
        
        # Selection count label
        self.selection_label = tk.Label(action_frame, text="No selection",
                                       bg=self.colors['bg_frame'], fg=self.colors['fg_secondary'],
                                       font=("Liberation Sans", 12))
        self.selection_label.pack(side="right")
    
    def _create_tab(self, tab_name: str) -> tk.Frame:
        """Create a tab with message list
        
        Args:
            tab_name: Name of the tab
            
        Returns:
            Frame containing the tab content
        """
        frame = tk.Frame(self.notebook, bg=self.colors['bg_frame'])
        
        # Create scrollable canvas for message list with checkboxes
        canvas = tk.Canvas(frame, bg=self.colors['bg_main'], highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_main'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Make scrollable frame expand to canvas width
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', on_canvas_configure)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Store references
        if tab_name == "Inbox":
            self.inbox_frame_content = scrollable_frame
            self.inbox_canvas = canvas
            self.inbox_items = []  # List of (checkbox_var, message_id, frame)
        elif tab_name == "Sent":
            self.sent_frame_content = scrollable_frame
            self.sent_canvas = canvas
            self.sent_items = []
        elif tab_name == "Archived":
            self.archived_frame_content = scrollable_frame
            self.archived_canvas = canvas
            self.archived_items = []
        
        return frame
    
    def _refresh_all_tabs(self):
        """Refresh all tab contents"""
        self._refresh_tab("inbox")
        self._refresh_tab("sent")
        self._refresh_tab("archived")
    
    def _refresh_tab(self, tab_type: str):
        """Refresh a specific tab
        
        Args:
            tab_type: "inbox", "sent", or "archived"
        """
        # Get the appropriate frame and items list
        if tab_type == "inbox":
            content_frame = self.inbox_frame_content
            items_list = self.inbox_items
        elif tab_type == "sent":
            content_frame = self.sent_frame_content
            items_list = self.sent_items
        else:  # archived
            content_frame = self.archived_frame_content
            items_list = self.archived_items
        
        # Clear existing items
        for widget in content_frame.winfo_children():
            widget.destroy()
        items_list.clear()
        
        # Get messages
        all_messages = self.message_manager.load_messages()
        logger.info(f"_refresh_tab({tab_type}): Loaded {len(all_messages)} total messages")
        
        # Filter messages based on tab type
        if tab_type == "inbox":
            # Inbox: Received messages not archived
            messages = [m for m in all_messages 
                       if m.get('direction') == 'received' and not m.get('archived', False)]
        elif tab_type == "sent":
            # Sent: Sent messages not archived
            messages = [m for m in all_messages 
                       if m.get('direction') == 'sent' and not m.get('archived', False)]
        else:  # archived
            # Archived: Both sent and received that are archived
            messages = [m for m in all_messages if m.get('archived', False)]
        
        logger.info(f"_refresh_tab({tab_type}): Filtered to {len(messages)} messages")
        
        # Sort by timestamp (newest first)
        messages.sort(key=lambda m: m.get('timestamp', 0), reverse=True)
        
        # Add messages as checkbox rows
        for msg in messages:
            self._add_message_row(content_frame, items_list, msg)
        
        logger.info(f"_refresh_tab({tab_type}): Added {len(messages)} message rows")
        
        # Update selection count
        self._update_selection_count()
    
    def _add_message_row(self, parent_frame: tk.Frame, items_list: list, message: Dict[str, Any]):
        """Add a message as a checkbox row
        
        Args:
            parent_frame: Parent frame to add to
            items_list: List to track checkbox vars
            message: Message dictionary
        """
        message_id = message.get('message_id', 'unknown')
        direction = message.get('direction', 'received')
        from_name = message.get('from_name', 'Unknown')
        to_ids = message.get('to_node_ids', [])
        is_bulletin = message.get('is_bulletin', False)
        text = message.get('text', '')
        timestamp = message.get('timestamp', 0)
        is_read = message.get('read', False)
        structured = message.get('structured', True)
        
        # Create row frame
        row_frame = tk.Frame(parent_frame, bg=self.colors['bg_frame'], relief='raised', bd=1)
        row_frame.pack(fill="x", padx=5, pady=2)
        
        # Checkbox
        check_var = tk.BooleanVar(value=False)
        checkbox = tk.Checkbutton(row_frame, variable=check_var,
                                  bg=self.colors['bg_frame'],
                                  fg='white',
                                  activebackground=self.colors['bg_frame'],
                                  activeforeground='white',
                                  selectcolor=self.colors['bg_main'],
                                  command=self._update_selection_count)
        checkbox.pack(side="left", padx=5, pady=5)
        
        # Message content frame (clickable)
        content_frame = tk.Frame(row_frame, bg=self.colors['bg_frame'], cursor="hand2")
        content_frame.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        # Direction icon and label
        if direction == 'sent':
            icon = "📤"
            dir_label = "Sent"
        elif is_bulletin:
            icon = "🔔"
            dir_label = "Bulletin"
        else:
            icon = "📥"
            dir_label = "Received"
        
        # From/To display
        if direction == 'sent':
            if is_bulletin:
                from_to = "To: Everyone"
            elif len(to_ids) > 1:
                from_to = f"To: {len(to_ids)} nodes"
            else:
                from_to = f"To: {to_ids[0] if to_ids else 'Unknown'}"
        else:
            from_to = f"From: {from_name}"
        
        # Preview (first 120 chars for wider display)
        preview = text[:120] + "..." if len(text) > 120 else text
        
        # Add status indicators
        status_icons = []
        
        # For received messages: show if unread or replied
        if direction == 'received':
            if not is_read:
                status_icons.append("🔵 Unread")
            # TODO: Add replied indicator when we track replies
            # if message.get('replied', False):
            #     status_icons.append("↩️ Replied")
        
        # For sent messages: show read receipt status
        elif direction == 'sent' and structured:
            read_receipts = message.get('read_receipts', {})
            if read_receipts:
                # Count how many recipients have read it
                read_count = sum(1 for r in read_receipts.values() if r.get('read'))
                total_recipients = len(message.get('to_node_ids', []))
                if read_count > 0:
                    if read_count == total_recipients:
                        status_icons.append(f"✓✓ Read by all ({read_count})")
                    else:
                        status_icons.append(f"✓ Read by {read_count}/{total_recipients}")
        
        # Add structured/unstructured indicator
        if not structured:
            status_icons.append("[Plain]")
        
        # Build preview with status
        if status_icons:
            preview = " ".join(status_icons) + " • " + preview
        
        # Format timestamp - for sent messages, show when it was read if available
        dt = datetime.fromtimestamp(timestamp)
        time_str = dt.strftime("%m/%d %H:%M")
        
        # For sent messages, add read timestamp if available
        if direction == 'sent' and structured:
            read_receipts = message.get('read_receipts', {})
            if read_receipts:
                # Get the latest read time
                read_times = [r.get('read_at') for r in read_receipts.values() if r.get('read_at')]
                if read_times:
                    latest_read = max(read_times)
                    read_dt = datetime.fromtimestamp(latest_read)
                    time_str = f"Sent {time_str}, Read {read_dt.strftime('%m/%d %H:%M')}"
        
        # Top line: icon + type + from/to + time
        top_line = tk.Frame(content_frame, bg=self.colors['bg_frame'])
        top_line.pack(fill="x")
        
        tk.Label(top_line, text=f"{icon} {dir_label}", 
                bg=self.colors['bg_frame'], fg=self.colors['fg_normal'],
                font=("Liberation Sans", 11, "bold")).pack(side="left")
        
        tk.Label(top_line, text=from_to, 
                bg=self.colors['bg_frame'], fg=self.colors['fg_normal'],
                font=("Liberation Sans", 11)).pack(side="left", padx=(10, 0))
        
        tk.Label(top_line, text=time_str, 
                bg=self.colors['bg_frame'], fg=self.colors['fg_secondary'],
                font=("Liberation Sans", 11)).pack(side="right")
        
        # Bottom line: preview
        tk.Label(content_frame, text=preview, 
                bg=self.colors['bg_frame'], fg=self.colors['fg_normal'],
                font=("Liberation Sans", 11), anchor="w", justify="left").pack(fill="x")
        
        # Make entire row clickable to view message (except checkbox)
        def on_click(event):
            if self.on_view_message_callback:
                self.on_view_message_callback(message_id)
                self.after(500, self._refresh_all_tabs)
        
        # Bind to the entire row and all its children except checkbox
        row_frame.bind('<Button-1>', on_click)
        content_frame.bind('<Button-1>', on_click)
        for child in content_frame.winfo_children():
            child.bind('<Button-1>', on_click)
            for subchild in child.winfo_children():
                subchild.bind('<Button-1>', on_click)
        
        # Store checkbox var and message_id
        items_list.append((check_var, message_id, row_frame))
    
    def _update_selection_count(self):
        """Update the selection count label"""
        count = self._get_selected_count()
        if count == 0:
            self.selection_label.config(text="No selection")
        elif count == 1:
            self.selection_label.config(text="1 message selected")
        else:
            self.selection_label.config(text=f"{count} messages selected")
    
    def _get_selected_count(self) -> int:
        """Get count of selected checkboxes"""
        count = 0
        for check_var, _, _ in self.inbox_items + self.sent_items + self.archived_items:
            if check_var.get():
                count += 1
        return count
    
    def _get_selected_message_ids(self) -> list:
        """Get list of selected message IDs"""
        selected = []
        for check_var, message_id, _ in self.inbox_items + self.sent_items + self.archived_items:
            if check_var.get():
                selected.append(message_id)
        return selected
    
    def after(self, ms: int, func):
        """Schedule a function call after delay"""
        self.window.after(ms, func)
    
    def _on_view_selected(self):
        """View the selected message(s)"""
        selected = self._get_selected_message_ids()
        
        if not selected:
            messagebox.showinfo("No Selection", "Please select a message to view.", parent=self.window)
            return
        
        # View first selected message
        message_id = selected[0]
        if self.on_view_message_callback:
            self.on_view_message_callback(message_id)
            # Refresh after viewing
            self.after(500, self._refresh_all_tabs)
    
    def _on_reply_selected(self):
        """Reply to the selected message"""
        selected = self._get_selected_message_ids()
        
        if not selected:
            messagebox.showinfo("No Selection", "Please select a message to reply to.", parent=self.window)
            return
        
        if len(selected) > 1:
            messagebox.showwarning("Multiple Selection", "Please select only one message to reply to.", parent=self.window)
            return
        
        # Get first selected message
        message_id = selected[0]
        message = self.message_manager.get_message_by_id(message_id)
        if message:
            # Determine who to reply to
            if message.get('direction') == 'received':
                reply_to_id = message.get('from_node_id')
            else:
                # For sent messages, reply to first recipient
                to_ids = message.get('to_node_ids', [])
                reply_to_id = to_ids[0] if to_ids else None
            
            if reply_to_id and self.on_send_message_callback:
                self.on_send_message_callback(reply_to_id)
    
    def _on_archive_selected(self):
        """Archive the selected message(s)"""
        selected = self._get_selected_message_ids()
        
        if not selected:
            messagebox.showinfo("No Selection", "Please select message(s) to archive.", parent=self.window)
            return
        
        # Archive all selected
        archived_count = 0
        for message_id in selected:
            if self.message_manager.archive_message(message_id):
                archived_count += 1
        
        if archived_count > 0:
            logger.info(f"Archived {archived_count} message(s)")
            self._refresh_all_tabs()
            messagebox.showinfo("Archived", f"Archived {archived_count} message(s).", parent=self.window)
    
    def _on_delete_selected(self):
        """Delete the selected message(s)"""
        selected = self._get_selected_message_ids()
        
        if not selected:
            messagebox.showinfo("No Selection", "Please select message(s) to delete.", parent=self.window)
            return
        
        count = len(selected)
        result = messagebox.askyesno(
            "Delete Messages",
            f"Are you sure you want to delete {count} message(s)?\\n\\n"
            "⚠️ Warning: For EmComm/emergency use, consider Archive instead.\\n"
            "Deleted messages cannot be recovered.",
            parent=self.window,
            icon='warning'
        )
        
        if result:
            deleted_count = 0
            for message_id in selected:
                self.message_manager.delete_message(message_id)
                deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} message(s)")
                self._refresh_all_tabs()
    
    def _on_compose(self):
        """Handle compose button click"""
        # Get available nodes from parent's data collector
        if not hasattr(self.parent, 'data_collector') or not self.parent.data_collector:
            logger.warning("No data collector available")
            return
        
        nodes_data = self.parent.data_collector.get_nodes_data()
        if not nodes_data:
            logger.warning("No nodes available")
            tk.messagebox.showinfo("No Nodes", "No nodes available to send message to.", parent=self.window)
            return
        
        # Create simple node selector dialog
        selector = tk.Toplevel(self.window)
        selector.title("Select Recipient")
        selector.geometry("400x500")
        selector.transient(self.window)
        selector.configure(bg=self.colors['bg_frame'])
        
        # Position relative to parent (50px down and right)
        selector.update_idletasks()
        x = self.window.winfo_x() + 50
        y = self.window.winfo_y() + 50
        selector.geometry(f"+{x}+{y}")
        
        tk.Label(selector, text="Select a node to send message:", 
                font=("Liberation Sans", 12, "bold"),
                bg=self.colors['bg_frame'], fg=self.colors['fg_normal']).pack(pady=10)
        
        # Create listbox with scrollbar
        list_frame = tk.Frame(selector, bg=self.colors['bg_frame'])
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                            bg=self.colors['bg_main'], fg=self.colors['fg_normal'],
                            font=("Liberation Sans", 11), selectmode="single",
                            height=15)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Add nodes to listbox
        node_list = []
        for node_id, node_data in sorted(nodes_data.items(), key=lambda x: x[1].get('Node LongName', x[0])):
            node_name = node_data.get('Node LongName', node_id)
            display_name = f"{node_name} ({node_id})"
            listbox.insert(tk.END, display_name)
            node_list.append(node_id)
        
        # Buttons
        btn_frame = tk.Frame(selector, bg=self.colors['bg_frame'])
        btn_frame.pack(pady=10)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                node_id = node_list[selection[0]]
                selector.destroy()
                if self.on_send_message_callback:
                    self.on_send_message_callback(node_id)
            else:
                tk.messagebox.showwarning("No Selection", "Please select a node.", parent=selector)
        
        tk.Button(btn_frame, text="Select", command=on_select,
                 bg='#2e7d32', fg='white', width=10, height=2,
                 font=("Liberation Sans", 12, "bold")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=selector.destroy,
                 bg='#424242', fg='white', width=10, height=2,
                 font=("Liberation Sans", 12)).pack(side="left", padx=5)
        
        # Bind double-click to select
        listbox.bind('<Double-Button-1>', lambda e: on_select())
    
    def _on_close(self):
        """Handle window close"""
        self.window.destroy()
