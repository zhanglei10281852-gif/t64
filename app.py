import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import csv
import calendar
from datetime import datetime, date
from tkinter import simpledialog


CATEGORY_CONVERSION_RATE = {
    "美妆": 0.08,
    "食品": 0.12,
    "服饰": 0.06,
    "家居": 0.05,
    "数码": 0.03,
}

DISCOUNT_FACTOR = 1.2

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BROADCASTERS_FILE = os.path.join(DATA_DIR, "broadcasters.json")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
SCHEDULES_FILE = os.path.join(DATA_DIR, "schedules.json")


def load_json(filepath, default=None):
    if default is None:
        default = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_id(prefix, items):
    if not items:
        return f"{prefix}001"
    max_num = 0
    for item in items:
        try:
            num = int(item["id"].replace(prefix, ""))
            if num > max_num:
                max_num = num
        except (ValueError, KeyError):
            pass
    return f"{prefix}{max_num + 1:03d}"


class DataManager:
    def __init__(self):
        self.broadcasters = load_json(BROADCASTERS_FILE, [])
        self.products = load_json(PRODUCTS_FILE, [])
        self.schedules = load_json(SCHEDULES_FILE, [])

    def save_all(self):
        save_json(BROADCASTERS_FILE, self.broadcasters)
        save_json(PRODUCTS_FILE, self.products)
        save_json(SCHEDULES_FILE, self.schedules)

    def get_broadcaster_by_id(self, bid):
        for b in self.broadcasters:
            if b["id"] == bid:
                return b
        return None

    def get_product_by_id(self, pid):
        for p in self.products:
            if p["id"] == pid:
                return p
        return None

    def get_schedules_by_date(self, date_str):
        return [s for s in self.schedules if s["date"] == date_str]

    def get_schedules_by_month(self, year, month):
        prefix = f"{year:04d}-{month:02d}"
        return [s for s in self.schedules if s["date"].startswith(prefix)]


class BroadcasterTab(ttk.Frame):
    def __init__(self, parent, data_manager, on_data_change):
        super().__init__(parent)
        self.data_manager = data_manager
        self.on_data_change = on_data_change
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=10, pady=8)

        ttk.Button(toolbar, text="新增主播", command=self.add_item).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="编辑选中", command=self.edit_item).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="删除选中", command=self.delete_item).pack(side=tk.LEFT, padx=4)

        columns = ("id", "name", "fans_count", "category", "base_fee", "commission_rate", "max_products")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")

        headings = [
            ("id", "ID", 60),
            ("name", "主播名称", 120),
            ("fans_count", "粉丝数", 100),
            ("category", "品类标签", 100),
            ("base_fee", "坑位费(元)", 100),
            ("commission_rate", "佣金比例(%)", 100),
            ("max_products", "每场最大上品数", 120),
        ]
        for col, text, width in headings:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=5)

        self.tree.bind("<Double-1>", lambda e: self.edit_item())

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for b in self.data_manager.broadcasters:
            fans = f"{b['fans_count']:,}"
            self.tree.insert(
                "", tk.END,
                values=(b["id"], b["name"], fans, b["category"],
                        f"{b['base_fee']:,}", b["commission_rate"], b["max_products"])
            )

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一行")
            return None
        return self.tree.item(sel[0], "values")[0]

    def add_item(self):
        dlg = BroadcasterDialog(self, title="新增主播")
        self.wait_window(dlg)
        if dlg.result:
            new_id = generate_id("b", self.data_manager.broadcasters)
            dlg.result["id"] = new_id
            self.data_manager.broadcasters.append(dlg.result)
            self.refresh()
            self.on_data_change()

    def edit_item(self):
        bid = self._get_selected_id()
        if not bid:
            return
        broadcaster = self.data_manager.get_broadcaster_by_id(bid)
        if not broadcaster:
            return
        dlg = BroadcasterDialog(self, title="编辑主播", data=broadcaster)
        self.wait_window(dlg)
        if dlg.result:
            for i, b in enumerate(self.data_manager.broadcasters):
                if b["id"] == bid:
                    dlg.result["id"] = bid
                    self.data_manager.broadcasters[i] = dlg.result
                    break
            self.refresh()
            self.on_data_change()

    def delete_item(self):
        bid = self._get_selected_id()
        if not bid:
            return
        if not messagebox.askyesno("确认", "确定要删除该主播吗？"):
            return
        self.data_manager.broadcasters = [
            b for b in self.data_manager.broadcasters if b["id"] != bid
        ]
        self.refresh()
        self.on_data_change()


