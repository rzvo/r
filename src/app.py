import os
import json
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageEnhance, ImageFilter

CONFIG_NAME = "reo_config.json"

PRESETS = [
    ("1920x1080", 1920, 1080),
    ("2560x1440", 2560, 1440),
    ("3840x2160", 3840, 2160),
    ("1440x1080", 1440, 1080),
    ("1280x720", 1280, 720),
]

BORDER = "#3a4252"
INK = "#ffffff"
MUTED = "#e2e7f0"
ACCENT = "#e5c07b"


def resource_path(rel_path: str) -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base, rel_path)


def crop_bg(bg_img: Image.Image | None, win_w: int, win_h: int, x: int, y: int, w: int, h: int, dim: float = 0.14) -> ImageTk.PhotoImage | None:
    if bg_img is None or w <= 1 or h <= 1 or win_w <= 1 or win_h <= 1:
        return None
    full = bg_img.resize((win_w, win_h), Image.Resampling.BILINEAR)
    x0 = max(0, min(win_w - 1, int(x)))
    y0 = max(0, min(win_h - 1, int(y)))
    x1 = max(x0 + 1, min(win_w, int(x + w)))
    y1 = max(y0 + 1, min(win_h, int(y + h)))
    part = full.crop((x0, y0, x1, y1))
    if dim > 0:
        overlay = Image.new("RGB", part.size, (12, 15, 22))
        part = Image.blend(part, overlay, alpha=max(0.0, min(0.85, dim)))
    return ImageTk.PhotoImage(part)


