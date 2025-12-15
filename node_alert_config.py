#!/usr/bin/env python3
"""
Node Alert Configuration Dialog
Per-node telemetry alert enable/disable settings
"""

import tkinter as tk
from tkinter import messagebox
import json
import os

class NodeAlertConfigDialog:
    """Dialog for configuring per-node alert settings"""
    
    def __init__(self, parent, nodes_data):
        self.parent = parent
        self.nodes_data = nodes_data
        self.result = None
        
        # Alert types that can be configured per node
        self.alert_types = [
            ("voltage", "Low Voltage (Ch3)"),
            ("temperature", "High Temperature"), 
            ("offline", "Node Offline")
        ]
        
        self.checkbox_vars = {}
        self.create_dialog()
        self.load_settings()
    
    def create_dialog(self):
        """Create the configuration dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Node Alert Configuration")
        self.dialog.geometry("600x500")
        self.dialog.configure(bg='#2d2d2d')
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (500 // 2)
        self.dialog.geometry(f"600x500+{x}+{y}")
        
        # Title
        title_label = tk.Label(self.dialog, 
                              text="Configure Node Alert Settings",
                              font=("Arial", 16, "bold"),
                              bg='#2d2d2d', fg='white')
        title_label.pack(pady=15)
        
        # Instructions
        instruction_text = ("Enable or disable specific alert types for each node.\n"
                          "Disable voltage alerts for nodes without voltage sensors.")
        
        instruction_label = tk.Label(self.dialog,
                                   text=instruction_text,
                                   font=("Arial", 10),
                                   bg='#2d2d2d', fg='#cccccc',
                                   justify='center')
        instruction_label.pack(pady=10)
        
        # Main scrollable area
        self.create_scrollable_content()
        
        # Buttons
        self.create_buttons()
    
    def create_scrollable_content(self):
        """Create scrollable content area"""
        # Frame for canvas and scrollbar
        canvas_frame = tk.Frame(self.dialog, bg='#2d2d2d')
        canvas_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Canvas and scrollbar
        canvas = tk.Canvas(canvas_frame, bg='#3d3d3d', highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#3d3d3d')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create node rows
        for i, (node_id, node_data) in enumerate(self.nodes_data.items()):
            self.create_node_row(scrollable_frame, node_id, node_data, i)
    
    def create_node_row(self, parent, node_id, node_data, row_num):
        """Create a row for one node's settings"""
        node_name = node_data.get('Node LongName', 'Unknown')
        short_name = node_data.get('Node ShortName', 'Unk')
        
        # Node frame
        node_frame = tk.LabelFrame(parent,
                                 text=f"{node_name} ({short_name})",
                                 font=("Arial", 11, "bold"),
                                 bg='#4d4d4d', fg='white',
                                 bd=2)
        node_frame.pack(fill='x', padx=10, pady=5)
        
        # Show current values - focus on ch3_voltage since that's what your hardware uses
        main_voltage = node_data.get('Voltage')
        ch3_voltage = node_data.get('Ch3 Voltage')
        temp = node_data.get('Temperature')
        
        # Use ch3_voltage as primary, fall back to main voltage
        actual_voltage = ch3_voltage if (ch3_voltage is not None and ch3_voltage != 0) else main_voltage
        
        status_text = "Current: "
        if temp is not None:
            status_text += f"Temp: {temp:.1f}°C  "
        
        if actual_voltage is not None and actual_voltage != 0:
            voltage_source = "Ch3" if (ch3_voltage is not None and ch3_voltage != 0) else "Main"
            status_text += f"Voltage: {actual_voltage:.2f}V ({voltage_source})  "
        else:
            status_text += "Voltage: No Ch3 sensor configured  "
        
        status_label = tk.Label(node_frame, text=status_text,
                              font=("Arial", 9),
                              bg='#4d4d4d', fg='#cccccc')
        status_label.pack(anchor='w', padx=10, pady=(5, 10))
        
        # Checkboxes frame
        checkboxes_frame = tk.Frame(node_frame, bg='#4d4d4d')
        checkboxes_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        # Store checkbox variables for this node
        self.checkbox_vars[node_id] = {}
        
        # Create checkboxes for each alert type
        for i, (alert_key, alert_name) in enumerate(self.alert_types):
            var = tk.BooleanVar()
            var.set(True)  # Default enabled
            
            checkbox = tk.Checkbutton(checkboxes_frame,
                                    text=alert_name,
                                    variable=var,
                                    font=("Arial", 10),
                                    bg='#4d4d4d', fg='white',
                                    selectcolor='#2d2d2d',
                                    activebackground='#4d4d4d',
                                    activeforeground='white')
            checkbox.grid(row=i//2, column=i%2, sticky='w', padx=10, pady=2)
            
            # Special handling for voltage - show current status without assumptions
            if alert_key == "voltage":
                main_voltage = node_data.get('Voltage')
                ch3_voltage = node_data.get('Ch3 Voltage') 
                last_heard = node_data.get('Last Heard')
                is_offline = (last_heard is None)
                
                warning_text = None
                warning_color = 'gray'
                
                if is_offline:
                    warning_text = "Offline - no recent data"
                    warning_color = 'gray'
                elif ch3_voltage is None:
                    warning_text = "Ch3 voltage: no data"
                    warning_color = 'orange' 
                elif ch3_voltage == 0:
                    warning_text = "Ch3 voltage: 0.00V"
                    warning_color = '#DC143C'  # Crimson - could indicate problem
                elif ch3_voltage > 0:
                    warning_text = f"Ch3 voltage: {ch3_voltage:.2f}V"
                    warning_color = '#228B22'  # Forest green - good reading
                elif main_voltage is not None and main_voltage > 0:
                    warning_text = f"Main voltage: {main_voltage:.2f}V"
                    warning_color = '#228B22'  # Forest green - good reading
                else:
                    warning_text = "No voltage data"
                    warning_color = 'orange'
                
                if warning_text:
                    info_label = tk.Label(checkboxes_frame,
                                        text=warning_text,
                                        font=("Arial", 8),
                                        bg='#4d4d4d', fg=warning_color)
                    info_label.grid(row=i//2, column=2, sticky='w', padx=5)
            
            self.checkbox_vars[node_id][alert_key] = var
    
    def create_buttons(self):
        """Create action buttons"""
        button_frame = tk.Frame(self.dialog, bg='#2d2d2d')
        button_frame.pack(fill='x', padx=20, pady=15)
        
        # Bulk action buttons on left
        bulk_frame = tk.Frame(button_frame, bg='#2d2d2d')
        bulk_frame.pack(side='left')
        
        # Remove the bulk disable button - let user decide manually
        info_label = tk.Label(bulk_frame,
                             text="Configure nodes based on hardware",
                             font=("Arial", 9, "italic"),
                             bg='#2d2d2d', fg='#888888')
        info_label.pack(side='left', padx=(0, 10))
        
        enable_all_btn = tk.Button(bulk_frame,
                                  text="Enable All",
                                  command=self.enable_all_alerts,
                                  bg='#28a745', fg='white',
                                  font=("Liberation Sans Narrow", 12),
                                  width=12, height=2)
        enable_all_btn.pack(side='left')
        
        # Main action buttons on right - enlarged for touch input
        action_frame = tk.Frame(button_frame, bg='#2d2d2d')
        action_frame.pack(side='right')
        
        cancel_btn = tk.Button(action_frame,
                              text="Cancel",
                              command=self.cancel,
                              bg='#6c757d', fg='white',
                              font=("Liberation Sans Narrow", 12),
                              width=12, height=2)
        cancel_btn.pack(side='right', padx=(10, 0))
        
        save_btn = tk.Button(action_frame,
                            text="Save",
                            command=self.save_settings,
                            bg='#007bff', fg='white',
                            font=("Liberation Sans Narrow", 12, "bold"),
                            width=12, height=2)
        save_btn.pack(side='right')
    
    def load_settings(self):
        """Load existing settings from file"""
        try:
            if os.path.exists('config/node_alert_settings.json'):
                with open('config/node_alert_settings.json', 'r') as f:
                    settings = json.load(f)
                
                # Apply loaded settings
                for node_id, node_settings in settings.items():
                    if node_id in self.checkbox_vars:
                        for alert_type, enabled in node_settings.items():
                            if alert_type in self.checkbox_vars[node_id]:
                                self.checkbox_vars[node_id][alert_type].set(enabled)
        except Exception as e:
            print(f"Error loading settings: {e}")
    

    
    def enable_all_alerts(self):
        """Enable all alerts for all nodes"""
        for node_vars in self.checkbox_vars.values():
            for var in node_vars.values():
                var.set(True)
        messagebox.showinfo("All Alerts Enabled", "Enabled all alert types for all nodes.")
    
    def save_settings(self):
        """Save settings and close dialog"""
        # Collect settings from checkboxes
        settings = {}
        for node_id, node_vars in self.checkbox_vars.items():
            settings[node_id] = {}
            for alert_type, var in node_vars.items():
                settings[node_id][alert_type] = var.get()
        
        self.result = settings
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel without saving"""
        self.result = None
        self.dialog.destroy()