class BroadcasterDialog(tk.Toplevel):
    def __init__(self, parent, title="", data=None):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.resizable(False, False)
        self.grab_set()

        self._build_widgets(data)

        self.transient(parent)
        self.geometry(f"+{parent.winfo_rootx()+100}+{parent.winfo_rooty()+100}")

    def _build_widgets(self, data):
        frm = ttk.Frame(self, padding=20)
        frm.pack()

        ttk.Label(frm, text="主播名称:").grid(row=0, column=0, sticky=tk.E, pady=6)
        self.name_var = tk.StringVar(value=data["name"] if data else "")
        ttk.Entry(frm, textvariable=self.name_var, width=25).grid(row=0, column=1, pady=6)

        ttk.Label(frm, text="粉丝数:").grid(row=1, column=0, sticky=tk.E, pady=6)
        self.fans_var = tk.StringVar(value=str(data["fans_count"]) if data else "")
        ttk.Entry(frm, textvariable=self.fans_var, width=25).grid(row=1, column=1, pady=6)

        ttk.Label(frm, text="品类标签:").grid(row=2, column=0, sticky=tk.E, pady=6)
        self.category_var = tk.StringVar(value=data["category"] if data else "美妆")
        categories = ["美妆", "食品", "服饰", "家居", "数码"]
        ttk.Combobox(frm, textvariable=self.category_var, values=categories,
                     state="readonly", width=23).grid(row=2, column=1, pady=6)

        ttk.Label(frm, text="坑位费(元):").grid(row=3, column=0, sticky=tk.E, pady=6)
        self.base_fee_var = tk.StringVar(value=str(data["base_fee"]) if data else "")
        ttk.Entry(frm, textvariable=self.base_fee_var, width=25).grid(row=3, column=1, pady=6)

        ttk.Label(frm, text="佣金比例(%):").grid(row=4, column=0, sticky=tk.E, pady=6)
        self.commission_var = tk.StringVar(value=str(data["commission_rate"]) if data else "")
        ttk.Entry(frm, textvariable=self.commission_var, width=25).grid(row=4, column=1, pady=6)

        ttk.Label(frm, text="每场最大上品数:").grid(row=5, column=0, sticky=tk.E, pady=6)
        self.max_prod_var = tk.StringVar(value=str(data["max_products"]) if data else "")
        ttk.Entry(frm, textvariable=self.max_prod_var, width=25).grid(row=5, column=1, pady=6)

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(btn_frame, text="确定", command=self._on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT, padx=10)

    def _on_ok(self):
        try:
            name = self.name_var.get().strip()
            if not name:
                raise ValueError("主播名称不能为空")
            fans = int(self.fans_var.get())
            if fans < 0:
                raise ValueError("粉丝数不能为负数")
            base_fee = int(self.base_fee_var.get())
            if base_fee < 0:
                raise ValueError("坑位费不能为负数")
            commission = float(self.commission_var.get())
            if commission < 0 or commission > 100:
                raise ValueError("佣金比例应在0-100之间")
            max_prod = int(self.max_prod_var.get())
            if max_prod <= 0:
                raise ValueError("最大上品数必须大于0")

            self.result = {
                "name": name,
                "fans_count": fans,
                "category": self.category_var.get(),
                "base_fee": base_fee,
                "commission_rate": commission,
                "max_products": max_prod,
            }
            self.destroy()
        except ValueError as e:
            messagebox.showerror("输入错误", str(e))


class ProductTab(ttk.Frame):
    def __init__(self, parent, data_manager, on_data_change):
        super().__init__(parent)
        self.data_manager = data_manager
        self.on_data_change = on_data_change
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=10, pady=8)

        ttk.Button(toolbar, text="新增商品", command=self.add_item).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="编辑选中", command=self.edit_item).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="删除选中", command=self.delete_item).pack(side=tk.LEFT, padx=4)

        columns = ("id", "name", "brand", "category", "supply_price",
                   "live_price", "commission_rate", "stock")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")

        headings = [
            ("id", "ID", 60),
            ("name", "商品名", 160),
            ("brand", "品牌", 100),
            ("category", "品类", 80),
            ("supply_price", "供货价", 80),
            ("live_price", "直播价", 80),
            ("commission_rate", "佣金(%)", 80),
            ("stock", "库存", 80),
        ]
        for col, text, width in headings:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=5)

        self.tree.bind("<Double-1>", lambda e: self.edit_item())

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for p in self.data_manager.products:
            self.tree.insert(
                "", tk.END,
                values=(p["id"], p["name"], p["brand"], p["category"],
                        p["supply_price"], p["live_price"],
                        p["commission_rate"], p["stock"])
            )

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一行")
            return None
        return self.tree.item(sel[0], "values")[0]

    def add_item(self):
        dlg = ProductDialog(self, title="新增商品")
        self.wait_window(dlg)
        if dlg.result:
            new_id = generate_id("p", self.data_manager.products)
            dlg.result["id"] = new_id
            self.data_manager.products.append(dlg.result)
            self.refresh()
            self.on_data_change()

    def edit_item(self):
        pid = self._get_selected_id()
        if not pid:
            return
        product = self.data_manager.get_product_by_id(pid)
        if not product:
            return
        dlg = ProductDialog(self, title="编辑商品", data=product)
        self.wait_window(dlg)
        if dlg.result:
            for i, p in enumerate(self.data_manager.products):
                if p["id"] == pid:
                    dlg.result["id"] = pid
                    self.data_manager.products[i] = dlg.result
                    break
            self.refresh()
            self.on_data_change()

    def delete_item(self):
        pid = self._get_selected_id()
        if not pid:
            return
        if not messagebox.askyesno("确认", "确定要删除该商品吗？"):
            return
        self.data_manager.products = [
            p for p in self.data_manager.products if p["id"] != pid
        ]
        self.refresh()
        self.on_data_change()


