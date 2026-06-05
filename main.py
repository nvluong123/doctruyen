# -*- coding: utf-8 -*-
"""
ĐỌC TRUYỆN - phiên bản Android (Kivy)
Cùng chức năng với bản máy tính:
- Mở file .txt (tự dò mã hoá)
- Cắt chương theo 2 kiểu: "Thứ 1 chương ..."  và  "chương 100 ..."
- Mục lục chương + ô tìm chương
- Đọc chương, chỉnh cỡ chữ, nền sáng/tối, chương trước/sau, nhớ vị trí đọc
- Chạm vào chữ -> chọn -> mở rộng/thu hẹp -> thay thế tên cho TOÀN bộ truyện
- Quản lý danh sách tên đã thay (gốc -> mới), xoá được; lưu riêng từng file
"""

import os
import re
import json

from kivy.app import App
from kivy.utils import platform
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.metrics import dp

ANDROID = platform == "android"

# ----- Mẫu nhận diện tiêu đề chương (giống bản PC) -----
#   "Thứ 1 chương Mở đầu"     -> số 1,   tên "Mở đầu"
#   "chương 100 Trọng quyền"  -> số 100, tên "Trọng quyền"
PATTERN = re.compile(r"(?i)^\s*(?:Thứ\s*(\d+)\s*chương|chương\s*(\d+))\b[\s:.\-]*(.*)$")
ENCODINGS = ["utf-8-sig", "utf-8", "utf-16", "cp1258", "latin-1"]

# Thư mục thường chứa file truyện trên Android
COMMON_DIRS = [
    "/storage/emulated/0/Truyen",
    "/storage/emulated/0/Download",
    "/storage/emulated/0/Documents",
    "/sdcard/Truyen",
    "/sdcard/Download",
]


def escape_markup(s):
    return (s.replace("&", "&amp;").replace("[", "&bl;").replace("]", "&br;"))


