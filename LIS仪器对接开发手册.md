# LIS 仪器数据对接开发手册

> 版本：v1.0 | 更新日期：2026-06-21

---

## 一、系统架构

```
仪器/工具 ──MQTT──→ Broker(1883) ──MQTT──→ LIS 系统
                              ↓
                        数据自动入库
```

LIS 系统通过 **MQTT 协议**接收仪器检验结果。任何能发送 MQTT 消息的程序、脚本、硬件都可以对接。

---

## 二、MQTT Broker 信息

| 参数 | 值 |
|------|-----|
| 地址 | `192.168.169.129`（LIS 服务器 IP） |
| 端口 | `1883` |
| 用户名 | 无（匿名连接） |
| Topic | `lis/instrument/{仪器编码}/result` |

**仪器编码**是在 LIS 系统「仪器管理」页面注册的编码，例如：
- `CBC-001`（血细胞分析仪）
- `CHEM-001`（生化分析仪）

---

## 三、消息格式（JSON）

### 3.1 完整格式

```json
{
  "msg_id": "唯一消息ID（UUID）",
  "instrument_code": "CHEM-001",
  "timestamp": "2026-06-21T10:30:00+08:00",
  "specimen": {
    "barcode": "SP20260621001"
  },
  "results": [
    {
      "channel": "1",
      "item_code": "ALT",
      "value": "25.3",
      "unit": "U/L",
      "flag": "N"
    },
    {
      "channel": "2",
      "item_code": "AST",
      "value": "38.1",
      "unit": "U/L",
      "flag": "N"
    }
  ]
}
```

### 3.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `msg_id` | string | 是 | 消息唯一标识，建议用 UUID |
| `instrument_code` | string | 是 | 仪器编码，必须在 LIS 中注册过 |
| `timestamp` | string | 否 | 发送时间，ISO 8601 格式 |
| `specimen.barcode` | string | 是 | 标本条码号，必须在 LIS 中存在 |
| `results` | array | 是 | 检验结果列表（不能为空） |
| `results[].item_code` | string | 是 | 项目编码（如 ALT、WBC），必须在 LIS 中存在 |
| `results[].value` | string | 是 | 结果值 |
| `results[].unit` | string | 否 | 单位，不传则用项目默认单位 |
| `results[].flag` | string | 否 | 异常标记：N=正常, H=偏高, L=偏低, A=异常 |

### 3.3 项目编码对照表

#### 血常规（绑定仪器 CBC-001）
| 编码 | 中文名 | 单位 | 参考范围 |
|------|--------|------|---------|
| WBC | 白细胞计数 | ×10⁹/L | 4.0 - 10.0 |
| RBC | 红细胞计数 | ×10¹²/L | 3.5 - 5.5 |
| HGB | 血红蛋白 | g/L | 110 - 160 |
| PLT | 血小板计数 | ×10⁹/L | 100 - 300 |

#### 生化（绑定仪器 CHEM-001）
| 编码 | 中文名 | 单位 | 参考范围 |
|------|--------|------|---------|
| GLU | 葡萄糖 | mmol/L | 3.9 - 6.1 |
| ALT | 谷丙转氨酶 | U/L | 0 - 40 |
| AST | 谷草转氨酶 | U/L | 0 - 40 |
| CRE | 肌酐 | μmol/L | 44 - 133 |
| BUN | 尿素氮 | mmol/L | 2.9 - 8.2 |
| TC | 总胆固醇 | mmol/L | 2.8 - 5.7 |
| TG | 甘油三酯 | mmol/L | 0.3 - 1.7 |

> 可在 LIS「基础数据 → 检验项目」页面查看/修改完整列表。

---

## 四、对接步骤

### 步骤 1：在 LIS 中注册仪器
进入 **仪器管理** → 添加仪器，记录仪器编码。

### 步骤 2：确认标本条码
发送前确保标本已在 LIS 中创建（条码号匹配）。

### 步骤 3：发送 MQTT 消息
连接 Broker → 发布 JSON 到对应 Topic。

### 步骤 4：验证
在 LIS「结果审核」页面查看是否收到结果。