class ProductDialog(tk.Toplevel):
    def __init__(self, parent, title="", data=None):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.resizable(False, False)
        self.grab_set()

        self._build_widgets(data)
        self.transient(parent)
        self.geometry(f"+{parent.winfo_rootx()+100}+{parent.winfo_rooty()+100}")

    def _build_widgets(self, data):
        frm = ttk.Frame(self, padding=20)
        frm.pack()

        ttk.Label(frm, text="商品名:").grid(row=0, column=0, sticky=tk.E, pady=5)
        self.name_var = tk.StringVar(value=data["name"] if data else "")
        ttk.Entry(frm, textvariable=self.name_var, width=25).grid(row=0, column=1, pady=5)

        ttk.Label(frm, text="品牌:").grid(row=1, column=0, sticky=tk.E, pady=5)
        self.brand_var = tk.StringVar(value=data["brand"] if data else "")
        ttk.Entry(frm, textvariable=self.brand_var, width=25).grid(row=1, column=1, pady=5)

        ttk.Label(frm, text="品类:").grid(row=2, column=0, sticky=tk.E, pady=5)
        self.category_var = tk.StringVar(value=data["category"] if data else "美妆")
        categories = ["美妆", "食品", "服饰", "家居", "数码"]
        ttk.Combobox(frm, textvariable=self.category_var, values=categories,
                     state="readonly", width=23).grid(row=2, column=1, pady=5)

        ttk.Label(frm, text="供货价:").grid(row=3, column=0, sticky=tk.E, pady=5)
        self.supply_var = tk.StringVar(value=str(data["supply_price"]) if data else "")
        ttk.Entry(frm, textvariable=self.supply_var, width=25).grid(row=3, column=1, pady=5)

        ttk.Label(frm, text="直播价:").grid(row=4, column=0, sticky=tk.E, pady=5)
        self.live_var = tk.StringVar(value=str(data["live_price"]) if data else "")
        ttk.Entry(frm, textvariable=self.live_var, width=25).grid(row=4, column=1, pady=5)

        ttk.Label(frm, text="佣金比例(%):").grid(row=5, column=0, sticky=tk.E, pady=5)
        self.commission_var = tk.StringVar(value=str(data["commission_rate"]) if data else "")
        ttk.Entry(frm, textvariable=self.commission_var, width=25).grid(row=5, column=1, pady=5)

        ttk.Label(frm, text="库存:").grid(row=6, column=0, sticky=tk.E, pady=5)
        self.stock_var = tk.StringVar(value=str(data["stock"]) if data else "")
        ttk.Entry(frm, textvariable=self.stock_var, width=25).grid(row=6, column=1, pady=5)

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(btn_frame, text="确定", command=self._on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT, padx=10)

    def _on_ok(self):
        try:
            name = self.name_var.get().strip()
            if not name:
                raise ValueError("商品名不能为空")
            brand = self.brand_var.get().strip()
            if not brand:
                raise ValueError("品牌不能为空")
            supply = float(self.supply_var.get())
            if supply < 0:
                raise ValueError("供货价不能为负")
            live = float(self.live_var.get())
            if live < 0:
                raise ValueError("直播价不能为负")
            commission = float(self.commission_var.get())
            if commission < 0 or commission > 100:
                raise ValueError("佣金比例应在0-100之间")
            stock = int(self.stock_var.get())
            if stock < 0:
                raise ValueError("库存不能为负")

            self.result = {
                "name": name,
                "brand": brand,
                "category": self.category_var.get(),
                "supply_price": supply,
                "live_price": live,
                "commission_rate": commission,
                "stock": stock,
            }
            self.destroy()
        except ValueError as e:
            messagebox.showerror("输入错误", str(e))