class Reader(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation="vertical", **kw)
        self.app = app
        self.chapters = []
        self.filtered = []
        self.current_file = None
        self.current_idx = None
        self.replacements = {}     # {gốc: mới} cho file hiện tại
        self.sel_start = None      # offset ký tự trong nội dung đang hiển thị
        self.sel_end = None

        self.cfg = app.load_cfg()
        self.font_size = self.cfg.get("font_size", 18)
        self.dark = self.cfg.get("dark", False)

        self._build()
        self._apply_theme()

        last = self.cfg.get("last_file")
        if last and os.path.isfile(last):
            self.load_file(last, remember=True)

    # ------------------------------------------------------------------ UI
    def _build(self):
        # Thanh trên
        top = BoxLayout(size_hint_y=None, height=dp(48), padding=dp(4), spacing=dp(4))
        top.add_widget(self._btn("Mở", self.open_picker))
        top.add_widget(self._btn("Mục lục", self.open_toc))
        top.add_widget(self._btn("A-", lambda *_: self.change_font(-2)))
        top.add_widget(self._btn("A+", lambda *_: self.change_font(2)))
        top.add_widget(self._btn("Nền", lambda *_: self.toggle_theme()))
        top.add_widget(self._btn("Tên", lambda *_: self.open_manage()))
        self.add_widget(top)

        # Tiêu đề chương
        self.title = Label(text="Chưa mở truyện", size_hint_y=None, height=dp(36),
                           bold=True, halign="left", valign="middle")
        self.title.bind(size=lambda *_: setattr(self.title, "text_size", self.title.size))
        self.add_widget(self.title)

        # Vùng đọc: ScrollView + Label markup (chạm chữ được nhờ [ref])
        self.scroll = ScrollView()
        self.body = Label(text="", markup=True, size_hint_y=None,
                          halign="left", valign="top", padding=(dp(14), dp(10)))
        self.body.bind(width=self._on_body_width, texture_size=self._on_texture)
        self.body.bind(on_ref_press=self._on_word)
        self.scroll.add_widget(self.body)
        self.add_widget(self.scroll)

        # Thanh dưới: điều hướng + lật trang
        bot = BoxLayout(size_hint_y=None, height=dp(50), padding=dp(4), spacing=dp(4))
        bot.add_widget(self._btn("◀ Trước", lambda *_: self.prev_chapter()))
        bot.add_widget(self._btn("▲", lambda *_: self.page(+1)))
        bot.add_widget(self._btn("▼", lambda *_: self.page(-1)))
        bot.add_widget(self._btn("Sau ▶", lambda *_: self.next_chapter()))
        self.add_widget(bot)

    def _btn(self, text, cb):
        b = Button(text=text, font_size=dp(15))
        b.bind(on_release=lambda *_: cb())
        return b

    def _on_body_width(self, *_):
        self.body.text_size = (self.body.width, None)

    def _on_texture(self, *_):
        self.body.height = self.body.texture_size[1]

    # ------------------------------------------------------------------ Theme
    def _apply_theme(self):
        if self.dark:
            Window.clearcolor = (0.12, 0.12, 0.12, 1)
            self.fg = (0.9, 0.9, 0.9, 1)
            self.pick = "ffd27f"
        else:
            Window.clearcolor = (0.98, 0.98, 0.96, 1)
            self.fg = (0.1, 0.1, 0.1, 1)
            self.pick = "c87800"
        self.title.color = self.fg
        self.body.color = self.fg
        self.body.font_size = dp(self.font_size)
        self.render()

    def toggle_theme(self):
        self.dark = not self.dark
        self._apply_theme()
        self.save_cfg()

    def change_font(self, d):
        self.font_size = max(10, min(40, self.font_size + d))
        self.body.font_size = dp(self.font_size)
        self.save_cfg()

    def page(self, direction):
        """Lật một màn hình (direction +1 lên, -1 xuống)."""
        if self.body.height <= 0:
            return
        step = (self.scroll.height / self.body.height) * 0.9
        self.scroll.scroll_y = max(0, min(1, self.scroll.scroll_y + direction * step))

    # ------------------------------------------------------------------ Mở file
    def open_picker(self):
        FileBrowser(self).open()

    def _read_text(self, path):
        with open(path, "rb") as f:
            data = f.read()
        for enc in ENCODINGS:
            try:
                return data.decode(enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
        return data.decode("utf-8", errors="ignore")

    def parse(self, raw):
        chapters, intro, cur = [], [], None
        for line in raw.splitlines():
            m = PATTERN.match(line)
            if m:
                if cur is not None:
                    chapters.append(cur)
                num = m.group(1) or m.group(2)
                ttl = (m.group(3) or "").strip() or f"(Chương {num})"
                cur = {"num": num, "title": ttl, "lines": []}
            else:
                (intro if cur is None else cur["lines"]).append(line)
        if cur is not None:
            chapters.append(cur)

        def clean(t):
            return "\n".join(ln.lstrip() for ln in t.splitlines()).strip()

        out = []
        intro_t = clean("\n".join(intro))
        if intro_t and not chapters:
            out.append({"num": "", "title": "Toàn văn", "content": intro_t})
        else:
            if intro_t:
                out.append({"num": "", "title": "Phần mở đầu", "content": intro_t})
            for c in chapters:
                out.append({"num": c["num"], "title": c["title"],
                            "content": clean("\n".join(c["lines"]))})
        return out

    def load_file(self, path, remember=False):
        try:
            raw = self._read_text(path)
        except Exception as e:
            self._toast(f"Không đọc được file: {e}")
            return
        self.chapters = self.parse(raw)
        if not self.chapters:
            self._toast("File rỗng / không có nội dung.")
            return
        self.current_file = path
        self.replacements = dict(self.cfg.get("rep", {}).get(path, {}))
        start = 0
        if remember:
            saved = self.cfg.get("pos", {}).get(path)
            if isinstance(saved, int) and 0 <= saved < len(self.chapters):
                start = saved
        self.show(start)
        self.save_cfg()

    # ------------------------------------------------------------------ Thay thế
    def apply_rep(self, text):
        if not text or not self.replacements:
            return text
        for k in sorted(self.replacements, key=len, reverse=True):
            if k:
                text = text.replace(k, self.replacements[k])
        return text

    # ------------------------------------------------------------------ Hiển thị
    def show(self, idx):
        if not (0 <= idx < len(self.chapters)):
            return
        self.current_idx = idx
        self.sel_start = self.sel_end = None
        c = self.chapters[idx]
        ttl = f"Chương {c['num']}: {c['title']}" if c["num"] else c["title"]
        self.title.text = self.apply_rep(ttl)
        self.render()
        self.scroll.scroll_y = 1
        self.save_pos()

    def _content(self):
        if self.current_idx is None:
            return ""
        return self.apply_rep(self.chapters[self.current_idx]["content"]) or "(trống)"

    def render(self):
        """Vẽ nội dung; bọc mỗi từ bằng [ref] để chạm chọn, tô vùng đang chọn."""
        text = self._content()
        if not self.chapters:
            self.body.text = "Bấm [b]Mở[/b] để chọn file truyện .txt"
            return
        a, b = self.sel_start, self.sel_end
        if a is None or b is None or a >= b:
            self.body.text = self._tokenize(text, 0, len(text))
        else:
            mid = "[color=%s][b]%s[/b][/color]" % (self.pick, escape_markup(text[a:b]))
            self.body.text = (self._tokenize(text, 0, a) + mid +
                              self._tokenize(text, b, len(text)))

    def _tokenize(self, text, start, end):
        """Bọc từng từ [start,end) thành ref theo vị trí ký tự tuyệt đối."""
        parts = []
        i = start
        seg = text[start:end]
        for m in re.finditer(r"\S+|\s+", seg):
            tok = m.group(0)
            abs_i = start + m.start()
            if tok.strip():
                parts.append("[ref=%d_%d]%s[/ref]" % (abs_i, abs_i + len(tok), escape_markup(tok)))
            else:
                parts.append(escape_markup(tok))
        return "".join(parts)

    def _on_word(self, instance, ref):
        try:
            i, j = ref.split("_")
            self.sel_start, self.sel_end = int(i), int(j)
        except Exception:
            return
        self.render()
        ReplacePopup(self).open()

    # mở rộng / thu hẹp vùng chọn (mỗi lần 1 ký tự)
    def expand_left(self):
        if self.sel_start is not None and self.sel_start > 0:
            self.sel_start -= 1
            self.render()

    def expand_right(self):
        if self.sel_end is not None and self.sel_end < len(self._content()):
            self.sel_end += 1
            self.render()

    def shrink_left(self):
        if self.sel_start is not None and self.sel_start + 1 < self.sel_end:
            self.sel_start += 1
            self.render()

    def shrink_right(self):
        if self.sel_end is not None and self.sel_end - 1 > self.sel_start:
            self.sel_end -= 1
            self.render()

    def selected(self):
        if self.sel_start is None or self.sel_end is None:
            return ""
        return self._content()[self.sel_start:self.sel_end]

    def do_replace(self, repl):
        orig = self.selected().strip()
        if not orig:
            self._toast("Chưa chọn chữ.")
            return False
        if not repl.strip():
            self._toast("Hãy nhập tên thay thế.")
            return False
        self.replacements[orig] = repl.strip()
        self.save_cfg()
        self.sel_start = self.sel_end = None
        if self.current_idx is not None:
            self.show(self.current_idx)
        self._toast(f"Đã thay '{orig}' → '{repl.strip()}'")
        return True

    def delete_rep(self, key):
        self.replacements.pop(key, None)
        self.save_cfg()
        if self.current_idx is not None:
            self.show(self.current_idx)

    # ------------------------------------------------------------------ Điều hướng
    def prev_chapter(self):
        if self.current_idx and self.current_idx > 0:
            self.show(self.current_idx - 1)

    def next_chapter(self):
        if self.current_idx is not None and self.current_idx < len(self.chapters) - 1:
            self.show(self.current_idx + 1)

    def open_toc(self):
        if not self.chapters:
            self._toast("Chưa mở truyện.")
            return
        TocPopup(self).open()

    def open_manage(self):
        ManagePopup(self).open()

    # ------------------------------------------------------------------ Lưu / báo
    def save_cfg(self):
        if self.current_file:
            self.cfg.setdefault("rep", {})[self.current_file] = self.replacements
        self.cfg["font_size"] = self.font_size
        self.cfg["dark"] = self.dark
        self.cfg["last_file"] = self.current_file
        self.app.save_cfg(self.cfg)

    def save_pos(self):
        if self.current_file and self.current_idx is not None:
            self.cfg.setdefault("pos", {})[self.current_file] = self.current_idx
            self.app.save_cfg(self.cfg)

    def _toast(self, msg):
        p = Popup(title="Thông báo", size_hint=(0.8, 0.3),
                  content=Label(text=msg, halign="center"))
        p.open()
        from kivy.clock import Clock
        Clock.schedule_once(lambda *_: p.dismiss(), 1.6)


# ============================================================ Các popup
class FileBrowser(Popup):
    def __init__(self, reader, **kw):
        self.reader = reader
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        self.path = self._first_dir()
        self.lbl = Label(text=self.path, size_hint_y=None, height=dp(28),
                         halign="left", valign="middle")
        self.lbl.bind(size=lambda *_: setattr(self.lbl, "text_size", self.lbl.size))
        box.add_widget(self.lbl)

        quick = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        for d in COMMON_DIRS:
            if os.path.isdir(d):
                name = os.path.basename(d) or d
                bb = Button(text=name, font_size=dp(12))
                bb.bind(on_release=lambda inst, dd=d: self.goto(dd))
                quick.add_widget(bb)
        box.add_widget(quick)

        self.sv = ScrollView()
        self.list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2))
        self.list.bind(minimum_height=self.list.setter("height"))
        self.sv.add_widget(self.list)
        box.add_widget(self.sv)

        box.add_widget(Button(text="Đóng", size_hint_y=None, height=dp(40),
                              on_release=lambda *_: self.dismiss()))
        super().__init__(title="Chọn file truyện (.txt)", content=box,
                         size_hint=(0.95, 0.95), **kw)
        self.refresh()

    def _first_dir(self):
        for d in COMMON_DIRS:
            if os.path.isdir(d):
                return d
        return "/storage/emulated/0" if os.path.isdir("/storage/emulated/0") else os.path.expanduser("~")

    def goto(self, path):
        if os.path.isdir(path):
            self.path = path
            self.refresh()

    def refresh(self):
        self.lbl.text = self.path
        self.list.clear_widgets()
        # nút lên thư mục cha
        parent = os.path.dirname(self.path.rstrip("/"))
        if parent and parent != self.path:
            self._row(".. (lên trên)", lambda *_: self.goto(parent), "#888888")
        try:
            entries = sorted(os.listdir(self.path))
        except Exception as e:
            self._row(f"[lỗi] {e}", lambda *_: None)
            return
        for name in entries:
            full = os.path.join(self.path, name)
            if os.path.isdir(full):
                self._row("📁 " + name, lambda inst, f=full: self.goto(f))
        for name in entries:
            full = os.path.join(self.path, name)
            if os.path.isfile(full) and name.lower().endswith(".txt"):
                self._row("📄 " + name, lambda inst, f=full: self.choose(f))

    def _row(self, text, cb, color=None):
        b = Button(text=text, size_hint_y=None, height=dp(44),
                   halign="left", valign="middle", font_size=dp(14))
        b.bind(size=lambda *_: setattr(b, "text_size", (b.width - dp(10), b.height)))
        b.bind(on_release=cb)
        self.list.add_widget(b)

    def choose(self, full):
        self.dismiss()
        self.reader.load_file(full)


