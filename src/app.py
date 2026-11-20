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

SURFACE = "#0c0f14"
SURFACE_ALT = "#12161e"
SURFACE_HOVER = "#1a202c"
BORDER = "#2a303c"
INK = "#f3f5f8"
MUTED = "#b4bccb"
ACCENT = "#e5c07b"


def resource_path(rel_path: str) -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base, rel_path)


def crop_bg_region(bg_img: Image.Image | None, win_w: int, win_h: int, x: int, y: int, w: int, h: int, dim: float = 0.25) -> ImageTk.PhotoImage | None:
    if bg_img is None or w <= 1 or h <= 1 or win_w <= 1 or win_h <= 1:
        return None
    full = bg_img.resize((win_w, win_h), Image.Resampling.BILINEAR)
    x0 = max(0, min(win_w - 1, int(x)))
    y0 = max(0, min(win_h - 1, int(y)))
    x1 = max(x0 + 1, min(win_w, int(x + w)))
    y1 = max(y0 + 1, min(win_h, int(y + h)))
    part = full.crop((x0, y0, x1, y1))
    if dim > 0:
        overlay = Image.new("RGB", part.size, (10, 12, 16))
        part = Image.blend(part, overlay, alpha=max(0.0, min(0.9, dim)))
    return ImageTk.PhotoImage(part)