class CalendarTab(ttk.Frame):
    def __init__(self, parent, data_manager, on_data_change):
        super().__init__(parent)
        self.data_manager = data_manager
        self.on_data_change = on_data_change

        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.day_cells = {}

        self._build_ui()
        self._render_calendar()

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(top, text="◀ 上月", command=self.prev_month).pack(side=tk.LEFT)
        self.month_label = ttk.Label(top, text="", font=("Arial", 14, "bold"))
        self.month_label.pack(side=tk.LEFT, expand=True)
        ttk.Button(top, text="下月 ▶", command=self.next_month).pack(side=tk.RIGHT)

        calendar_frame = ttk.Frame(self, relief=tk.SUNKEN, borderwidth=1)
        calendar_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        weekdays = ["日", "一", "二", "三", "四", "五", "六"]
        for i, wd in enumerate(weekdays):
            lbl = ttk.Label(calendar_frame, text=wd, anchor=tk.CENTER,
                            font=("Arial", 10, "bold"),
                            background="#e0e0e0")
            lbl.grid(row=0, column=i, sticky="nsew", padx=1, pady=1)

        self.cells_frame = ttk.Frame(calendar_frame)
        self.cells_frame.grid(row=1, column=0, columnspan=7, sticky="nsew")

        for i in range(7):
            calendar_frame.grid_columnconfigure(i, weight=1)
        calendar_frame.grid_rowconfigure(1, weight=1)

        legend = ttk.Frame(self)
        legend.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(legend, text="■ 有排期的日期", foreground="#4a90d9").pack(side=tk.LEFT)
        ttk.Label(legend, text="  (双击日期可编辑排期)").pack(side=tk.LEFT)

    def _render_calendar(self):
        for widget in self.cells_frame.winfo_children():
            widget.destroy()
        self.day_cells = {}

        self.month_label.config(text=f"{self.current_year}年{self.current_month}月")

        cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
        weeks = cal.monthdayscalendar(self.current_year, self.current_month)

        for row_idx, week in enumerate(weeks):
            for col_idx, day in enumerate(week):
                cell = tk.Frame(self.cells_frame, bg="white",
                                highlightbackground="#cccccc",
                                highlightthickness=1)
                cell.grid(row=row_idx, column=col_idx, sticky="nsew", padx=1, pady=1)
                self.cells_frame.grid_rowconfigure(row_idx, weight=1)
                self.cells_frame.grid_columnconfigure(col_idx, weight=1)

                if day == 0:
                    cell.config(bg="#f5f5f5")
                else:
                    date_str = f"{self.current_year:04d}-{self.current_month:02d}-{day:02d}"
                    day_label = tk.Label(cell, text=str(day), bg="white",
                                         anchor=tk.NW, padx=5, pady=3)
                    day_label.pack(fill=tk.X)

                    info_label = tk.Label(cell, text="", bg="white",
                                          anchor=tk.NW, justify=tk.LEFT,
                                          padx=5, wraplength=80)
                    info_label.pack(fill=tk.BOTH, expand=True)

                    schedules = self.data_manager.get_schedules_by_date(date_str)
                    if schedules:
                        cell.config(bg="#d6e8f7")
                        day_label.config(bg="#d6e8f7")
                        info_label.config(bg="#d6e8f7")
                        info_text = []
                        for s in schedules:
                            bc = self.data_manager.get_broadcaster_by_id(s["broadcaster_id"])
                            bc_name = bc["name"] if bc else "未知"
                            info_text.append(f"{s['time']} {bc_name}")
                        info_label.config(text="\n".join(info_text))

                    cell.bind("<Double-Button-1>", lambda e, d=day: self._edit_day(d))
                    day_label.bind("<Double-Button-1>", lambda e, d=day: self._edit_day(d))
                    info_label.bind("<Double-Button-1>", lambda e, d=day: self._edit_day(d))

                    self.day_cells[day] = {
                        "cell": cell, "day_label": day_label, "info_label": info_label
                    }

    def prev_month(self):
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self._render_calendar()

    def next_month(self):
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self._render_calendar()

    def _edit_day(self, day):
        date_str = f"{self.current_year:04d}-{self.current_month:02d}-{day:02d}"
        dlg = ScheduleDayDialog(self, date_str, self.data_manager)
        self.wait_window(dlg)
        if dlg.modified:
            self._render_calendar()
            self.on_data_change()


