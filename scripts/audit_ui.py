"""Shared blue theme for the local audit dialogs."""

import ctypes
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk


BACKGROUND = "#EDF5FF"
LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "sklmt.png"


def _enable_high_dpi():
    if sys.platform != "win32":
        return
    try:
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except AttributeError:
        pass
    # Older Windows releases may only expose system-DPI awareness.
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except AttributeError:
        pass


def _logo_for_window(window):
    try:
        from PIL import Image, ImageChops, ImageTk
    except ImportError:
        return None
    if not LOGO_PATH.is_file():
        return None
    with Image.open(LOGO_PATH) as source:
        original = source.convert("RGB")
    white = Image.new("RGB", original.size, "white")
    cropped = original.crop(ImageChops.difference(original, white).getbbox())
    width = round(window.winfo_fpixels("88p"))
    height = round(cropped.height * width / cropped.width)
    resampling = getattr(Image, "Resampling", Image)
    logo = cropped.resize((width, height), resampling.LANCZOS)
    # Match the preview's multiply blend without modifying the source PNG.
    backdrop = Image.new("RGB", logo.size, BACKGROUND)
    return ImageTk.PhotoImage(ImageChops.multiply(logo, backdrop), master=window)


def blue_dialog(title, heading, *, lab_logo=False):
    _enable_high_dpi()
    window = tk.Tk()
    window.title(title)
    window.resizable(False, False)
    window.attributes("-topmost", True)
    background = BACKGROUND
    ink = "#183458"
    blue = "#215FA7"
    border = "#B5CCE8"
    window.configure(background=background)

    window.option_add("*Font", "{Times New Roman} 11")
    theme = ttk.Style(window)
    theme.theme_use("clam")
    theme.configure(".", background=background, foreground=ink, font=("Times New Roman", 11))
    theme.configure("Title.TLabel", font=("SimSun", 19, "bold"), foreground="#13345F")
    theme.configure("Section.TLabel", font=("Times New Roman", 11, "bold"), foreground=blue)
    theme.configure("Hint.TLabel", font=("Times New Roman", 10), foreground="#42658F")
    theme.configure("Lab.TLabel", font=("Times New Roman", 14, "bold"), foreground="#0253A0")
    theme.configure("TEntry", fieldbackground="#FFFFFF", bordercolor=border,
                    selectbackground="#C4DCFB", selectforeground=ink, padding="3p")
    theme.map("TEntry", fieldbackground=[("disabled", "#E3EDF8")], foreground=[("disabled", "#6F87A0")])
    theme.configure("TCombobox", fieldbackground="#FFFFFF", bordercolor=border,
                    arrowcolor=blue, selectbackground="#C4DCFB", selectforeground=ink, padding=4)
    theme.map("TCombobox", fieldbackground=[("readonly", "#FFFFFF")])
    theme.configure("TRadiobutton", indicatorsize="9p", indicatormargin=(0, 0, "4p", 0),
                    indicatorbackground="#FFFFFF", indicatorforeground=blue,
                    upperbordercolor="#778799", lowerbordercolor="#778799")
    theme.map("TRadiobutton", upperbordercolor=[("selected", blue)], lowerbordercolor=[("selected", blue)])
    theme.configure("TButton", background="#E0EEFE", bordercolor=border, padding=("8p", "4p"))
    theme.map("TButton", background=[("active", "#CDE3FE")])
    theme.configure("Primary.TButton", background=blue, foreground="#FFFFFF", bordercolor=blue)
    theme.map("Primary.TButton", background=[("active", "#174C89")], foreground=[("active", "#FFFFFF")])
    window.option_add("*TCombobox*Listbox.background", "#F1F7FF")
    window.option_add("*TCombobox*Listbox.foreground", ink)
    window.option_add("*TCombobox*Listbox.selectBackground", "#C4DCFB")
    window.option_add("*TCombobox*Listbox.selectForeground", ink)

    frame = ttk.Frame(window, padding=("17p", "13p"))
    frame.grid(sticky="nsew")
    title = ttk.Frame(frame)
    title.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, "7p"))
    title.columnconfigure(0, weight=1)
    ttk.Label(title, text=heading, style="Title.TLabel").grid(row=0, column=0, sticky="w")
    if lab_logo:
        title.logo = _logo_for_window(window)
        logo = (ttk.Label(title, image=title.logo) if title.logo is not None
                else ttk.Label(title, text="SKLMT", style="Lab.TLabel"))
        logo.grid(row=0, column=1, sticky="e", padx=("10p", 0))
    window.bind("<Escape>", lambda event: window.destroy())
    return window, frame


def paste_into(entry, on_empty=None):
    try:
        pasted = entry.clipboard_get().strip()
    except tk.TclError:
        pasted = ""
    if pasted:
        if entry.selection_present():
            entry.delete("sel.first", "sel.last")
        entry.insert("insert", pasted)
        entry.focus_set()
    elif on_empty:
        on_empty()
    return "break"


def bind_paste(entry, on_empty=None):
    for shortcut in ("<Control-v>", "<Control-V>", "<Shift-Insert>", "<<Paste>>"):
        entry.bind(shortcut, lambda event: paste_into(entry, on_empty))
