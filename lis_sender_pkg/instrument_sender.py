#!/usr/bin/env python3
"""
仪器结果通讯程序 — 读取 Excel 表格 → 发送到 MQTT → LIS 自动接收

用法:
  python instrument_sender.py 测试.xlsx
  python instrument_sender.py 测试.xlsx --instrument CBC-001
  python instrument_sender.py 测试.xlsx --broker 192.168.1.100 --port 1883

Excel 格式要求:
  第一行为表头，至少包含以下列（名称可灵活匹配）：
  | 样品编号/条码/标本号 | 项目名称/项目编码/检验项目 | 结果/结果值/检测结果 |

  示例:
  | 样品编号 | 项目名称 | 结果 |
  |---------|---------|------|
  | SP001   | WBC     | 6.8  |
  | SP001   | GLU     | 5.2  |
  | SP002   | ALT     | 35   |
"""

import argparse
import json
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("❌ 请先安装 openpyxl: pip install openpyxl")
    sys.exit(1)

try:
    import paho.mqtt.client as mqtt
    from paho.mqtt.client import CallbackAPIVersion
except ImportError:
    print("❌ 请先安装 paho-mqtt: pip install paho-mqtt")
    sys.exit(1)


# ========== 列名映射（支持多种写法） ==========
SAMPLE_ID_KEYWORDS = ["样品编号", "条码", "标本号", "标本编号", "样本号", "sample", "barcode", "id"]
ITEM_NAME_KEYWORDS = ["项目名称", "项目编码", "检验项目", "项目", "item", "test", "name", "code"]
RESULT_KEYWORDS = ["结果", "结果值", "检测结果", "result", "value"]

# 项目名称 → 项目编码 映射（中文名→系统编码）
# 如果 Excel 里直接用编码（如 WBC、GLU），则不需要映射
ITEM_NAME_TO_CODE = {
    # 血常规
    "白细胞计数": "WBC", "白细胞": "WBC", "WBC计数": "WBC",
    "红细胞计数": "RBC", "红细胞": "RBC", "RBC计数": "RBC",
    "血红蛋白": "HGB", "血红蛋白测定": "HGB", "Hb": "HGB",
    "血小板计数": "PLT", "血小板": "PLT", "PLT计数": "PLT",
    "中性粒细胞比率": "NEUT%", "中性粒比率": "NEUT%", "NEUT": "NEUT%",
    "淋巴细胞比率": "LYM%", "淋巴比率": "LYM%", "LYM": "LYM%",
    # 生化
    "葡萄糖": "GLU", "血糖": "GLU", "空腹血糖": "GLU", "GLU葡萄糖": "GLU",
    "谷丙转氨酶": "ALT", "丙氨酸氨基转移酶": "ALT", "ALT谷丙": "ALT",
    "谷草转氨酶": "AST", "天门冬氨酸氨基转移酶": "AST", "AST谷草": "AST",
    "肌酐": "CRE", "血肌酐": "CRE", "CRE肌酐": "CRE",
    "尿素氮": "BUN", "尿素": "BUN", "BUN尿素氮": "BUN",
    "尿酸": "UA", "血尿酸": "UA", "UA尿酸": "UA",
    "总胆固醇": "TC", "胆固醇": "TC", "TC总胆固醇": "TC",
    "甘油三酯": "TG", "TG甘油三酯": "TG",
    # 尿液
    "尿蛋白": "U-PRO", "蛋白": "U-PRO",
    "尿糖": "U-GLU", "尿液葡萄糖": "U-GLU",
    "尿潜血": "U-BLD", "潜血": "U-BLD",
}


def find_column(headers: list, keywords: list) -> int:
    """根据关键词找到对应的列索引"""
    for i, h in enumerate(headers):
        h_lower = str(h).strip().lower()
        for kw in keywords:
            if kw.lower() in h_lower:
                return i
    return -1


def resolve_item_code(name: str) -> str:
    """将项目名称解析为项目编码"""
    name = str(name).strip()
    # 如果本身就是编码格式（全大写+数字），直接返回
    if name.upper() == name and len(name) <= 10:
        return name.upper()
    # 查映射表
    if name in ITEM_NAME_TO_CODE:
        return ITEM_NAME_TO_CODE[name]
    # 模糊匹配
    for cn, code in ITEM_NAME_TO_CODE.items():
        if cn in name or name in cn:
            return code
    # 都没匹配到，原样返回
    return name