class ScheduleDayDialog(tk.Toplevel):
    def __init__(self, parent, date_str, data_manager):
        super().__init__(parent)
        self.title(f"排期编辑 - {date_str}")
        self.date_str = date_str
        self.data_manager = data_manager
        self.modified = False
        self.grab_set()

        self.geometry("520x500")
        self._build_ui()
        self._load_schedules()

        self.transient(parent)
        self.geometry(f"+{parent.winfo_rootx()+80}+{parent.winfo_rooty()+50}")

    def _build_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text=f"日期: {self.date_str}", font=("Arial", 11, "bold")).pack(anchor=tk.W)

        list_frame = ttk.LabelFrame(main, text="当日排期")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=8)

        self.schedule_list = tk.Listbox(list_frame, height=6)
        self.schedule_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.schedule_list.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.schedule_list.config(yscrollcommand=sb.set)

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="新增场次", command=self._add_schedule).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="编辑场次", command=self._edit_schedule).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="删除场次", command=self._delete_schedule).pack(side=tk.LEFT, padx=3)

        ttk.Button(main, text="关闭", command=self.destroy).pack(pady=10)

    def _load_schedules(self):
        self.schedule_list.delete(0, tk.END)
        schedules = self.data_manager.get_schedules_by_date(self.date_str)
        for s in schedules:
            bc = self.data_manager.get_broadcaster_by_id(s["broadcaster_id"])
            bc_name = bc["name"] if bc else "未知主播"
            prod_count = len(s["product_ids"])
            text = f"{s['time']} - {bc_name} ({prod_count}个商品)"
            self.schedule_list.insert(tk.END, text)

    def _get_selected_schedule(self):
        sel = self.schedule_list.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个场次")
            return None
        schedules = self.data_manager.get_schedules_by_date(self.date_str)
        return schedules[sel[0]]

    def _add_schedule(self):
        dlg = ScheduleEditDialog(self, self.data_manager, date_str=self.date_str)
        self.wait_window(dlg)
        if dlg.result:
            new_id = generate_id("s", self.data_manager.schedules)
            dlg.result["id"] = new_id
            dlg.result["date"] = self.date_str
            self.data_manager.schedules.append(dlg.result)
            self._load_schedules()
            self.modified = True

    def _edit_schedule(self):
        sched = self._get_selected_schedule()
        if not sched:
            return
        dlg = ScheduleEditDialog(self, self.data_manager, schedule=sched)
        self.wait_window(dlg)
        if dlg.result:
            for i, s in enumerate(self.data_manager.schedules):
                if s["id"] == sched["id"]:
                    dlg.result["id"] = sched["id"]
                    dlg.result["date"] = self.date_str
                    self.data_manager.schedules[i] = dlg.result
                    break
            self._load_schedules()
            self.modified = True

    def _delete_schedule(self):
        sched = self._get_selected_schedule()
        if not sched:
            return
        if not messagebox.askyesno("确认", "确定要删除该场次吗？"):
            return
        self.data_manager.schedules = [
            s for s in self.data_manager.schedules if s["id"] != sched["id"]
        ]
        self._load_schedules()
        self.modified = True