---

## 五、代码示例

### 5.1 Python（推荐）

```python
import json
import uuid
from datetime import datetime
import paho.mqtt.client as mqtt

# 配置
BROKER_HOST = "192.168.169.129"
BROKER_PORT = 1883
INSTRUMENT_CODE = "CHEM-001"

# 构造消息
message = {
    "msg_id": str(uuid.uuid4()),
    "instrument_code": INSTRUMENT_CODE,
    "timestamp": datetime.now().astimezone().isoformat(),
    "specimen": {"barcode": "SP20260621001"},
    "results": [
        {"item_code": "ALT", "value": "25.3", "unit": "U/L", "flag": "N"},
        {"item_code": "AST", "value": "38.1", "unit": "U/L", "flag": "N"},
    ]
}

# 发送
client = mqtt.Client()
client.connect(BROKER_HOST, BROKER_PORT)
topic = f"lis/instrument/{INSTRUMENT_CODE}/result"
client.publish(topic, json.dumps(message, ensure_ascii=False), qos=1)
client.disconnect()
print("发送成功")
```

**安装依赖：**
```bash
pip install paho-mqtt
```

### 5.2 JavaScript / Node.js

```javascript
const mqtt = require('mqtt');
const { v4: uuidv4 } = require('uuid');

const client = mqtt.connect('mqtt://192.168.169.129:1883');

client.on('connect', () => {
  const message = {
    msg_id: uuidv4(),
    instrument_code: 'CHEM-001',
    timestamp: new Date().toISOString(),
    specimen: { barcode: 'SP20260621001' },
    results: [
      { item_code: 'ALT', value: '25.3', unit: 'U/L', flag: 'N' },
      { item_code: 'AST', value: '38.1', unit: 'U/L', flag: 'N' },
    ]
  };

  client.publish(
    'lis/instrument/CHEM-001/result',
    JSON.stringify(message),
    { qos: 1 },
    () => { console.log('发送成功'); client.end(); }
  );
});
```

**安装依赖：**
```bash
npm install mqtt uuid
```

### 5.3 Java

```java
import org.eclipse.paho.client.mqttv3.*;
import com.google.gson.Gson;
import java.util.*;

MqttClient client = new MqttClient("tcp://192.168.169.129:1883", "instr-001");
client.connect();

Map<String, Object> msg = new HashMap<>();
msg.put("msg_id", UUID.randomUUID().toString());
msg.put("instrument_code", "CHEM-001");

Map<String, String> specimen = new HashMap<>();
specimen.put("barcode", "SP20260621001");
msg.put("specimen", specimen);

List<Map<String, String>> results = new ArrayList<>();
Map<String, String> r1 = new HashMap<>();
r1.put("item_code", "ALT"); r1.put("value", "25.3");
results.add(r1);
msg.put("results", results);

MqttMessage mqttMsg = new MqttMessage(new Gson().toJson(msg).getBytes());
mqttMsg.setQos(1);
client.publish("lis/instrument/CHEM-001/result", mqttMsg);
client.disconnect();
```

### 5.4 C# (.NET)

```csharp
using MQTTnet;
using MQTTnet.Client;
using System.Text.Json;

var factory = new MqttFactory();
var client = factory.CreateMqttClient();

var options = new MqttClientOptionsBuilder()
    .WithTcpServer("192.168.169.129", 1883)
    .Build();

await client.ConnectAsync(options);

var message = new {
    msg_id = Guid.NewGuid().ToString(),
    instrument_code = "CHEM-001",
    timestamp = DateTime.Now.ToString("o"),
    specimen = new { barcode = "SP20260621001" },
    results = new[] {
        new { item_code = "ALT", value = "25.3", unit = "U/L", flag = "N" },
        new { item_code = "AST", value = "38.1", unit = "U/L", flag = "N" },
    }
};

var mqttMsg = new MqttApplicationMessageBuilder()
    .WithTopic("lis/instrument/CHEM-001/result")
    .WithPayload(JsonSerializer.Serialize(message))
    .WithQualityOfServiceLevel(MqttQualityOfServiceLevel.AtLeastOnce)
    .Build();

await client.PublishAsync(mqttMsg);
await client.DisconnectAsync();
```