class GlassAccordion(tk.Frame):
    def __init__(self, parent, title: str, app_ref, on_toggle=None):
        super().__init__(parent, highlightthickness=1, highlightbackground=BORDER, bd=0)
        self.title = title
        self.app = app_ref
        self.on_toggle = on_toggle
        self.expanded = False

        self.header_bg_lbl = tk.Label(self, bd=0, highlightthickness=0)
        self.header_bg_lbl.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.header = tk.Button(
            self,
            text=f"+  {title}",
            command=self.toggle,
            fg=INK,
            activeforeground=ACCENT,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            anchor="w",
            padx=10,
            pady=7,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        self.header.pack(fill=tk.X)

        self.body = tk.Frame(self, bd=0, highlightthickness=0, padx=10, pady=8)
        self.body_bg_lbl = tk.Label(self.body, bd=0, highlightthickness=0)
        self.body_bg_lbl.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._h_photo = None
        self._b_photo = None
        self.bind("<Configure>", lambda _e: self.sync_bg())

    def sync_bg(self):
        self.update_idletasks()
        w = self.header.winfo_width()
        h = self.header.winfo_height()
        if w > 1 and h > 1 and self.app.bg_raw_img is not None:
            rx = self.header.winfo_rootx() - self.app.root.winfo_rootx()
            ry = self.header.winfo_rooty() - self.app.root.winfo_rooty()
            p = crop_bg(self.app.bg_raw_img, self.app.root.winfo_width(), self.app.root.winfo_height(), rx, ry, w, h, dim=0.22)
            if p:
                self._h_photo = p
                self.header_bg_lbl.configure(image=self._h_photo)
                self.header_bg_lbl.lower(self.header)
                try:
                    self.header.configure(bg=self._sample_color(p, 0.22), activebackground=self._sample_color(p, 0.12))
                except Exception:
                    pass

        if self.expanded:
            bw = self.body.winfo_width()
            bh = self.body.winfo_height()
            if bw > 1 and bh > 1 and self.app.bg_raw_img is not None:
                bx = self.body.winfo_rootx() - self.app.root.winfo_rootx()
                by = self.body.winfo_rooty() - self.app.root.winfo_rooty()
                bp = crop_bg(self.app.bg_raw_img, self.app.root.winfo_width(), self.app.root.winfo_height(), bx, by, bw, bh, dim=0.30)
                if bp:
                    self._b_photo = bp
                    self.body_bg_lbl.configure(image=self._b_photo)
                    self.body_bg_lbl.lower(self.body_bg_lbl)
                    for child in self.body.winfo_children():
                        if child is not self.body_bg_lbl:
                            try:
                                child.lift()
                            except Exception:
                                pass

    @staticmethod
    def _sample_color(photo: ImageTk.PhotoImage, factor: float = 0.2) -> str:
        return "#121722"

    def toggle(self):
        self.expanded = not self.expanded
        if self.expanded:
            self.header.config(text=f"-  {self.title}", fg=ACCENT)
            self.body.pack(fill=tk.X)
        else:
            self.header.config(text=f"+  {self.title}", fg=INK)
            self.body.pack_forget()
        self.app.root.after(20, self.sync_bg)
        if self.on_toggle:
            self.on_toggle()


class ReoApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("reo")
        self.root.geometry("1120x700")
        self.root.minsize(780, 500)
        self.root.configure(bg="#0a0d12")

        ico_p = self.default_ico()
        if ico_p and os.path.exists(ico_p):
            try:
                self.root.iconbitmap(ico_p)
            except Exception:
                pass

        base_dir = os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, "frozen", False) else __file__))
        self.config_path = os.path.join(base_dir, CONFIG_NAME)

        self.source_img: Image.Image | None = None
        self.result_img: Image.Image | None = None
        self.bg_raw_img: Image.Image | None = None
        self.bg_photo = None
        self.top_bg_photo = None
        self.menu_bg_photo = None
        self.stage_bg_photo = None
        self.preview_photo = None
        self.stage_visible = False
        self.sections: list[GlassAccordion] = []

        self.settings = self.load_settings()
        self.build_ui()
        self.load_bg_source()
        self.render_backdrop()
        self.root.after(80, self.refresh_all_glass)

    def default_ico(self) -> str:
        p = resource_path("reo.ico")
        if os.path.exists(p):
            return p
        p2 = resource_path(os.path.join("assets", "reo.ico"))
        return p2 if os.path.exists(p2) else ""

    def default_bg(self) -> str:
        p = resource_path("theme_bg.jpg")
        if os.path.exists(p):
            return p
        p2 = resource_path(os.path.join("assets", "theme_bg.jpg"))
        return p2 if os.path.exists(p2) else ""

    def default_settings(self) -> dict:
        return {
            "w": 1920,
            "h": 1080,
            "mode": "stretch",
            "scale_x": 100.0,
            "scale_y": 100.0,
            "offset_x": 0,
            "offset_y": 0,
            "brightness": 1.0,
            "contrast": 1.0,
            "saturation": 1.0,
            "bg_dim": 0.05,
            "bg_blur": 0.0,
        }

    def load_settings(self) -> dict:
        cfg = self.default_settings()
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        for k in cfg:
                            if k in loaded:
                                cfg[k] = loaded[k]
            except Exception:
                pass
        return cfg

    def save_settings(self):
        self.sync_settings()
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            messagebox.showinfo("reo", "Saved.")
        except Exception as e:
            messagebox.showerror("reo", str(e))

    def load_bg_source(self):
        bg_path = self.default_bg()
        if bg_path and os.path.exists(bg_path):
            try:
                img = Image.open(bg_path).convert("RGB")
                blur_r = float(self.settings.get("bg_blur", 0.0))
                if blur_r > 0:
                    img = img.filter(ImageFilter.GaussianBlur(radius=blur_r))
                self.bg_raw_img = img
                return
            except Exception:
                pass
        self.bg_raw_img = None

    def build_ui(self):
        self.bg_canvas = tk.Canvas(self.root, highlightthickness=0, bd=0, bg="#0a0d12")
        self.bg_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.bg_canvas.bind("<Configure>", self._on_resize)

        self.top_bar = tk.Frame(self.root, bd=0, highlightthickness=1, highlightbackground=BORDER, padx=12, pady=6)
        self.top_bar.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(10, 6))
        self.top_bg_lbl = tk.Label(self.top_bar, bd=0, highlightthickness=0)
        self.top_bg_lbl.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.lbl_brand = tk.Label(self.top_bar, text="reo", fg=ACCENT, font=("Segoe UI", 12, "bold"))
        self.lbl_brand.pack(side=tk.LEFT)
        self.lbl_status = tk.Label(self.top_bar, text="1920x1080 | stretch", fg=MUTED, font=("Segoe UI", 9))
        self.lbl_status.pack(side=tk.LEFT, padx=14)

        tk.Button(
            self.top_bar,
            text="Export PNG",
            command=lambda: self.export_file("PNG"),
            bg=ACCENT,
            fg="#0a0d12",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            padx=12,
            pady=3,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(side=tk.RIGHT)

        self.btn_save = tk.Button(
            self.top_bar,
            text="Save",
            command=self.save_settings,
            fg=INK,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=3,
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        self.btn_save.pack(side=tk.RIGHT, padx=6)

        self.workspace = tk.Frame(self.root, bd=0, highlightthickness=0)
        self.workspace.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.menu_col = tk.Frame(self.workspace, bd=0, width=265, highlightthickness=1, highlightbackground=BORDER)
        self.menu_col.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.menu_col.pack_propagate(False)

        self.menu_bg_lbl = tk.Label(self.menu_col, bd=0, highlightthickness=0)
        self.menu_bg_lbl.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.menu_canvas = tk.Canvas(self.menu_col, highlightthickness=0, bd=0)
        self.menu_canvas.pack(fill=tk.BOTH, expand=True)

        self.menu_canvas_bg_id = self.menu_canvas.create_image(0, 0, anchor="nw")
        self.menu_inner = tk.Frame(self.menu_canvas, bd=0, highlightthickness=0, padx=8, pady=8)
        self.menu_win_id = self.menu_canvas.create_window((0, 0), window=self.menu_inner, anchor="nw", width=247)
        self.menu_inner.bind("<Configure>", lambda _e: self._on_menu_inner_cfg())

        self.stage = tk.Frame(self.workspace, bd=0, highlightthickness=1, highlightbackground=BORDER, padx=8, pady=8)
        self.stage_bg_lbl = tk.Label(self.stage, bd=0, highlightthickness=0)
        self.stage_bg_lbl.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.preview_canvas = tk.Canvas(self.stage, highlightthickness=0, bd=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas.bind("<Configure>", lambda _e: self.render_preview())

        self._build_sections()

    def _on_menu_inner_cfg(self):
        self.menu_canvas.configure(scrollregion=self.menu_canvas.bbox("all"))
        self.refresh_all_glass()

    def _on_resize(self, _e):
        self.render_backdrop()
        self.refresh_all_glass()

    def refresh_all_glass(self):
        self.root.update_idletasks()
        rw = max(1, self.root.winfo_width())
        rh = max(1, self.root.winfo_height())
        if self.bg_raw_img is None:
            return

        tw, th = self.top_bar.winfo_width(), self.top_bar.winfo_height()
        if tw > 1 and th > 1:
            tx = self.top_bar.winfo_rootx() - self.root.winfo_rootx()
            ty = self.top_bar.winfo_rooty() - self.root.winfo_rooty()
            tp = crop_bg(self.bg_raw_img, rw, rh, tx, ty, tw, th, dim=0.22)
            if tp:
                self.top
