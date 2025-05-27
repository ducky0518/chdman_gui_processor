import customtkinter
import tkinter
from tkinter import filedialog, messagebox
import os
import subprocess
import threading
import queue
import shlex 
import shutil 
import time
import sys 

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("CHDMAN GUI Processor (by -God-like)")
        self.geometry("750x780")
        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")

        self.processed_file_details = []
        self.stop_operation_flag = False
        self.ui_queue = queue.Queue()
        self.chdman_executable_path = self.resolve_chdman_path()

        self.create_widgets()
        self.on_mode_change() 
        self.process_ui_queue()

        if not self.chdman_executable_path:
            messagebox.showerror("CHDMAN Missing", 
                                 "chdman.exe was not found. Please place chdman.exe in the same folder as this application and restart.")
            if hasattr(self, 'scan_button'): self.scan_button.configure(state="disabled")
            if hasattr(self, 'start_op_button'): self.start_op_button.configure(state="disabled")

    def resolve_chdman_path(self):
        chdman_exe_name = "chdman.exe" if os.name == 'nt' else "chdman"
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        
        local_chdman = os.path.join(base_path, chdman_exe_name)
        if os.path.exists(local_chdman):
            return local_chdman
        
        chdman_in_path = shutil.which(chdman_exe_name)
        if chdman_in_path:
            return chdman_in_path
        return None

    def create_widgets(self):
        self.grid_columnconfigure(1, weight=1)
        current_row = 0

        # Source Directory
        self.source_dir_label = customtkinter.CTkLabel(self, text="Source Directory:")
        self.source_dir_label.grid(row=current_row, column=0, padx=10, pady=(10,5), sticky="w")
        self.source_dir_var = tkinter.StringVar()
        self.source_dir_entry = customtkinter.CTkEntry(self, textvariable=self.source_dir_var, state="disabled", width=350)
        self.source_dir_entry.grid(row=current_row, column=1, padx=10, pady=(10,5), sticky="ew")
        self.source_dir_browse_button = customtkinter.CTkButton(self, text="Browse", command=self.select_source_dir)
        self.source_dir_browse_button.grid(row=current_row, column=2, padx=10, pady=(10,5))
        current_row += 1

        # Destination Directory
        self.dest_dir_label = customtkinter.CTkLabel(self, text="Destination Directory:")
        self.dest_dir_label.grid(row=current_row, column=0, padx=10, pady=5, sticky="w")
        self.dest_dir_var = tkinter.StringVar()
        self.dest_dir_entry = customtkinter.CTkEntry(self, textvariable=self.dest_dir_var, state="disabled", width=350)
        self.dest_dir_entry.grid(row=current_row, column=1, padx=10, pady=5, sticky="ew")
        self.dest_dir_browse_button = customtkinter.CTkButton(self, text="Browse", command=self.select_dest_dir)
        self.dest_dir_browse_button.grid(row=current_row, column=2, padx=10, pady=5)
        current_row += 1

        # Mode Selection
        self.mode_label = customtkinter.CTkLabel(self, text="Operation Mode:")
        self.mode_label.grid(row=current_row, column=0, padx=10, pady=5, sticky="w")
        self.mode_var = tkinter.StringVar(value="Compress to CHD")
        self.mode_menu = customtkinter.CTkOptionMenu(self, values=["Compress to CHD", "Extract from CHD"],
                                                     variable=self.mode_var, command=self.on_mode_change)
        self.mode_menu.grid(row=current_row, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        current_row += 1

        # Extraction Format (Conditional Row)
        self.extract_format_row = current_row 
        self.extract_format_label = customtkinter.CTkLabel(self, text="Extraction Format:")
        self.extract_format_var = tkinter.StringVar(value="CUE/BIN")
        self.extract_format_options = ["CUE/BIN", "ISO", "GDI", "ISO (CD error fix)"]
        self.extract_format_menu = customtkinter.CTkOptionMenu(self, values=self.extract_format_options,
                                                              variable=self.extract_format_var)
        current_row += 1
        
        # Options
        self.delete_originals_var = tkinter.BooleanVar(value=True)
        self.delete_originals_check = customtkinter.CTkCheckBox(self, text="Delete original files (from Source) after ALL operations succeed",
                                                               variable=self.delete_originals_var)
        self.delete_originals_check.grid(row=current_row, column=0, columnspan=3, padx=10, pady=5, sticky="w")
        current_row += 1

        # Action Buttons Row
        self.action_button_row = current_row 
        self.scan_button = customtkinter.CTkButton(self, text="Scan Files", command=self.start_scan_thread)
        self.scan_button.grid(row=self.action_button_row, column=0, padx=10, pady=10, sticky="ew")
        
        self.start_op_button = customtkinter.CTkButton(self, text="Compress", command=self.start_operation_thread)
        self.start_op_button.grid(row=self.action_button_row, column=1, padx=10, pady=10, sticky="ew")

        self.stop_op_button = customtkinter.CTkButton(self, text="Stop Operation", command=self.trigger_stop_operation, 
                                                      fg_color="red", hover_color="#C00000")
        current_row += 1
        
        # File List
        self.listbox_label = customtkinter.CTkLabel(self, text="Files to be processed (Alphabetical):")
        self.listbox_label.grid(row=current_row, column=0, columnspan=3, padx=10, pady=(10,0), sticky="w")
        current_row += 1
        
        self.listbox_frame = customtkinter.CTkFrame(self)
        self.listbox_frame.grid(row=current_row, column=0, columnspan=3, padx=10, pady=5, sticky="nsew")
        self.listbox_frame.grid_rowconfigure(0, weight=1)
        self.listbox_frame.grid_columnconfigure(0, weight=1)
        
        self.listbox = tkinter.Listbox(self.listbox_frame, height=10) 
        self.listbox.grid(row=0, column=0, sticky="nsew")
        
        self.listbox_scrollbar_y = customtkinter.CTkScrollbar(self.listbox_frame, command=self.listbox.yview)
        self.listbox_scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=self.listbox_scrollbar_y.set)
        
        self.listbox_scrollbar_x = customtkinter.CTkScrollbar(self.listbox_frame, command=self.listbox.xview, orientation="horizontal")
        self.listbox_scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.listbox.configure(xscrollcommand=self.listbox_scrollbar_x.set)
        self.grid_rowconfigure(current_row, weight=1)
        current_row += 1

        # Progress Bar & Status
        self.progress_label = customtkinter.CTkLabel(self, text="Progress:")
        self.progress_label.grid(row=current_row, column=0, padx=10, pady=5, sticky="w")
        self.progressbar = customtkinter.CTkProgressBar(self)
        self.progressbar.set(0)
        self.progressbar.grid(row=current_row, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        current_row += 1

        self.status_label = customtkinter.CTkLabel(self, text="Status: Idle.", anchor="w")
        if self.chdman_executable_path:
            self.status_label.configure(text=f"Status: Idle. CHDMAN: {os.path.basename(self.chdman_executable_path)}")
        else:
            self.status_label.configure(text="Status: chdman.exe NOT FOUND! Place it with the app or in PATH and restart.")
        self.status_label.grid(row=current_row, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        current_row += 1

        warnings_text = (
            "IMPORTANT NOTES:\n"
            "- If 'Delete originals' is checked, source files WILL BE DELETED upon batch success!\n"
            "- GameCube, Wii, Xbox, PSP discs generally should not be CHDed.\n"
            "- Process files for one system/type at a time in the source directory.\n"
            "- chdman.exe must be in the app folder or system PATH.\n"
            "- PS2 CHD to ISO: Try 'CUE/BIN' for CD games, 'ISO (CD error fix)' for wrongly made CHDs."
        )
        self.warning_display = customtkinter.CTkLabel(self, text=warnings_text, justify="left", wraplength=680) 
        self.warning_display.grid(row=current_row, column=0, columnspan=3, padx=10, pady=(5,10), sticky="w")

    def _set_entry_text(self, entry_widget, text_to_set):
        entry_widget.configure(state="normal")
        entry_widget.delete(0, tkinter.END)
        entry_widget.insert(0, text_to_set)
        entry_widget.configure(state="disabled")

    def select_source_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.source_dir_var.set(path) 
            self._set_entry_text(self.source_dir_entry, path)
            self.processed_file_details.clear() 
            self.listbox.delete(0, tkinter.END)
            self.update_button_states()

    def select_dest_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.dest_dir_var.set(path) 
            self._set_entry_text(self.dest_dir_entry, path)
            self.update_button_states()

    def on_mode_change(self, new_mode_selection=None):
        mode = self.mode_var.get()
        self.listbox.delete(0, tkinter.END)
        self.processed_file_details.clear()
        self.progressbar.set(0)
        
        if mode == "Extract from CHD":
            self.extract_format_label.grid(row=self.extract_format_row, column=0, padx=10, pady=5, sticky="w")
            self.extract_format_menu.grid(row=self.extract_format_row, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
            self.start_op_button.configure(text="Extract")
        else: # Compress to CHD
            self.extract_format_label.grid_remove()
            self.extract_format_menu.grid_remove()
            self.start_op_button.configure(text="Compress")
        self.update_button_states()

    def update_button_states(self, is_scanning=False, is_processing=False):
        source_dir_ok = bool(self.source_dir_var.get())
        dest_dir_ok = bool(self.dest_dir_var.get())
        files_scanned = bool(self.processed_file_details)
        chdman_ok = bool(self.chdman_executable_path)
        
        can_scan = chdman_ok and source_dir_ok and not is_scanning and not is_processing
        can_operate = chdman_ok and source_dir_ok and dest_dir_ok and files_scanned and not is_scanning and not is_processing
        
        scan_btn_state = "normal" if can_scan else "disabled"
        start_op_btn_state = "normal" if can_operate else "disabled"
        
        if is_scanning or is_processing:
            self.scan_button.grid_remove()
            self.start_op_button.grid_remove()
            self.stop_op_button.grid(row=self.action_button_row, column=1, padx=10, pady=10, sticky="ew")
        else:
            self.stop_op_button.grid_remove()
            self.scan_button.grid(row=self.action_button_row, column=0, padx=10, pady=10, sticky="ew")
            self.scan_button.configure(state=scan_btn_state)
            self.start_op_button.grid(row=self.action_button_row, column=1, padx=10, pady=10, sticky="ew")
            self.start_op_button.configure(state=start_op_btn_state)

        controls_state = "disabled" if (is_scanning or is_processing) else "normal"
        self.source_dir_browse_button.configure(state=controls_state)
        self.dest_dir_browse_button.configure(state=controls_state)
        self.mode_menu.configure(state=controls_state)
        if self.mode_var.get() == "Extract from CHD":
            self.extract_format_menu.configure(state=controls_state)
        else:
            self.extract_format_menu.configure(state="disabled")
        self.delete_originals_check.configure(state=controls_state)

    def update_status(self, message):
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.configure(text=f"Status: {message}")
        # else: # This debug print can be noisy if status label isn't ready yet
            # print(f"DEBUG: status_label not ready. Status: {message}")


    def trigger_stop_operation(self):
        self.stop_operation_flag = True
        self.update_status("Stop signal received... finishing current file/step.")

    def start_scan_thread(self):
        if not self.chdman_executable_path: messagebox.showerror("CHDMAN Missing", "chdman.exe not found."); return
        if not self.source_dir_var.get(): messagebox.showerror("Input Error", "Source directory not selected."); return

        self.stop_operation_flag = False
        self.processed_file_details.clear()
        self.listbox.delete(0, tkinter.END)
        self.update_status(f"Scanning in {os.path.basename(self.source_dir_var.get())}...")
        self.update_button_states(is_scanning=True)
        self.progressbar.set(0)
        scan_thread = threading.Thread(target=self._scan_files_worker,
                                       args=(self.source_dir_var.get(), self.mode_var.get(), self.ui_queue),
                                       daemon=True)
        scan_thread.start()

    def _scan_files_worker(self, source_dir, mode, q):
        local_files_found = []
        files_checked_count = 0
        scan_stopped_early = False
        try:
            q.put(("status", f"Gathering files in {os.path.basename(source_dir)}..."))
            time.sleep(0.01)
            extensions_to_find = ()
            if mode == "Compress to CHD": extensions_to_find = ('.cue', '.iso', '.gdi')
            elif mode == "Extract from CHD": extensions_to_find = ('.chd',)

            for root, _, files in os.walk(source_dir):
                if self.stop_operation_flag: scan_stopped_early = True; break
                for file_idx, filename in enumerate(files):
                    if self.stop_operation_flag: scan_stopped_early = True; break
                    files_checked_count += 1
                    if files_checked_count % 100 == 0: # Update status periodically
                        q.put(("status", f"Scanning... checked {files_checked_count} files."))
                        time.sleep(0.001) # Brief yield
                    if filename.lower().endswith(extensions_to_find):
                        full_path = os.path.join(root, filename)
                        relative_path_to_source = os.path.relpath(full_path, source_dir)
                        local_files_found.append({
                            'display_name': relative_path_to_source, 
                            'full_path': full_path, 
                            'name': filename,
                            'relative_dir': os.path.dirname(relative_path_to_source), 
                            'base_name': os.path.splitext(filename)[0], 
                            'ext': os.path.splitext(filename)[1].lower()
                        })
                if self.stop_operation_flag: scan_stopped_early = True; break
            
            final_status = ""
            if scan_stopped_early: final_status = f"Scan stopped. Found {len(local_files_found)} relevant files from {files_checked_count} checked."
            else: final_status = f"Scan complete. Found {len(local_files_found)} relevant files from {files_checked_count} checked."
            q.put(("status", final_status))
            q.put(("scan_results", local_files_found))
        except Exception as e:
            q.put(("status", f"Error during scan: {e}"))
            q.put(("scan_results", []))
        finally:
            q.put(("scan_finished", None))

    def start_operation_thread(self):
        if not self.chdman_executable_path: messagebox.showerror("CHDMAN Missing", "chdman.exe not found."); return
        if not self.processed_file_details: messagebox.showinfo("No Files", "No files scanned or available for operation."); return
        if not self.source_dir_var.get(): messagebox.showerror("Input Error", "Source directory not set."); return
        if not self.dest_dir_var.get(): messagebox.showerror("Input Error", "Destination directory not set."); return
        if self.source_dir_var.get() == self.dest_dir_var.get() and self.delete_originals_var.get():
            if not messagebox.askyesno("Warning", "Source and Destination directories are the same, and 'Delete Originals' is checked.\nThis means original files might be replaced (if names collide) and then deleted upon success.\nAre you absolutely sure you want to proceed?"):
                return

        self.stop_operation_flag = False
        self.update_status(f"Starting {self.mode_var.get()} operation...")
        self.update_button_states(is_processing=True)
        self.progressbar.set(0)
        op_thread = threading.Thread(
            target=self._process_files_worker,
            args=(self.source_dir_var.get(), self.dest_dir_var.get(),
                  self.mode_var.get(), self.extract_format_var.get(),
                  self.delete_originals_var.get(), list(self.processed_file_details), 
                  self.ui_queue, self.chdman_executable_path), daemon=True)
        op_thread.start()

    def _process_files_worker(self, source_dir, dest_dir, mode, extract_format, delete_originals, files_list, q, chdman_exe):
        successful_ops = 0
        total_to_process = len(files_list)
        operation_stopped_early = False
        files_processed_this_session = 0

        try:
            for i, file_info in enumerate(files_list):
                if self.stop_operation_flag: operation_stopped_early = True; files_processed_this_session = i; break
                files_processed_this_session = i + 1
                
                q.put(("status", f"Processing {files_processed_this_session}/{total_to_process}: {file_info['display_name']}"))
                q.put(("progress", (files_processed_this_session, total_to_process)))
                time.sleep(0.01)

                input_path = file_info['full_path']
                output_sub_dir = os.path.join(dest_dir, file_info['relative_dir'])
                os.makedirs(output_sub_dir, exist_ok=True)
                output_base_name = file_info['base_name']
                
                command = [chdman_exe] 
                output_path_primary = "" 
                temp_cue_path_for_iso_fix = "" 
                verb = ""

                if mode == "Compress to CHD":
                    output_path_primary = os.path.join(output_sub_dir, output_base_name + ".chd")
                    verb = "createdvd" if file_info['ext'] == '.iso' else "createcd"
                    command.extend([verb, "-i", input_path, "-o", output_path_primary, "-f"])
                elif mode == "Extract from CHD":
                    if extract_format == "CUE/BIN":
                        output_path_primary = os.path.join(output_sub_dir, output_base_name + ".cue")
                        verb = "extractcd"
                        command.extend([verb, "-i", input_path, "-o", output_path_primary, "-f"])
                    elif extract_format == "ISO":
                        output_path_primary = os.path.join(output_sub_dir, output_base_name + ".iso")
                        verb = "extractdvd"
                        command.extend([verb, "-i", input_path, "-o", output_path_primary, "-f"])
                    elif extract_format == "GDI":
                        output_path_primary = os.path.join(output_sub_dir, output_base_name + ".gdi")
                        verb = "extractcd"
                        command.extend([verb, "-i", input_path, "-o", output_path_primary, "-f"])
                    elif extract_format == "ISO (CD error fix)":
                        temp_cue_path_for_iso_fix = os.path.join(output_sub_dir, output_base_name + "_temp.cue")
                        output_path_primary = os.path.join(output_sub_dir, output_base_name + ".iso")
                        verb = "extractcd"
                        command.extend([verb, "-i", input_path, "-o", temp_cue_path_for_iso_fix, "-ob", output_path_primary, "-f"])
                    else: 
                        # q.put(("log", f"Skipping due to unknown extraction format: {extract_format}"))
                        continue
                else: 
                    # q.put(("log", f"Unknown mode: {mode} for file {file_info['name']}"))
                    continue
                
                # q.put(("log", f"Executing: {' '.join(shlex.quote(s) for s in command)}"))
                op_successful_for_file = False
                try:
                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, 
                                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                    stdout, stderr = process.communicate(timeout=7200)

                    if process.returncode == 0:
                        if os.path.exists(output_path_primary):
                            # q.put(("log", f"Success: {file_info['display_name']} -> {os.path.basename(output_path_primary)}"))
                            successful_ops += 1
                            op_successful_for_file = True
                            if mode == "Extract from CHD" and extract_format == "ISO (CD error fix)" and os.path.exists(temp_cue_path_for_iso_fix):
                                try: os.remove(temp_cue_path_for_iso_fix) # q.put(("log", f"Removed temp: {os.path.basename(temp_cue_path_for_iso_fix)}"))
                                except Exception as e_del_cue: pass # q.put(("log", f"Could not delete temp cue {temp_cue_path_for_iso_fix}: {e_del_cue}"))
                        # else:
                            # q.put(("log", f"CHDMAN OK for {file_info['display_name']} but output {os.path.basename(output_path_primary)} missing."))
                            # if stdout: q.put(("log", f"STDOUT: {stdout.strip()}"))
                            # if stderr: q.put(("log", f"STDERR: {stderr.strip()}"))
                    # else:
                        # q.put(("log", f"CHDMAN Error for {file_info['display_name']}: Code {process.returncode}"))
                        # if stdout: q.put(("log", f"STDOUT: {stdout.strip()}"))
                        # if stderr: q.put(("log", f"STDERR: {stderr.strip()}"))
                except subprocess.TimeoutExpired:
                    # q.put(("log", f"CHDMAN Timeout for {file_info['display_name']}"))
                    if 'process' in locals() and hasattr(process, 'kill') and process.poll() is None: process.kill()
                except Exception as e_sub:
                    pass
                    # q.put(("log", f"Subprocess Error for {file_info['display_name']}: {e_sub}"))
            
            if not operation_stopped_early and delete_originals and successful_ops > 0 :
                if successful_ops == total_to_process : 
                    q.put(("status", f"All {successful_ops} ops successful. Deleting originals from Source..."))
                    time.sleep(0.1)
                    for file_info_del in files_list:
                        try:
                            source_file_to_delete = file_info_del['full_path']
                            files_to_delete_for_item = [source_file_to_delete]
                            if mode == "Compress to CHD" and file_info_del['ext'] == '.cue':
                                base_path_no_ext = os.path.splitext(source_file_to_delete)[0]
                                for common_ext in ['.bin', '.img', '.raw', '.wav', '.ape', '.flac', '.sub', '.ccd']:
                                    associated_file = base_path_no_ext + common_ext
                                    if os.path.exists(associated_file): files_to_delete_for_item.append(associated_file)
                            
                            for f_to_del in files_to_delete_for_item:
                                if os.path.exists(f_to_del): os.remove(f_to_del) # q.put(("log", f"Deleted source: {os.path.basename(f_to_del)}"))
                        except Exception as e_del: pass # q.put(("log", f"Error deleting {file_info_del['name']}: {e_del}"))
                    q.put(("status", "Source file deletion phase complete."))
                else: 
                    q.put(("status", f"Not all ops successful ({successful_ops}/{total_to_process}). Source files not deleted."))
            elif delete_originals and successful_ops == 0 and total_to_process > 0:
                 q.put(("status", "No operations successful. Source files not deleted."))

            summary_msg = ""
            if operation_stopped_early: summary_msg = f"Operation stopped. Attempted: {files_processed_this_session}, Successful: {successful_ops}."
            else: summary_msg = f"Operation Complete! Attempted: {total_to_process}, Successful: {successful_ops}."
            q.put(("status", summary_msg)); q.put(("operation_summary", summary_msg))
        except Exception as e:
            q.put(("status", f"Critical error in operation worker: {e}")); q.put(("operation_summary", f"Operation failed with critical error: {e}"))
        finally:
            q.put(("operation_finished", None))

    def process_ui_queue(self):
        try:
            while True: 
                retrieved_item = self.ui_queue.get_nowait()
                # print(f"DEBUG UI QUEUE GOT: {retrieved_item}") # Keep this if ValueError persists
                
                if not isinstance(retrieved_item, tuple) or not retrieved_item:
                    # print(f"DEBUG: Invalid item from queue: {retrieved_item}") 
                    continue

                msg_type = retrieved_item[0]
                data = retrieved_item[1] if len(retrieved_item) > 1 else None

                if msg_type == "status": self.update_status(data)
                # elif msg_type == "log": print(f"LOG: {data}") # Removed LOG printing
                elif msg_type == "scan_results":
                    self.processed_file_details = data if data is not None else []
                    self.processed_file_details.sort(key=lambda item: item['display_name'].lower())
                    self.listbox.delete(0, tkinter.END)
                    for item_data in self.processed_file_details:
                        self.listbox.insert(tkinter.END, item_data['display_name'])
                    self.update_button_states() 
                elif msg_type == "scan_finished":
                    self.stop_operation_flag = False 
                    self.update_button_states(is_scanning=False)
                elif msg_type == "progress":
                    if data is not None and isinstance(data, tuple) and len(data) == 2:
                        current, total = data 
                        if total > 0: self.progressbar.set(float(current) / total)
                        else: self.progressbar.set(0)
                    # else: # This else can be noisy if progress data is sometimes None intentionally
                        # print(f"DEBUG: Malformed or None progress data: {data}")
                elif msg_type == "operation_summary":
                    messagebox.showinfo("Operation Finished", data if data is not None else "Operation summary not available.")
                elif msg_type == "operation_finished":
                    self.stop_operation_flag = False 
                    self.update_button_states(is_processing=False)
                    self.progressbar.set(0) 
        except queue.Empty: pass 
        except Exception as e: 
            print(f"Error processing UI queue: {e}")
            import traceback
            traceback.print_exc()
        finally: self.after(100, self.process_ui_queue) 

if __name__ == "__main__":
    app = App()
    app.mainloop()