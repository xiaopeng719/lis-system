"""
MQTT 测试工具 — 模拟仪器发送检验结果
用法: python -m app.test_mqtt
"""
import json
import time
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected to MQTT Broker: {rc}")


def send_result(client, instrument_code, barcode, results):
    """发送模拟检验结果"""
    topic = f"lis/instrument/{instrument_code}/result"
    payload = {
        "msg_id": f"test-{int(time.time() * 1000)}",
        "instrument_code": instrument_code,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "specimen": {
            "barcode": barcode,
        },
        "results": results,
    }
    payload_str = json.dumps(payload, ensure_ascii=False)
    result = client.publish(topic, payload_str, qos=1)
    print(f"📤 Published to {topic}: {payload_str}")
    return result


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test-instrument")
    client.on_connect = on_connect
    client.connect(BROKER, PORT)
    client.loop_start()

    time.sleep(1)

    # 模拟血常规结果
    print("\n=== 发送血常规结果 ===")
    send_result(client, "CBC-001", "SP20260619001", [
        {"channel": "WBC", "item_code": "WBC", "value": "7.5", "unit": "×10⁹/L", "flag": "N"},
        {"channel": "RBC", "item_code": "RBC", "value": "4.8", "unit": "×10¹²/L", "flag": "N"},
        {"channel": "HGB", "item_code": "HGB", "value": "145", "unit": "g/L", "flag": "N"},
        {"channel": "PLT", "item_code": "PLT", "value": "220", "unit": "×10⁹/L", "flag": "N"},
    ])

    time.sleep(1)

    # 模拟生化结果（含异常值）
    print("\n=== 发送生化结果 ===")
    send_result(client, "CHEM-001", "SP20260619002", [
        {"channel": "GLU", "item_code": "GLU", "value": "8.5", "unit": "mmol/L", "flag": "H"},
        {"channel": "ALT", "item_code": "ALT", "value": "85.3", "unit": "U/L", "flag": "H"},
        {"channel": "CRE", "item_code": "CRE", "value": "95.0", "unit": "μmol/L", "flag": "N"},
        {"channel": "BUN", "item_code": "BUN", "value": "6.5", "unit": "mmol/L", "flag": "N"},
    ])

    time.sleep(1)

    # 模拟另一个生化结果
    print("\n=== 发送生化结果（正常）===")
    send_result(client, "CHEM-001", "SP20260619003", [
        {"channel": "GLU", "item_code": "GLU", "value": "5.2", "unit": "mmol/L", "flag": "N"},
        {"channel": "ALT", "item_code": "ALT", "value": "25.0", "unit": "U/L", "flag": "N"},
        {"channel": "AST", "item_code": "AST", "value": "28.5", "unit": "U/L", "flag": "N"},
        {"channel": "TC", "item_code": "TC", "value": "4.8", "unit": "mmol/L", "flag": "N"},
        {"channel": "TG", "item_code": "TG", "value": "1.2", "unit": "mmol/L", "flag": "N"},
    ])

    time.sleep(1)
    client.loop_stop()
    client.disconnect()
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    main()
