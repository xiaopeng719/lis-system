import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class JsonParser:
    """解析 JSON 格式的仪器结果数据"""

    @staticmethod
    def parse(payload: bytes | str) -> dict[str, Any]:
        """
        解析 MQTT JSON 消息

        期望格式（两种）:

        方式1 - 用项目编码:
        {
            "instrument_code": "CHEM-001",
            "specimen": {"barcode": "SP001"},
            "results": [{"item_code": "ALT", "value": "25"}]
        }

        方式2 - 用通道号:
        {
            "instrument_code": "CHEM-001",
            "specimen": {"barcode": "SP001"},
            "results": [{"channel": "1", "value": "25"}]
        }
        """
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        data = json.loads(payload)

        # 校验必需字段
        required = ["instrument_code", "specimen", "results"]
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        specimen = data["specimen"]
        if "barcode" not in specimen:
            raise ValueError("Missing specimen.barcode")

        results = data["results"]
        if not isinstance(results, list) or len(results) == 0:
            raise ValueError("Results must be a non-empty list")

        for r in results:
            if "value" not in r:
                raise ValueError("Each result must have 'value'")
            # 必须有 item_code 或 channel 之一
            if "item_code" not in r and "channel" not in r:
                raise ValueError("Each result must have 'item_code' or 'channel'")

        return data


class AstmParser:
    """解析 ASTM 格式（预留）"""

    @staticmethod
    def parse(payload: bytes | str) -> dict[str, Any]:
        raise NotImplementedError("ASTM parser not yet implemented")


class Hl7Parser:
    """解析 HL7 格式（预留）"""

    @staticmethod
    def parse(payload: bytes | str) -> dict[str, Any]:
        raise NotImplementedError("HL7 parser not yet implemented")
