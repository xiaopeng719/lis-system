#!/usr/bin/env python3
"""
LIS 仪器结果通讯工具 — GUI 版
从 Excel 表格读取仪器结果，通过 MQTT 发送到 LIS 系统
"""
import sys
import os
import json
import uuid
import threading
from datetime import datetime, timezone, timedelta

# PyInstaller 打包时需要处理路径
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# 依赖检查
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
except ImportError:
    print("需要 tkinter，请安装 python3-tk")
    sys.exit(1)

try:
    import openpyxl
except ImportError:
    print("需要 openpyxl，请运行: pip install openpyxl")
    sys.exit(1)

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False

# ========== 项目名称 → 编码映射 ==========
ITEM_NAME_MAP = {
    '白细胞': 'WBC', '白细胞计数': 'WBC', '白细胞数': 'WBC', '白细胞总数': 'WBC',
    '红细胞': 'RBC', '红细胞计数': 'RBC', '红细胞数': 'RBC',
    '血红蛋白': 'HGB', '血红蛋白测定': 'HGB', '血色素': 'HGB',
    '血小板': 'PLT', '血小板计数': 'PLT', '血小板数': 'PLT',
    '红细胞压积': 'HCT', '血细胞比容': 'HCT', '压积': 'HCT',
    '葡萄糖': 'GLU', '血糖': 'GLU', '空腹血糖': 'GLU', '葡萄糖测定': 'GLU',
    '谷丙转氨酶': 'ALT', '丙氨酸氨基转移酶': 'ALT',
    '谷草转氨酶': 'AST', '天门冬氨酸氨基转移酶': 'AST',
    '总蛋白': 'TP', '总蛋白测定': 'TP',
    '白蛋白': 'ALB', '白蛋白测定': 'ALB',
    '总胆红素': 'TBIL', '总胆红素测定': 'TBIL',
    '肌酐': 'CRE', '肌酐测定': 'CRE', '血肌酐': 'CRE',
    '尿素氮': 'BUN', '尿素': 'BUN',
    '尿酸': 'UA', '尿酸测定': 'UA',
    '总胆固醇': 'TC', '胆固醇': 'TC',
    '甘油三酯': 'TG',
    '高密度脂蛋白': 'HDL', '高密度脂蛋白胆固醇': 'HDL',
    '低密度脂蛋白': 'LDL', '低密度脂蛋白胆固醇': 'LDL',
    '钾': 'K', '钾离子': 'K', '血钾': 'K',
    '钠': 'Na', '钠离子': 'Na', '血钠': 'Na',
    '氯': 'Cl', '氯离子': 'Cl', '血氯': 'Cl',
    '钙': 'Ca', '钙离子': 'Ca', '血钙': 'Ca',
    '中性粒细胞': 'NEUT', '中性粒细胞百分比': 'NEUT%',
    '淋巴细胞': 'LYMPH', '淋巴细胞百分比': 'LYMPH%',
    '单核细胞': 'MONO', '单核细胞百分比': 'MONO%',
    '嗜酸性粒细胞': 'EO', '嗜酸性粒细胞百分比': 'EO%',
    '嗜碱性粒细胞': 'BASO', '嗜碱性粒细胞百分比': 'BASO%',
    '平均红细胞体积': 'MCV', '平均血红蛋白量': 'MCH', '平均血红蛋白浓度': 'MCHC',
    '红细胞分布宽度': 'RDW', '血小板分布宽度': 'PDW', '平均血小板体积': 'MPV',
    '碱性磷酸酶': 'ALP', '谷氨酰转肽酶': 'GGT', 'γ-谷氨酰转肽酶': 'GGT',
    '乳酸脱氢酶': 'LDH', '肌酸激酶': 'CK', '肌酸激酶同工酶': 'CK-MB',
    '淀粉酶': 'AMY', '脂肪酶': 'LPS',
    '直接胆红素': 'DBIL', '间接胆红素': 'IBIL',
}


def resolve_item_code(name: str) -> str:
    """将项目名称转为编码"""
    code = ITEM_NAME_MAP.get(name.strip())
    if code:
        return code
    code = ITEM_NAME_MAP.get(name.strip(), name.strip().upper())
    return code