class TocPopup(Popup):
    def __init__(self, reader, **kw):
        self.reader = reader
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        self.search = TextInput(hint_text="Tìm chương...", multiline=False,
                                size_hint_y=None, height=dp(40))
        self.search.bind(text=lambda *_: self.refresh())
        box.add_widget(self.search)

        sv = ScrollView()
        self.list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2))
        self.list.bind(minimum_height=self.list.setter("height"))
        sv.add_widget(self.list)
        box.add_widget(sv)

        box.add_widget(Button(text="Đóng", size_hint_y=None, height=dp(40),
                              on_release=lambda *_: self.dismiss()))
        super().__init__(title="Mục lục", content=box, size_hint=(0.95, 0.95), **kw)
        self.refresh()

    def refresh(self):
        kw = self.search.text.strip().lower()
        self.list.clear_widgets()
        for i, c in enumerate(self.reader.chapters):
            label = f"Chương {c['num']}: {c['title']}" if c["num"] else c["title"]
            label = self.reader.apply_rep(label)
            if kw and kw not in label.lower():
                continue
            b = Button(text=label, size_hint_y=None, height=dp(44),
                       halign="left", valign="middle", font_size=dp(14))
            b.bind(size=lambda inst, *_: setattr(inst, "text_size", (inst.width - dp(10), inst.height)))
            b.bind(on_release=lambda inst, idx=i: self.pick(idx))
            self.list.add_widget(b)

    def pick(self, idx):
        self.dismiss()
        self.reader.show(idx)


