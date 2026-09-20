"""Native controls for authored original components; no downloaded model reuse."""
from pathlib import Path
import json
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser

from .component_jobs import save_frame, list_components, verify_component
from .bedding.jobs import save_study

ROOT = Path(__file__).resolve().parent


class OriginalComponentsView(tk.Toplevel):
    def __init__(self, master, *, selected_job=None, on_message=None):
        super().__init__(master)
        self.title('Original components · frame and bedding studies')
        self.geometry('760x520')
        self.configure(bg='#06111d')
        self.on_message = on_message or (lambda text: None)
        self.selected_job = selected_job
        self.messages = queue.Queue()
        self.worker = None
        self.preview = None
        self.closing = False
        self.busy = False
        self.items = []
        self.latest = None
        self.protocol('WM_DELETE_WINDOW', self.close)
        root = ttk.Frame(self, padding=14); root.pack(fill='both', expand=True)
        ttk.Label(root, text='Build an original rigid bed frame', style='Header.TLabel').pack(anchor='w')
        ttk.Label(root, text='Authored dimensions in metres. No downloaded meshes or textures.').pack(anchor='w', pady=(4, 10))
        fields = ttk.Frame(root); fields.pack(fill='x')
        self.values = {key: tk.StringVar(value=value) for key, value in [('name', 'Original bed frame'),
                       ('mattress_width', '1.00'), ('mattress_length', '2.00'), ('slat_max_gap', '0.07')]}
        for row, (key, label) in enumerate([('name', 'Component name'), ('mattress_width', 'Mattress width (0.70–1.80 m)'),
                                           ('mattress_length', 'Mattress length (1.80–2.20 m)'), ('slat_max_gap', 'Maximum slat gap (0.04–0.07 m)')]):
            ttk.Label(fields, text=label).grid(row=row, column=0, sticky='w', pady=3)
            ttk.Entry(fields, textvariable=self.values[key]).grid(row=row, column=1, sticky='ew', padx=(12, 0))
        fields.columnconfigure(1, weight=1)
        self.bind_selected = tk.BooleanVar(value=False)
        self.bind_button = ttk.Checkbutton(root, text='Bind to the selected original-world layout (no placement)', variable=self.bind_selected)
        self.bind_button.pack(anchor='w', pady=(10, 4))
        if selected_job is None:
            self.bind_button.state(['disabled'])
        row = ttk.Frame(root); row.pack(fill='x', pady=5)
        self.build_button = ttk.Button(row, text='Build / reuse saved frame', command=self.build)
        self.build_button.pack(side='left')
        self.open_button = ttk.Button(row, text='Open selected frame', command=self.open_selected)
        self.open_button.pack(side='left', padx=8)
        self.bedding_button = ttk.Button(row, text='Inspect bedding on selected frame', command=self.build_bedding)
        self.bedding_button.pack(side='left')
        self.listbox = tk.Listbox(root, height=6, bg='#071827', fg='#ffffff', selectbackground='#174d79', exportselection=False)
        self.listbox.pack(fill='both', expand=True, pady=(6, 6))
        self.listbox.bind('<<ListboxSelect>>', self.selection_changed)
        self.status = tk.StringVar(value='Bedding studies support 1.00 × 2.00 m and 1.60 × 2.10 m frames. Visual review is pending; nothing is placed in a world.')
        ttk.Label(root, textvariable=self.status, wraplength=710).pack(anchor='w')
        self.refresh()

    def set_world_job(self, job):
        self.selected_job = job
        self.bind_selected.set(False)
        self.bind_button.state(['!disabled'] if job else ['disabled'])

    def refresh(self):
        try:
            self.items = list_components()
            self.listbox.delete(0, 'end')
            for item in self.items:
                if item['status'] == 'held':
                    self.listbox.insert('end', f"Retained {item['name']} · held: {item['hold_reason']}")
                else:
                    spec = item['spec']
                    self.listbox.insert('end', f"{item['name']} · {spec['mattress_width']:.2f} × {spec['mattress_length']:.2f} m" + (' · world-bound' if item['world_bound'] else ''))
            if self.items:
                current = [i for i, item in enumerate(self.items) if item['status'] == 'current']
                index = next((i for i in current if self.latest and self.items[i]['manifest'] == self.latest['manifest']), current[-1] if current else len(self.items) - 1)
                self.listbox.selection_set(index)
            self.selection_changed()
        except Exception as exc:
            self.status.set('Saved component unavailable: ' + str(exc))

    def selection_changed(self, event=None):
        selection = self.listbox.curselection()
        item = self.items[selection[0]] if selection else None
        available = not self.busy and item is not None and item.get('status') == 'current'
        for button in (self.open_button, self.bedding_button):
            button.state(['!disabled'] if available else ['disabled'])
        if item is not None and item.get('status') != 'current' and not self.busy:
            self.status.set('Retained frame is held: ' + str(item.get('hold_reason') or 'Not verified for this source version') + '. Its files are unchanged. Build a new revision to use the current controls.')

    def selected_current(self):
        selection = self.listbox.curselection()
        if not selection:
            self.status.set('Build or select a saved original frame first.'); return None
        item = self.items[selection[0]]
        if item.get('status') != 'current':
            self.selection_changed()
            return None
        return dict(item)

    def build(self):
        if self.busy:
            return
        try:
            spec = {'name': self.values['name'].get().strip(), **{key: float(self.values[key].get()) for key in ('mattress_width', 'mattress_length', 'slat_max_gap')}}
            job = self.selected_job if self.bind_selected.get() else None
            if self.bind_selected.get() and job is None:
                raise ValueError('Choose a saved original-world layout first')
        except ValueError as exc:
            self.status.set('Check the authored dimensions: ' + str(exc)); return
        self.set_busy(True)
        self.status.set('Constructing and checking original rails, feet, supports and slats…')

        def work():
            try:
                self.messages.put(('ready', save_frame(spec, world_job=job)))
            except Exception as exc:
                self.messages.put(('error', str(exc)))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start(); self.after(100, self.poll)

    def set_busy(self, value):
        self.busy = value
        for button in (self.build_button, self.open_button, self.bedding_button):
            button.state(['disabled'] if value else ['!disabled'])
        if not value:
            self.selection_changed()

    def build_bedding(self):
        if self.busy:
            return
        item = self.selected_current()
        if item is None:
            return
        self.set_busy(True)
        self.status.set('Checking the saved frame and preparing its original bedding study…')

        def work():
            try:
                self.messages.put(('study-ready', save_study(item['manifest'], item['sha256'])))
            except Exception as exc:
                self.messages.put(('error', str(exc)))
        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start(); self.after(100, self.poll)

    def poll(self):
        if self.closing:
            return
        try:
            kind, value = self.messages.get_nowait()
        except queue.Empty:
            self.after(100, self.poll); return
        self.set_busy(False)
        if kind == 'ready':
            self.latest = value; self.refresh()
            text = 'Saved original frame and construction recipe. Open it to inspect parts and assembly. It is not placed in a world.'
            self.status.set(text); self.on_message(text + ' ' + value['component_file'])
        elif kind == 'study-ready':
            self.on_message('Saved original frame/bedding engineering study; visual review pending; no world placement. ' + value['component_file'])
            self.start_preview(value, ROOT / 'bedding/preview_server.py', 'Opened the saved frame and bedding study. Contact and fold appearance still need review.')
        elif kind == 'preview-ready':
            process, item, ready, message = value
            if process is not self.preview or process.poll() is not None:
                self.close_preview(); self.status.set('Preview closed before it was ready.'); return
            try:
                result = json.loads(ready)
                if not isinstance(result.get('url'), str) or not result['url'].startswith('http://127.0.0.1:') or result.get('manifest') != item['manifest']:
                    raise ValueError('Unexpected component preview identity')
                webbrowser.open(result['url']); self.status.set(message)
            except Exception as exc:
                self.close_preview(); self.status.set('Component preview unavailable: ' + str(exc))
        else:
            self.close_preview()
            self.status.set('Frame construction held: ' + value)
            self.on_message('Original frame construction held: ' + value)

    def close_preview(self):
        if self.preview is not None:
            process = self.preview; self.preview = None
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=3)
            for stream in (process.stdout, process.stderr):
                if stream:
                    stream.close()

    def open_selected(self):
        if self.busy:
            return
        item = self.selected_current()
        if item is None:
            return
        try:
            verify_component(item['manifest'], item['sha256'])
            self.start_preview(item, ROOT / 'preview_server.py', 'Opened saved original frame inspection.')
        except Exception as exc:
            self.close_preview(); self.status.set('Component preview unavailable: ' + str(exc))

    def start_preview(self, item, server, message):
        try:
            self.close_preview()
            executable = Path(sys.executable)
            if executable.name.lower() == 'pythonw.exe':
                executable = executable.with_name('python.exe')
            command = [str(executable), '-I', '-B', '-X', 'utf8', str(server), '--manifest', item['manifest'], '--sha256', item['sha256']]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.preview = process
            self.set_busy(True)
            self.status.set('Opening the exact saved component preview…')
            ready = queue.Queue()
            threading.Thread(target=lambda: ready.put(process.stdout.readline(8000)), daemon=True).start()
            def wait_ready():
                try:
                    self.messages.put(('preview-ready', (process, item, ready.get(timeout=12), message)))
                except queue.Empty:
                    self.messages.put(('error', 'Preview startup timed out'))
            self.worker = threading.Thread(target=wait_ready, daemon=True)
            self.worker.start(); self.after(100, self.poll)
        except Exception as exc:
            self.set_busy(False); self.close_preview(); self.status.set('Component preview unavailable: ' + str(exc))

    def close(self):
        self.closing = True
        self.close_preview()
        self.destroy()