class ScheduleEditDialog(tk.Toplevel):
    def __init__(self, parent, data_manager, date_str="", schedule=None):
        super().__init__(parent)
        self.title("场次编辑")
        self.data_manager = data_manager
        self.result = None
        self.grab_set()
        self.geometry("460x520")
        self.resizable(False, False)

        self._build_ui()
        if schedule:
            self._load_schedule(schedule)

        self.transient(parent)

    def _build_ui(self):
        frm = ttk.Frame(self, padding=15)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="主播:").grid(row=0, column=0, sticky=tk.E, pady=6)
        self.broadcaster_var = tk.StringVar()
        self.broadcaster_names = [
            f"{b['name']} ({b['category']}, 上限{b['max_products']}品)"
            for b in self.data_manager.broadcasters
        ]
        self.broadcaster_map = {
            f"{b['name']} ({b['category']}, 上限{b['max_products']}品)": b["id"]
            for b in self.data_manager.broadcasters
        }
        self.broadcaster_combo = ttk.Combobox(
            frm, textvariable=self.broadcaster_var,
            values=self.broadcaster_names, state="readonly", width=35
        )
        self.broadcaster_combo.grid(row=0, column=1, pady=6, sticky=tk.W)
        self.broadcaster_combo.bind("<<ComboboxSelected>>", self._on_bc_change)

        ttk.Label(frm, text="时段:").grid(row=1, column=0, sticky=tk.E, pady=6)
        time_frame = ttk.Frame(frm)
        time_frame.grid(row=1, column=1, sticky=tk.W, pady=6)
        self.hour_var = tk.StringVar(value="19")
        self.minute_var = tk.StringVar(value="00")
        ttk.Spinbox(time_frame, from_=0, to=23, width=5, textvariable=self.hour_var,
                    format="%02.0f").pack(side=tk.LEFT)
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        ttk.Spinbox(time_frame, from_=0, to=59, width=5, textvariable=self.minute_var,
                    format="%02.0f").pack(side=tk.LEFT)

        ttk.Label(frm, text="场均观看:").grid(row=2, column=0, sticky=tk.E, pady=6)
        self.viewers_var = tk.StringVar(value="50000")
        ttk.Entry(frm, textvariable=self.viewers_var, width=20).grid(row=2, column=1, sticky=tk.W, pady=6)

        ttk.Label(frm, text="本场商品:").grid(row=3, column=0, sticky=tk.NE, pady=6)

        prod_frame = ttk.Frame(frm)
        prod_frame.grid(row=3, column=1, sticky="nsew", pady=6)

        self.product_listbox = tk.Listbox(prod_frame, selectmode=tk.MULTIPLE, height=12, width=45)
        self.product_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        psb = ttk.Scrollbar(prod_frame, orient=tk.VERTICAL, command=self.product_listbox.yview)
        psb.pack(side=tk.RIGHT, fill=tk.Y)
        self.product_listbox.config(yscrollcommand=psb.set)

        self._product_items = []
        for p in self.data_manager.products:
            text = f"{p['id']} - {p['name']} ({p['brand']}, {p['category']})"
            self._product_items.append((p["id"], text))
            self.product_listbox.insert(tk.END, text)

        self.count_label = ttk.Label(frm, text="已选: 0 / 0 (上限)")
        self.count_label.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=4)
        self.product_listbox.bind("<<ListboxSelect>>", self._on_product_select)

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(btn_frame, text="确定", command=self._on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT, padx=10)

        if self.broadcaster_names and not self.broadcaster_var.get():
            self.broadcaster_var.set(self.broadcaster_names[0])
        self._on_bc_change(None)

    def _load_schedule(self, schedule):
        bc = self.data_manager.get_broadcaster_by_id(schedule["broadcaster_id"])
        if bc:
            key = f"{bc['name']} ({bc['category']}, 上限{bc['max_products']}品)"
            self.broadcaster_var.set(key)

        hour, minute = schedule["time"].split(":")
        self.hour_var.set(hour)
        self.minute_var.set(minute)

        self.viewers_var.set(str(schedule.get("avg_viewers", 50000)))

        for i, (pid, _) in enumerate(self._product_items):
            if pid in schedule["product_ids"]:
                self.product_listbox.selection_set(i)

        self._on_bc_change(None)

    def _on_bc_change(self, event):
        bc_name = self.broadcaster_var.get()
        if bc_name and bc_name in self.broadcaster_map:
            bid = self.broadcaster_map[bc_name]
            bc = self.data_manager.get_broadcaster_by_id(bid)
            if bc:
                self.max_products = bc["max_products"]
                self._update_count_label()
                return
        self.max_products = 0
        self._update_count_label()

    def _on_product_select(self, event):
        self._update_count_label()

    def _update_count_label(self):
        selected = len(self.product_listbox.curselection())
        limit = self.max_products if hasattr(self, 'max_products') else 0
        self.count_label.config(text=f"已选: {selected} / {limit} (上限)")

    def _on_ok(self):
        try:
            if not self.broadcaster_var.get():
                raise ValueError("请选择主播")

            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("时间格式不正确")
            time_str = f"{hour:02d}:{minute:02d}"

            viewers = int(self.viewers_var.get())
            if viewers < 0:
                raise ValueError("场均观看不能为负")

            selected_indices = self.product_listbox.curselection()
            product_ids = [self._product_items[i][0] for i in selected_indices]

            bc_name = self.broadcaster_var.get()
            bid = self.broadcaster_map[bc_name]
            bc = self.data_manager.get_broadcaster_by_id(bid)

            if len(product_ids) > bc["max_products"]:
                raise ValueError(
                    f"商品数量({len(product_ids)})超过主播上限({bc['max_products']})"
                )
            if len(product_ids) == 0:
                raise ValueError("请至少选择一个商品")

            self.result = {
                "broadcaster_id": bid,
                "time": time_str,
                "product_ids": product_ids,
                "avg_viewers": viewers,
            }
            self.destroy()
        except ValueError as e:
            messagebox.showerror("输入错误", str(e))