def parse_excel(filepath: str):
    """解析 Excel 文件，返回 {barcode: [(item_code, value), ...]}"""
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        raise ValueError("文件为空")

    # 自动识别表头行
    header_row = rows[0]
    barcode_col = item_col = value_col = None

    for i, cell in enumerate(header_row):
        if cell is None:
            continue
        c = str(cell).strip().lower()
        if any(k in c for k in ['样品', '样本', '编号', '条码', 'barcode', 'sample', 'specimen', '标本号']):
            barcode_col = i
        elif any(k in c for k in ['项目', '名称', 'item', 'test', '检验']):
            item_col = i
        elif any(k in c for k in ['结果', '值', 'result', 'value']):
            value_col = i

    # 默认：第1列=样品, 第2列=项目, 第3列=结果
    if barcode_col is None: barcode_col = 0
    if item_col is None: item_col = 1
    if value_col is None: value_col = 2

    data = {}
    for row in rows[1:]:
        if not row or all(c is None for c in row):
            continue
        bc = str(row[barcode_col]).strip() if row[barcode_col] else ''
        item_name = str(row[item_col]).strip() if row[item_col] else ''
        result_val = str(row[value_col]).strip() if row[value_col] else ''

        if not bc or not item_name:
            continue

        item_code = resolve_item_code(item_name)
        data.setdefault(bc, []).append((item_code, result_val))

    return data


def build_mqtt_message(barcode: str, results: list, instrument_code: str, tz_offset: int = 8):
    """构建 MQTT JSON 消息"""
    tz = timezone(timedelta(hours=tz_offset))
    return {
        "msg_id": str(uuid.uuid4()),
        "instrument_code": instrument_code,
        "timestamp": datetime.now(tz).isoformat(),
        "specimen": {"barcode": barcode},
        "results": [
            {"channel": code, "item_code": code, "value": val, "unit": "", "flag": "N"}
            for code, val in results
        ]
    }


class LISApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LIS 仪器结果通讯工具 v1.0")
        self.root.geometry("650x580")
        self.root.resizable(True, True)

        self.filepath = tk.StringVar()
        self.broker_host = tk.StringVar(value="localhost")
        self.broker_port = tk.IntVar(value=1883)
        self.instrument_code = tk.StringVar(value="CHEM-001")
        self.topic_template = tk.StringVar(value="lis/instrument/{instrument}/result")

        self._build_ui()

    def _build_ui(self):
        pad = {'padx': 10, 'pady': 5}

        # ---- 连接设置 ----
        conn_frame = ttk.LabelFrame(self.root, text="MQTT 连接设置", padding=10)
        conn_frame.pack(fill='x', **pad)

        row0 = ttk.Frame(conn_frame)
        row0.pack(fill='x')
        ttk.Label(row0, text="Broker 地址:").pack(side='left')
        ttk.Entry(row0, textvariable=self.broker_host, width=20).pack(side='left', padx=(5, 15))
        ttk.Label(row0, text="端口:").pack(side='left')
        ttk.Entry(row0, textvariable=self.broker_port, width=8).pack(side='left', padx=(5, 15))
        ttk.Label(row0, text="仪器编码:").pack(side='left')
        ttk.Entry(row0, textvariable=self.instrument_code, width=15).pack(side='left', padx=5)

        row1 = ttk.Frame(conn_frame)
        row1.pack(fill='x', pady=(5, 0))
        ttk.Label(row1, text="Topic 模板:").pack(side='left')
        ttk.Entry(row1, textvariable=self.topic_template, width=45).pack(side='left', padx=5, fill='x', expand=True)

        # ---- 文件选择 ----
        file_frame = ttk.LabelFrame(self.root, text="Excel 文件", padding=10)
        file_frame.pack(fill='x', **pad)

        row2 = ttk.Frame(file_frame)
        row2.pack(fill='x')
        ttk.Entry(row2, textvariable=self.filepath, width=50).pack(side='left', fill='x', expand=True)
        ttk.Button(row2, text="选择文件...", command=self._browse_file).pack(side='left', padx=(5, 0))
        ttk.Button(row2, text="解析预览", command=self._preview).pack(side='left', padx=5)

        # ---- 预览 ----
        preview_frame = ttk.LabelFrame(self.root, text="解析预览", padding=10)
        preview_frame.pack(fill='both', expand=True, **pad)

        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=8, font=('Consolas', 10))
        self.preview_text.pack(fill='both', expand=True)

        # ---- 操作栏 ----
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill='x')

        self.send_btn = ttk.Button(btn_frame, text="📡  发送到 LIS", command=self._send)
        self.send_btn.pack(side='left', padx=5)

        self.status_label = ttk.Label(btn_frame, text="就绪", foreground='gray')
        self.status_label.pack(side='left', padx=15)

        ttk.Button(btn_frame, text="退出", command=self.root.quit).pack(side='right', padx=5)

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="选择仪器结果 Excel 文件",
            filetypes=[("Excel 文件", "*.xlsx *.xls"), ("所有文件", "*.*")]
        )
        if path:
            self.filepath.set(path)
            self._preview()

    def _log(self, msg):
        self.preview_text.insert('end', msg + '\n')
        self.preview_text.see('end')
        self.root.update_idletasks()

    def _preview(self):
        path = self.filepath.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showwarning("提示", "请先选择 Excel 文件")
            return

        self.preview_text.delete('1.0', 'end')
        self._log(f"📁 文件: {os.path.basename(path)}")
        self._log(f"🔧 仪器: {self.instrument_code.get()}")
        self._log("")

        try:
            data = parse_excel(path)
            total = sum(len(v) for v in data.values())
            self._log(f"📊 解析完成: {len(data)} 个样品, {total} 条结果")
            self._log("")

            for bc, results in data.items():
                self._log(f"📦 样品 {bc}:")
                for code, val in results:
                    self._log(f"   {code:12s} = {val}")
                self._log("")

            self.status_label.config(text=f"✅ 解析成功: {len(data)} 样品, {total} 条结果", foreground='green')

        except Exception as e:
            self._log(f"❌ 解析失败: {e}")
            self.status_label.config(text="❌ 解析失败", foreground='red')

    def _send(self):
        if not HAS_MQTT:
            messagebox.showerror("缺少依赖", "需要 paho-mqtt 库\n请运行: pip install paho-mqtt")
            return

        path = self.filepath.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showwarning("提示", "请先选择 Excel 文件")
            return

        self.send_btn.config(state='disabled')
        self.status_label.config(text="📡 正在发送...", foreground='blue')
        self.preview_text.delete('1.0', 'end')

        threading.Thread(target=self._send_thread, args=(path,), daemon=True).start()

    def _send_thread(self, path):
        try:
            data = parse_excel(path)
            instrument = self.instrument_code.get()
            topic_tpl = self.topic_template.get()
            topic = topic_tpl.replace("{instrument}", instrument)

            self.root.after(0, self._log, f"📡 连接 MQTT: {self.broker_host.get()}:{self.broker_port.get()}")

            client = mqtt.Client(client_id=f"lis-sender-{uuid.uuid4().hex[:8]}")

            connected = threading.Event()
            def on_connect(c, ud, flags, rc):
                connected.set()

            client.on_connect = on_connect
            client.connect(self.broker_host.get(), self.broker_port.get(), 60)
            client.loop_start()

            if not connected.wait(timeout=10):
                raise ConnectionError(f"连接超时: {self.broker_host.get()}:{self.broker_port.get()}")

            self.root.after(0, self._log, f"✅ 连接成功，Topic: {topic}\n")

            success = 0
            fail = 0
            for bc, results in data.items():
                msg = build_mqtt_message(bc, results, instrument)
                payload = json.dumps(msg, ensure_ascii=False)

                info = client.publish(topic, payload, qos=1)
                if info.rc == mqtt.MQTT_ERR_SUCCESS:
                    success += 1
                    self.root.after(0, self._log, f"  📤 [{bc}] → {topic}  ({len(results)} 项)")
                else:
                    fail += 1
                    self.root.after(0, self._log, f"  ❌ [{bc}] 发送失败 (rc={info.rc})")

            client.loop_stop()
            client.disconnect()

            self.root.after(0, self._log, "")
            self.root.after(0, self._log, f"✅ 发送完成: {success} 成功, {fail} 失败")
            self.root.after(0, self._log, "🎉 LIS 系统将自动接收结果！请在「结果审核」页面查看。")
            self.root.after(0, lambda: self.status_label.config(
                text=f"✅ 发送完成: {success}/{success+fail}", foreground='green'))

        except Exception as e:
            self.root.after(0, self._log, f"\n❌ 发送失败: {e}")
            self.root.after(0, lambda: self.status_label.config(text=f"❌ {e}", foreground='red'))

        finally:
            self.root.after(0, lambda: self.send_btn.config(state='normal'))

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = LISApp()
    app.run()