### 5.5 Shell（curl 测试用）

```bash
# 安装 mosquitto 客户端
# CentOS: yum install mosquitto
# Ubuntu: apt install mosquitto-clients

mosquitto_pub -h 192.168.169.129 -p 1883 \
  -t "lis/instrument/CHEM-001/result" \
  -m '{"msg_id":"test-001","instrument_code":"CHEM-001","specimen":{"barcode":"SP001"},"results":[{"item_code":"ALT","value":"25","flag":"N"}]}'
```

---

## 六、从 Excel 批量发送

LIS 自带了一个 Python 工具 `instrument_sender.py`，可以直接读取 Excel 发送。

### Excel 格式要求

| 样品编号 | 项目名称 | 结果 |
|---------|---------|------|
| SP001   | ALT     | 25   |
| SP001   | AST     | 38   |
| SP002   | GLU     | 5.6  |

- 第 1 列：样品编号/条码
- 第 2 列：项目编码或中文名（支持自动转换）
- 第 3 列：结果值

### 使用方法

```bash
# 安装依赖
pip install openpyxl paho-mqtt

# 发送
python instrument_sender.py 数据.xlsx

# 指定仪器和 Broker
python instrument_sender.py 数据.xlsx --instrument CHEM-001 --broker 192.168.169.129

# 只预览不发送
python instrument_sender.py 数据.xlsx --dry-run
```

---

## 七、支持的项目名称映射

工具支持中文名自动转编码：

| Excel 中写法 | 转换为 |
|-------------|--------|
| 白细胞 / 白细胞计数 | WBC |
| 红细胞 / 红细胞计数 | RBC |
| 血红蛋白 | HGB |
| 血小板 / 血小板计数 | PLT |
| 葡萄糖 / 血糖 | GLU |
| 谷丙转氨酶 | ALT |
| 谷草转氨酶 | AST |
| 肌酐 | CRE |
| 尿素氮 | BUN |
| 总胆固醇 | TC |
| 甘油三酯 | TG |
| 钾 / 血钾 | K |
| 钠 / 血钠 | Na |
| 氯 / 血氯 | Cl |
| 钙 / 血钙 | Ca |

也可以直接使用编码（ALT、WBC 等）。

---

## 八、常见问题

### Q1: 发送成功但 LIS 没收到？
1. 检查 Broker 是否运行：`telnet 192.168.169.129 1883`
2. 检查仪器编码是否在 LIS 中注册
3. 检查标本条码是否在 LIS 中存在
4. 检查项目编码是否在 LIS 中存在

### Q2: 提示 "Instrument not found"？
仪器编码不匹配。去 LIS「仪器管理」页面确认编码。

### Q3: 提示 "Specimen not found"？
标本条码不匹配。去 LIS「标本管理」页面确认条码。

### Q4: 提示 "Results must be a non-empty list"？
results 数组不能为空，至少要有一条结果。

### Q5: 如何确认消息已收到？
1. 在 LIS「结果审核」页面查看
2. 查看 LIS 后端日志中的 `mqtt_service` 输出

---

## 九、Topic 规则

```
lis/instrument/{仪器编码}/result
```

示例：
- `lis/instrument/CBC-001/result` → 血细胞分析仪结果
- `lis/instrument/CHEM-001/result` → 生化分析仪结果
- `lis/instrument/COAG-001/result` → 凝血分析仪结果

---

## 十、安全建议（生产环境）

1. **MQTT 认证**：配置 Broker 用户名密码
2. **TLS 加密**：使用 8883 端口 + SSL 证书
3. **Topic 权限**：限制每个仪器只能发布自己的 Topic
4. **消息持久化**：Broker 配置消息持久化，防止丢失
5. **日志记录**：LIS 已自动记录所有 MQTT 消息

---

## 十一、技术支持

- LIS 系统地址：http://192.168.169.129:3000
- API 文档：http://192.168.169.129:8000/docs
- MQTT Broker：192.168.169.129:1883

如有问题请联系检验科信息组。
