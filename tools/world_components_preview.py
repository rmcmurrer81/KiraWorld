"""Standalone native controls for original frame and bedding engineering studies."""
from pathlib import Path
import sys
import tkinter as tk
sys.path.insert(0,str(Path(__file__).resolve().parent))
from world_builder_components.workspace_adapter import OriginalComponentsView

def main():
    root=tk.Tk();root.withdraw()
    view=OriginalComponentsView(root,selected_job=None)
    def close():
        view.close()
        root.destroy()
    view.protocol('WM_DELETE_WINDOW',close)
    root.mainloop()

if __name__=='__main__':main()