class ReplacePopup(Popup):
    def __init__(self, reader, **kw):
        self.reader = reader
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        self.sel_lbl = Label(text="", size_hint_y=None, height=dp(36))
        box.add_widget(Label(text="Chữ đang chọn:", size_hint_y=None, height=dp(24)))
        box.add_widget(self.sel_lbl)

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
        row.add_widget(self._b("◀ Rộng", reader.expand_left))
        row.add_widget(self._b("Hẹp ▶", reader.shrink_left))
        row.add_widget(self._b("◀ Hẹp", reader.shrink_right))
        row.add_widget(self._b("Rộng ▶", reader.expand_right))
        box.add_widget(row)

        box.add_widget(Label(text="Thay bằng tên:", size_hint_y=None, height=dp(24)))
        self.inp = TextInput(multiline=False, size_hint_y=None, height=dp(44))
        box.add_widget(self.inp)

        act = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        act.add_widget(Button(text="✔ Áp dụng", on_release=lambda *_: self.apply()))
        act.add_widget(Button(text="Quản lý", on_release=lambda *_: self.manage()))
        act.add_widget(Button(text="Đóng", on_release=lambda *_: self.dismiss()))
        box.add_widget(act)

        super().__init__(title="Thay thế tên", content=box,
                         size_hint=(0.95, None), height=dp(360), **kw)
        self.refresh()

    def _b(self, text, fn):
        b = Button(text=text, font_size=dp(13))
        b.bind(on_release=lambda *_: (fn(), self.refresh()))
        return b

    def refresh(self):
        sel = self.reader.selected()
        self.sel_lbl.text = sel
        if sel in self.reader.replacements and not self.inp.text:
            self.inp.text = self.reader.replacements[sel]

    def apply(self):
        if self.reader.do_replace(self.inp.text):
            self.dismiss()

    def manage(self):
        self.dismiss()
        ManagePopup(self.reader).open()