def read_excel(filepath: str) -> dict:
    """
    读取 Excel，返回按样品编号分组的结果
    返回: { "样品编号": [ {"item_code": "WBC", "value": "6.8", "unit": ""}, ... ] }
    """
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(min_row=1, values_only=True))
    if len(rows) < 2:
        print("❌ Excel 至少需要 2 行（1 行表头 + 1 行数据）")
        sys.exit(1)

    headers = [str(h).strip() if h else "" for h in rows[0]]
    print(f"📋 表头: {headers}")

    # 查找列
    sample_col = find_column(headers, SAMPLE_ID_KEYWORDS)
    item_col = find_column(headers, ITEM_NAME_KEYWORDS)
    result_col = find_column(headers, RESULT_KEYWORDS)

    if sample_col < 0:
        print(f"❌ 找不到样品编号列（支持: {SAMPLE_ID_KEYWORDS}）")
        sys.exit(1)
    if item_col < 0:
        print(f"❌ 找不到项目名称列（支持: {ITEM_NAME_KEYWORDS}）")
        sys.exit(1)
    if result_col < 0:
        print(f"❌ 找不到结果列（支持: {RESULT_KEYWORDS}）")
        sys.exit(1)

    print(f"✅ 列映射: 样品编号=第{sample_col+1}列, 项目名称=第{item_col+1}列, 结果=第{result_col+1}列")

    # 解析数据
    grouped = defaultdict(list)
    for row_num, row in enumerate(rows[1:], start=2):
        sample_id = str(row[sample_col]).strip() if row[sample_col] else ""
        item_name = str(row[item_col]).strip() if row[item_col] else ""
        result_val = str(row[result_col]).strip() if row[result_col] else ""

        if not sample_id or not item_name:
            continue

        item_code = resolve_item_code(item_name)
        grouped[sample_id].append({
            "item_code": item_code,
            "item_name": item_name,
            "result_value": result_val,
        })

    print(f"📊 解析完成: {len(grouped)} 个样品, {sum(len(v) for v in grouped.values())} 条结果")
    return dict(grouped)


def build_mqtt_message(instrument_code: str, sample_id: str, results: list) -> str:
    """构造 MQTT JSON 消息"""
    msg = {
        "msg_id": str(uuid.uuid4()),
        "instrument_code": instrument_code,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "specimen": {
            "barcode": sample_id,
        },
        "results": [
            {
                "channel": r["item_code"],
                "item_code": r["item_code"],
                "value": r["result_value"],
                "unit": "",
                "flag": "N",
            }
            for r in results
        ],
    }
    return json.dumps(msg, ensure_ascii=False)


def send_to_mqtt(broker: str, port: int, instrument_code: str, messages: list):
    """通过 MQTT 发送所有消息"""
    topic = f"lis/instrument/{instrument_code}/result"

    print(f"\n📡 连接 MQTT Broker: {broker}:{port}")
    client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id=f"instrument-{instrument_code}-{int(time.time())}")

    connected = False
    def on_connect(client, userdata, flags, rc, properties=None):
        nonlocal connected
        connected = True
        print(f"✅ MQTT 连接成功")

    client.on_connect = on_connect

    try:
        client.connect(broker, port, keepalive=60)
        client.loop_start()

        # 等待连接
        for _ in range(30):
            if connected:
                break
            time.sleep(0.1)

        if not connected:
            print("❌ MQTT 连接超时")
            return False

        # 发送消息
        success = 0
        for sample_id, payload in messages:
            result = client.publish(topic, payload, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"  📤 [{sample_id}] → {topic}")
                success += 1
            else:
                print(f"  ❌ [{sample_id}] 发送失败: rc={result.rc}")
            time.sleep(0.1)  # 避免发送过快

        client.loop_stop()
        client.disconnect()

        print(f"\n✅ 发送完成: {success}/{len(messages)} 条消息")
        return True

    except Exception as e:
        print(f"❌ MQTT 错误: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="仪器结果通讯程序 — Excel → MQTT → LIS")
    parser.add_argument("file", help="Excel 文件路径")
    parser.add_argument("--instrument", "-i", default="CHEM-001",
                        help="仪器编码（默认: CHEM-001）")
    parser.add_argument("--broker", "-b", default="localhost",
                        help="MQTT Broker 地址（默认: localhost）")
    parser.add_argument("--port", "-p", type=int, default=1883,
                        help="MQTT Broker 端口（默认: 1883）")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="只解析不发送（调试用）")
    args = parser.parse_args()

    # 检查文件
    if not Path(args.file).exists():
        print(f"❌ 文件不存在: {args.file}")
        sys.exit(1)

    print(f"🔬 仪器结果通讯程序")
    print(f"{'='*50}")
    print(f"📁 文件: {args.file}")
    print(f"🔧 仪器: {args.instrument}")
    print(f"📡 Broker: {args.broker}:{args.port}")
    print()

    # 读取 Excel
    data = read_excel(args.file)
    if not data:
        print("❌ 没有读取到有效数据")
        sys.exit(1)

    # 构造消息
    messages = []
    for sample_id, results in data.items():
        payload = build_mqtt_message(args.instrument, sample_id, results)
        messages.append((sample_id, payload))
        print(f"\n📦 样品 {sample_id}:")
        for r in results:
            print(f"   {r['item_code']:10s} = {r['result_value']}")

    if args.dry_run:
        print(f"\n🔍 Dry run 模式，不发送消息")
        print(f"\n示例消息:")
        print(messages[0][1] if messages else "无")
        return

    # 发送
    success = send_to_mqtt(args.broker, args.port, args.instrument, messages)
    if success:
        print(f"\n🎉 全部完成！LIS 系统将自动接收并处理这些结果。")
        print(f"   请在 LIS 的「结果审核」页面查看。")
    else:
        print(f"\n❌ 发送失败，请检查 MQTT Broker 是否运行。")


if __name__ == "__main__":
    main()