class FinanceTab(ttk.Frame):
    def __init__(self, parent, data_manager, on_data_change):
        super().__init__(parent)
        self.data_manager = data_manager
        self.on_data_change = on_data_change

        today = date.today()
        self.current_year = today.year
        self.current_month = today.month

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(top, text="选择月份:").pack(side=tk.LEFT)

        self.year_var = tk.StringVar(value=str(self.current_year))
        year_combo = ttk.Combobox(top, textvariable=self.year_var, width=8,
                                  values=[str(y) for y in range(2020, 2031)],
                                  state="readonly")
        year_combo.pack(side=tk.LEFT, padx=5)
        year_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(top, text="年").pack(side=tk.LEFT)

        self.month_var = tk.StringVar(value=str(self.current_month))
        month_combo = ttk.Combobox(top, textvariable=self.month_var, width=5,
                                   values=[str(m) for m in range(1, 13)],
                                   state="readonly")
        month_combo.pack(side=tk.LEFT, padx=5)
        month_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(top, text="月").pack(side=tk.LEFT)

        ttk.Button(top, text="导出CSV", command=self.export_csv).pack(side=tk.RIGHT, padx=5)
        ttk.Button(top, text="刷新", command=self.refresh).pack(side=tk.RIGHT, padx=5)

        columns = ("date", "time", "broadcaster", "product_count",
                   "slot_fee", "commission_est", "total")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")

        headings = [
            ("date", "日期", 100),
            ("time", "时段", 80),
            ("broadcaster", "主播", 100),
            ("product_count", "商品数", 80),
            ("slot_fee", "坑位费(元)", 100),
            ("commission_est", "预估佣金(元)", 120),
            ("total", "合计(元)", 120),
        ]
        for col, text, width in headings:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=5)

        summary_frame = ttk.Frame(self, relief=tk.GROOVE, borderwidth=1)
        summary_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(summary_frame, text="月度汇总", font=("Arial", 10, "bold")).pack(
            anchor=tk.W, padx=10, pady=(8, 5)
        )

        grid_frame = ttk.Frame(summary_frame)
        grid_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(grid_frame, text="总坑位费:").grid(row=0, column=0, sticky=tk.E, padx=(0, 5), pady=3)
        self.total_slot_label = ttk.Label(grid_frame, text="0", foreground="#d9534f",
                                          font=("Arial", 10, "bold"))
        self.total_slot_label.grid(row=0, column=1, sticky=tk.W, pady=3)

        ttk.Label(grid_frame, text="总预估佣金:").grid(row=0, column=2, sticky=tk.E, padx=(20, 5), pady=3)
        self.total_comm_label = ttk.Label(grid_frame, text="0", foreground="#5cb85c",
                                          font=("Arial", 10, "bold"))
        self.total_comm_label.grid(row=0, column=3, sticky=tk.W, pady=3)

        ttk.Label(grid_frame, text="月总收入:").grid(row=1, column=0, sticky=tk.E, padx=(0, 5), pady=(8, 3))
        self.total_all_label = ttk.Label(grid_frame, text="0", foreground="#337ab7",
                                         font=("Arial", 12, "bold"))
        self.total_all_label.grid(row=1, column=1, columnspan=3, sticky=tk.W, pady=(8, 3))

        grid_frame.grid_columnconfigure(1, weight=1)
        grid_frame.grid_columnconfigure(3, weight=1)

    def _calc_commission_estimate(self, schedule):
        bc = self.data_manager.get_broadcaster_by_id(schedule["broadcaster_id"])
        if not bc:
            return 0

        avg_viewers = schedule.get("avg_viewers", 50000)
        total_commission = 0

        for pid in schedule["product_ids"]:
            prod = self.data_manager.get_product_by_id(pid)
            if not prod:
                continue

            cat = prod["category"]
            conv_rate = CATEGORY_CONVERSION_RATE.get(cat, 0.05)
            est_sales = avg_viewers * conv_rate * DISCOUNT_FACTOR
            prod_commission = est_sales * prod["live_price"] * (prod["commission_rate"] / 100)
            total_commission += prod_commission

        return total_commission

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        try:
            year = int(self.year_var.get())
            month = int(self.month_var.get())
        except ValueError:
            return

        schedules = self.data_manager.get_schedules_by_month(year, month)
        schedules.sort(key=lambda s: (s["date"], s["time"]))

        total_slot = 0
        total_comm = 0

        for s in schedules:
            bc = self.data_manager.get_broadcaster_by_id(s["broadcaster_id"])
            bc_name = bc["name"] if bc else "未知"
            prod_count = len(s["product_ids"])

            slot_fee = prod_count * (bc["base_fee"] if bc else 0)
            comm_est = self._calc_commission_estimate(s)
            total = slot_fee + comm_est

            total_slot += slot_fee
            total_comm += comm_est

            self.tree.insert(
                "", tk.END,
                values=(
                    s["date"], s["time"], bc_name, prod_count,
                    f"{slot_fee:,.0f}", f"{comm_est:,.0f}", f"{total:,.0f}"
                )
            )

        self.total_slot_label.config(text=f"{total_slot:,.0f} 元")
        self.total_comm_label.config(text=f"{total_comm:,.0f} 元")
        self.total_all_label.config(text=f"{total_slot + total_comm:,.0f} 元")

    def export_csv(self):
        try:
            year = int(self.year_var.get())
            month = int(self.month_var.get())
        except ValueError:
            return

        default_name = f"费用核算_{year}年{month:02d}月.csv"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv")],
            initialfile=default_name,
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "日期", "时段", "主播", "商品数",
                    "坑位费(元)", "预估佣金(元)", "合计(元)"
                ])

                schedules = self.data_manager.get_schedules_by_month(year, month)
                schedules.sort(key=lambda s: (s["date"], s["time"]))

                total_slot = 0
                total_comm = 0

                for s in schedules:
                    bc = self.data_manager.get_broadcaster_by_id(s["broadcaster_id"])
                    bc_name = bc["name"] if bc else "未知"
                    prod_count = len(s["product_ids"])
                    slot_fee = prod_count * (bc["base_fee"] if bc else 0)
                    comm_est = self._calc_commission_estimate(s)
                    total = slot_fee + comm_est

                    total_slot += slot_fee
                    total_comm += comm_est

                    writer.writerow([
                        s["date"], s["time"], bc_name, prod_count,
                        f"{slot_fee:.0f}", f"{comm_est:.0f}", f"{total:.0f}"
                    ])

                writer.writerow([])
                writer.writerow(["", "", "", "合计",
                                 f"{total_slot:.0f}", f"{total_comm:.0f}",
                                 f"{total_slot + total_comm:.0f}"])

            messagebox.showinfo("成功", f"已导出到:\n{filepath}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MCN直播运营管理工具")
        self.geometry("1000x650")
        self.minsize(900, 600)

        self.data_manager = DataManager()

        self._build_menu()
        self._build_main_layout()
        self._build_statusbar()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="导入商品CSV", command=self._import_csv)
        file_menu.add_separator()
        file_menu.add_command(label="保存", command=self._save_data)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._on_close)
        menubar.add_cascade(label="文件", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self._show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)

        self.config(menu=menubar)

    def _build_main_layout(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.broadcaster_tab = BroadcasterTab(
            self.notebook, self.data_manager, self._on_data_change
        )
        self.product_tab = ProductTab(
            self.notebook, self.data_manager, self._on_data_change
        )
        self.calendar_tab = CalendarTab(
            self.notebook, self.data_manager, self._on_data_change
        )
        self.finance_tab = FinanceTab(
            self.notebook, self.data_manager, self._on_data_change
        )

        self.notebook.add(self.broadcaster_tab, text="主播管理")
        self.notebook.add(self.product_tab, text="商品池")
        self.notebook.add(self.calendar_tab, text="排期日历")
        self.notebook.add(self.finance_tab, text="费用核算")

    def _build_statusbar(self):
        self.status_var = tk.StringVar()
        self.status_var.set(f"数据目录: {DATA_DIR}")
        statusbar = ttk.Label(self, textvariable=self.status_var,
                              relief=tk.SUNKEN, anchor=tk.W, padding=(10, 3))
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    def _on_data_change(self):
        self.calendar_tab._render_calendar()
        self.finance_tab.refresh()

    def _save_data(self):
        try:
            self.data_manager.save_all()
            self.status_var.set(f"已保存 | 数据目录: {DATA_DIR}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def _import_csv(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")],
            title="选择商品CSV文件"
        )
        if not filepath:
            return

        try:
            count = 0
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        new_id = generate_id("p", self.data_manager.products)
                        product = {
                            "id": new_id,
                            "name": row.get("商品名", row.get("name", "")).strip(),
                            "brand": row.get("品牌", row.get("brand", "")).strip(),
                            "category": row.get("品类", row.get("category", "美妆")).strip(),
                            "supply_price": float(row.get("供货价", row.get("supply_price", 0))),
                            "live_price": float(row.get("直播价", row.get("live_price", 0))),
                            "commission_rate": float(row.get("佣金比例", row.get("commission_rate", 0))),
                            "stock": int(float(row.get("库存", row.get("stock", 0)))),
                        }
                        if not product["name"]:
                            continue
                        self.data_manager.products.append(product)
                        count += 1
                    except (ValueError, KeyError):
                        continue

            self.product_tab.refresh()
            self._on_data_change()
            messagebox.showinfo("导入完成", f"成功导入 {count} 个商品")
        except Exception as e:
            messagebox.showerror("导入失败", str(e))

    def _show_about(self):
        messagebox.showinfo(
            "关于",
            "MCN直播运营管理工具 v1.0\n\n"
            "功能：\n"
            "• 主播管理\n"
            "• 商品池管理\n"
            "• 排期日历\n"
            "• 费用核算"
        )

    def _on_close(self):
        self._save_data()
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