class AccordionSection(tk.Frame):
    def __init__(self, parent, title: str, on_toggle=None):
        super().__init__(parent, bg=SURFACE_ALT, highlightthickness=1, highlightbackground=BORDER, bd=0)
        self.title = title
        self.on_toggle = on_toggle
        self.expanded = False

        self.header = tk.Button(
            self,
            text=f"+  {title}",
            command=self.toggle,
            bg=SURFACE_ALT,
            fg=INK,
            activebackground=SURFACE_HOVER,
            activeforeground="#ffffff",
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

        self.body = tk.Frame(self, bg=SURFACE, bd=0, highlightthickness=0, padx=10, pady=8)

    def toggle(self):
        self.expanded = not self.expanded
        if self.expanded:
            self.header.config(text=f"-  {self.title}", fg=ACCENT)
            self.body.pack(fill=tk.X)
        else:
            self.header.config(text=f"+  {self.title}", fg=INK)
            self.body.pack_forget()
        if self.on_toggle:
            self.on_toggle()


class ReoApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("reo")
        self.root.geometry("1120x700")
        self.root.minsize(780, 500)
        self.root.configure(bg=SURFACE)

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
        self.menu_bg_photo = None
        self.preview_photo = None
        self.stage_visible = False

        self.settings = self.load_settings()
        self.build_ui()
        self.load_bg_source()
        self.render_backdrop()
        self.root.after(80, self.refresh_glass_panels)

def default_ico(self) -> str:
        p = resource_path("reo.ico")
        return p if os.path.exists(p) else ""

    def default_bg(self) -> str:
        p = resource_path("theme_bg.jpg")
        return p if os.path.exists(p) else ""

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
            "bg_dim": 0.08,
            "bg_blur": 0.0,
        }

    def load_settings(self) -> dict:
        cfg = self.default_settings()
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        for k in ("w", "h", "mode", "scale_x", "scale_y", "offset_x", "offset_y", "brightness", "contrast", "saturation", "bg_dim", "bg_blur"):
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
        self.bg_canvas = tk.Canvas(self.root, highlightthickness=0, bd=0, bg=SURFACE)
        self.bg_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.bg_canvas.bind("<Configure>", self._on_root_resize)

        top_bar = tk.Frame(
            self.root,
            bg=SURFACE_ALT,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            padx=12,
            pady=6,
        )
        top_bar.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(10, 6))

        tk.Label(top_bar, text="reo", bg=SURFACE_ALT, fg=ACCENT, font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        self.lbl_status = tk.Label(top_bar, text="1920x1080 | stretch", bg=SURFACE_ALT, fg=MUTED, font=("Segoe UI", 9))
        self.lbl_status.pack(side=tk.LEFT, padx=14)

        tk.Button(
            top_bar,
            text="Export PNG",
            command=lambda: self.export_file("PNG"),
            bg=ACCENT,
            fg=SURFACE,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            padx=12,
            pady=3,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(side=tk.RIGHT)

        tk.Button(
            top_bar,
            text="Save",
            command=self.save_settings,
            bg=SURFACE_HOVER,
            fg=INK,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=3,
            font=("Segoe UI", 9),
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=6)

        self.workspace = tk.Frame(self.root, bg=SURFACE, bd=0, highlightthickness=0)
        self.workspace.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.menu_col = tk.Frame(
            self.workspace,
            bg=SURFACE,
            bd=0,
            width=265,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.menu_col.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.menu_col.pack_propagate(False)
        self.menu_col.bind("<Configure>", lambda _e: self.refresh_glass_panels())

        self.menu_bg_label = tk.Label(self.menu_col, bd=0, highlightthickness=0)
        self.menu_bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.menu_canvas = tk.Canvas(self.menu_col, bg=SURFACE, highlightthickness=0, bd=0)
        self.menu_inner = tk.Frame(self.menu_canvas, bg=SURFACE, bd=0, highlightthickness=0, padx=8, pady=8)
        self.menu_inner.bind(
            "<Configure>",
            lambda _e: self.menu_canvas.configure(scrollregion=self.menu_canvas.bbox("all")),
        )
        self.menu_canvas.create_window((0, 0), window=self.menu_inner, anchor="nw", width=247)
        self.menu_canvas.pack(fill=tk.BOTH, expand=True)

        self.stage = tk.Frame(
            self.workspace,
            bg=SURFACE,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            padx=8,
            pady=8,
        )

        self.preview_canvas = tk.Canvas(self.stage, bg=SURFACE, highlightthickness=0, bd=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas.bind("<Configure>", lambda _e: self.render_preview())

        self._build_sections()

    def _on_root_resize(self, _e):
        self.render_backdrop()
        self.refresh_glass_panels()

    def refresh_glass_panels(self):
        if self.bg_raw_img is None:
            self.menu_bg_label.configure(image="", bg=SURFACE)
            return
        rw = max(1, self.root.winfo_width())
        rh = max(1, self.root.winfo_height())
        mw = self.menu_col.winfo_width()
        mh = self.menu_col.winfo_height()
        mx = self.menu_col.winfo_rootx() - self.root.winfo_rootx()
        my = self.menu_col.winfo_rooty() - self.root.winfo_rooty()
        photo = crop_bg_region(self.bg_raw_img, rw, rh, mx, my, mw, mh, dim=0.35)
        if photo is not None:
            self.menu_bg_photo = photo
            self.menu_bg_label.configure(image=self.menu_bg_photo)
            self.menu_bg_label.lower(self.menu_canvas)

    def _show_preview_stage(self):
        if not self.stage_visible:
            self.stage.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.stage_visible = True

    def _build_sections(self):
        p = self.menu_inner

        sec_img = AccordionSection(p, "Image & Resolution")
        sec_img.pack(fill=tk.X, pady=(0, 6))

        tk.Button(
            sec_img.body,
            text="Pick Image",
            command=self.pick_source_image,
            bg=SURFACE_HOVER,
            fg="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            pady=5,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(fill=tk.X, pady=(0, 6))

        self.var_w = tk.StringVar(value=str(self.settings["w"]))
        self.var_h = tk.StringVar(value=str(self.settings["h"]))

        row_res = tk.Frame(sec_img.body, bg=SURFACE, bd=0, highlightthickness=0)
        row_res.pack(fill=tk.X, pady=(0, 6))
        tk.Entry(
            row_res,
            textvariable=self.var_w,
            width=7,
            bg=SURFACE_ALT,
            fg=INK,
            insertbackground=INK,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
        ).pack(side=tk.LEFT)
        tk.Label(row_res, text=" x ", bg=SURFACE, fg=MUTED).pack(side=tk.LEFT)
        tk.Entry(
            row_res,
            textvariable=self.var_h,
            width=7,
            bg=SURFACE_ALT,
            fg=INK,
            insertbackground=INK,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
        ).pack(side=tk.LEFT)
        tk.Button(
            row_res,
            text="Apply",
            command=self.apply_custom_size,
            bg=ACCENT,
            fg=SURFACE,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            padx=8,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        ).pack(side=tk.RIGHT)

        for label, pw, ph in PRESETS:
            tk.Button(
                sec_img.body,
                text=f"{label} (Stretch)",
                command=lambda ww=pw, hh=ph: self.set_size(ww, hh),
                bg=SURFACE_ALT,
                fg=INK,
                relief=tk.FLAT,
                bd=0,
                highlightthickness=0,
                pady=3,
                font=("Segoe UI", 8),
                cursor="hand2",
            ).pack(fill=tk.X, pady=1)

        sec_pos = AccordionSection(p, "Stretch & Position")
        sec_pos.pack(fill=tk.X, pady=(0, 6))

        self.var_mode = tk.StringVar(value=self.settings["mode"])
        for m in ("stretch", "cover", "contain"):
            tk.Radiobutton(
                sec_pos.body,
                text=m,
                variable=self.var_mode,
                value=m,
                command=self.render_preview,
                bg=SURFACE,
                fg=INK,
                selectcolor=SURFACE_ALT,
                activebackground=SURFACE,
                activeforeground=ACCENT,
                bd=0,
                highlightthickness=0,
                font=("Segoe UI", 8),
            ).pack(anchor="w")

        self.var_sx = tk.DoubleVar(value=self.settings["scale_x"])
        self.var_sy = tk.DoubleVar(value=self.settings["scale_y"])
        self.var_ox = tk.IntVar(value=self.settings["offset_x"])
        self.var_oy = tk.IntVar(value=self.settings["offset_y"])

        self._slider(sec_pos.body, "Scale X %", self.var_sx, 50.0, 200.0, self.render_preview)
        self._slider(sec_pos.body, "Scale Y %", self.var_sy, 50.0, 200.0, self.render_preview)
        self._slider(sec_pos.body, "Offset X", self.var_ox, -600, 600, self.render_preview)
        self._slider(sec_pos.body, "Offset Y", self.var_oy, -600, 600, self.render_preview)

        sec_col = AccordionSection(p, "Color Tune")
        sec_col.pack(fill=tk.X, pady=(0, 6))

        self.var_br = tk.DoubleVar(value=self.settings["brightness"])
        self.var_ct = tk.DoubleVar(value=self.settings["contrast"])
        self.var_sa = tk.DoubleVar(value=self.settings["saturation"])

        self._slider(sec_col.body, "Brightness", self.var_br, 0.3, 1.8, self.render_preview)
        self._slider(sec_col.body, "Contrast", self.var_ct, 0.4, 1.8, self.render_preview)
        self._slider(sec_col.body, "Saturation", self.var_sa, 0.0, 2.0, self.render_preview)

    def _slider(self, parent, label: str, var, lo, hi, cb):
        top = tk.Frame(parent, bg=SURFACE, bd=0, highlightthickness=0)
        top.pack(fill=tk.X)
        tk.Label(top, text=label, bg=SURFACE, fg=INK, font=("Segoe UI", 8)).pack(side=tk.LEFT)
        val_lbl = tk.Label(top, text="", bg=SURFACE, fg=ACCENT, font=("Segoe UI", 8, "bold"))
        val_lbl.pack(side=tk.RIGHT)

        def _fmt(*_):
            v = var.get()
            val_lbl.config(text=f"{int(v)}" if isinstance(var, tk.IntVar) else f"{v:.2f}")

        _fmt()
        var.trace_add("write", _fmt)

        tk.Scale(
            parent,
            variable=var,
            from_=lo,
            to=hi,
            resolution=1 if isinstance(var, tk.IntVar) else 0.02,
            orient=tk.HORIZONTAL,
            showvalue=False,
            bg=SURFACE,
            troughcolor=SURFACE_ALT,
            activebackground=ACCENT,
            highlightthickness=0,
            bd=0,
            relief=tk.FLAT,
            command=lambda _v: cb(),
        ).pack(fill=tk.X, pady=(0, 4))

    def sync_settings(self):
        try:
            w = max(64, int(self.var_w.get()))
        except ValueError:
            w = 1920
        try:
            h = max(64, int(self.var_h.get()))
        except ValueError:
            h = 1080

        self.settings.update({
            "w": w,
            "h": h,
            "mode": self.var_mode.get(),
            "scale_x": float(self.var_sx.get()),
            "scale_y": float(self.var_sy.get()),
            "offset_x": int(self.var_ox.get()),
            "offset_y": int(self.var_oy.get()),
            "brightness": float(self.var_br.get()),
            "contrast": float(self.var_ct.get()),
            "saturation": float(self.var_sa.get()),
        })

    def set_size(self, w: int, h: int):
        self.var_w.set(str(w))
        self.var_h.set(str(h))
        self.render_preview()

    def apply_custom_size(self):
        self.render_preview()

    def pick_source_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All", "*.*")])
        if path:
            self.source_img = Image.open(path).convert("RGB")
            self._show_preview_stage()
            self.render_preview()

    def render_backdrop(self):
        self.sync_settings()
        cw = max(1, self.bg_canvas.winfo_width())
        ch = max(1, self.bg_canvas.winfo_height())
        self.bg_canvas.delete("all")

        if self.bg_raw_img is not None:
            try:
                img = self.bg_raw_img.resize((cw, ch), Image.Resampling.BILINEAR)
                blur_r = float(self.settings.get("bg_blur", 0.0))
                if blur_r > 0:
                    img = img.filter(ImageFilter.GaussianBlur(radius=blur_r))
                dim = max(0.0, min(0.95, float(self.settings.get("bg_dim", 0.08))))
                dark = Image.new("RGB", (cw, ch), (12, 15, 20))
                img = Image.blend(img, dark, alpha=dim)
                self.bg_photo = ImageTk.PhotoImage(img)
                self.bg_canvas.create_image(0, 0, anchor="nw", image=self.bg_photo)
                return
            except Exception:
                pass
        self.bg_canvas.configure(bg=SURFACE)

    def build_output(self) -> Image.Image | None:
        if self.source_img is None:
            return None
        self.sync_settings()
        tw, th = self.settings["w"], self.settings["h"]
        mode = self.settings["mode"]
        sx = self.settings["scale_x"] / 100.0
        sy = self.settings["scale_y"] / 100.0
        ox, oy = self.settings["offset_x"], self.settings["offset_y"]

        img = self.source_img.copy()
        img = ImageEnhance.Brightness(img).enhance(self.settings["brightness"])
        img = ImageEnhance.Contrast(img).enhance(self.settings["contrast"])
        img = ImageEnhance.Color(img).enhance(self.settings["saturation"])

        sw, sh = img.size
        if mode == "stretch":
            bw, bh = tw, th
        elif mode == "cover":
            sc = max(tw / max(1, sw), th / max(1, sh))
            bw, bh = max(1, int(sw * sc)), max(1, int(sh * sc))
        else:
            sc = min(tw / max(1, sw), th / max(1, sh))
            bw, bh = max(1, int(sw * sc)), max(1, int(sh * sc))

        fw, fh = max(1, int(bw * sx)), max(1, int(bh * sy))
        resized = img.resize((fw, fh), Image.Resampling.LANCZOS)
        out = Image.new("RGB", (tw, th), (12, 15, 20))
        out.paste(resized, ((tw - fw) // 2 + ox, (th - fh) // 2 + oy))
        self.result_img = out
        return out

    def render_preview(self):
        if self.source_img is None or not self.stage_visible:
            return
        out = self.build_output()
        if out is None:
            return
        tw, th = self.settings["w"], self.settings["h"]
        self.lbl_status.config(text=f"{tw}x{th} | {self.settings['mode']}")

        cw = max(40, self.preview_canvas.winfo_width() - 12)
        ch = max(40, self.preview_canvas.winfo_height() - 12)
        sc = min(cw / max(1, tw), ch / max(1, th))
        pw, ph = max(1, int(tw * sc)), max(1, int(th * sc))

        thumb = out.resize((pw, ph), Image.Resampling.BILINEAR)
        self.preview_photo = ImageTk.PhotoImage(thumb)
        self.preview_canvas.delete("all")
        x0 = (self.preview_canvas.winfo_width() - pw) // 2
        y0 = (self.preview_canvas.winfo_height() - ph) // 2
        self.preview_canvas.create_image(x0, y0, anchor="nw", image=self.preview_photo)
        self.preview_canvas.create_rectangle(x0, y0, x0 + pw, y0 + ph, outline=ACCENT, width=1)

    def export_file(self, fmt: str):
        out = self.build_output()
        if out is None:
            messagebox.showinfo("reo", "Pick an image first.")
            return
        tw, th = self.settings["w"], self.settings["h"]
        ext = "png" if fmt == "PNG" else "jpg"
        path = filedialog.asksaveasfilename(
            initialfile=f"reo_{tw}x{th}.{ext}",
            defaultextension=f".{ext}",
            filetypes=[(fmt, f"*.{ext}"), ("All", "*.*")],
        )
        if path:
            out.save(path, format="PNG" if ext == "png" else "JPEG", quality=95)
            messagebox.showinfo("reo", "Exported.")


def main():
    root = tk.Tk()
    ReoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