class ManagePopup(Popup):
    def __init__(self, reader, **kw):
        self.reader = reader
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        box.add_widget(Label(text="Tên đã thay (gốc → mới):",
                             size_hint_y=None, height=dp(26)))
        sv = ScrollView()
        self.list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2))
        self.list.bind(minimum_height=self.list.setter("height"))
        sv.add_widget(self.list)
        box.add_widget(sv)
        box.add_widget(Button(text="Đóng", size_hint_y=None, height=dp(40),
                              on_release=lambda *_: self.dismiss()))
        super().__init__(title="Quản lý tên", content=box, size_hint=(0.95, 0.9), **kw)
        self.refresh()

    def refresh(self):
        self.list.clear_widgets()
        if not self.reader.replacements:
            self.list.add_widget(Label(text="(Chưa có name nào)",
                                       size_hint_y=None, height=dp(40)))
            return
        for k, v in list(self.reader.replacements.items()):
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
            lab = Button(text=f"{k}  →  {v}", halign="left", valign="middle",
                         font_size=dp(14), background_normal="")
            lab.bind(size=lambda inst, *_: setattr(inst, "text_size", (inst.width - dp(8), inst.height)))
            row.add_widget(lab)
            d = Button(text="🗑", size_hint_x=None, width=dp(50))
            d.bind(on_release=lambda inst, key=k: self._del(key))
            row.add_widget(d)
            self.list.add_widget(row)

    def _del(self, key):
        self.reader.delete_rep(key)
        self.refresh()


# ============================================================ App
class DocTruyenApp(App):
    def build(self):
        self.title = "Đọc Truyện"
        if ANDROID:
            self._request_perms()
        return Reader(self)

    def _request_perms(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ])
        except Exception:
            pass

    @property
    def cfg_path(self):
        return os.path.join(self.user_data_dir, "doc_truyen_cfg.json")

    def load_cfg(self):
        try:
            with open(self.cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_cfg(self, cfg):
        try:
            with open(self.cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


if __name__ == "__main__":
    DocTruyenApp().run()
