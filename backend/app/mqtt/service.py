import asyncio
import logging
import json
from datetime import datetime

import aiomqtt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.instrument import Instrument
from app.models.specimen import Specimen
from app.models.test_result import TestResult
from app.models.test_item import TestItem
from app.models.mqtt_log import MqttMessageLog
from app.mqtt.parsers import JsonParser
from app.utils.helpers import judge_abnormal, format_ref_range

logger = logging.getLogger("mqtt_service")
settings = get_settings()

# 仪器最后心跳时间记录 {instrument_code: datetime}
_instrument_heartbeat: dict[str, datetime] = {}


def get_instrument_heartbeat(instrument_code: str) -> datetime | None:
    """获取仪器最后心跳时间"""
    return _instrument_heartbeat.get(instrument_code)


def get_all_heartbeats() -> dict[str, datetime]:
    """获取所有仪器的最后心跳时间"""
    return dict(_instrument_heartbeat)


class MqttService:
    def __init__(self):
        self._running = False

    async def start(self):
        """启动 MQTT 服务，连接失败时静默重试"""
        self._running = True
        logger.info(f"MQTT Service: connecting to {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")

        retry_count = 0
        while self._running:
            try:
                async with aiomqtt.Client(
                    hostname=settings.MQTT_BROKER_HOST,
                    port=settings.MQTT_BROKER_PORT,
                    identifier=settings.MQTT_CLIENT_ID,
                    username=settings.MQTT_USERNAME or None,
                    password=settings.MQTT_PASSWORD or None,
                ) as client:
                    retry_count = 0
                    logger.info("✅ MQTT connected successfully")
                    await client.subscribe(settings.MQTT_TOPIC_RESULT)
                    logger.info(f"Subscribed to: {settings.MQTT_TOPIC_RESULT}")

                    async for message in client.messages:
                        await self._handle_message(message)

            except aiomqtt.MqttError as e:
                retry_count += 1
                if retry_count <= 3:
                    logger.warning(f"MQTT connection failed (attempt {retry_count}): {e}")
                elif retry_count == 4:
                    logger.warning("MQTT: continuing to retry in background (logging suppressed)")
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"MQTT unexpected error: {e}")
                await asyncio.sleep(10)

    async def stop(self):
        self._running = False
        logger.info("MQTT Service stopping")

    async def _handle_message(self, message: aiomqtt.Message):
        topic = str(message.topic)
        payload = message.payload
        logger.info(f"Received: {topic}")

        # 尝试从 topic 提取仪器编码并更新心跳（不管解析是否成功）
        try:
            parts = topic.split("/")
            if len(parts) >= 3 and parts[0] == "lis" and parts[1] == "instrument":
                _instrument_heartbeat[parts[2]] = datetime.now()
        except Exception:
            pass

        async with AsyncSessionLocal() as db:
            try:
                data = JsonParser.parse(payload)
                instrument_code = data["instrument_code"]
                barcode = data["specimen"]["barcode"]
                results = data["results"]

                # 记录仪器心跳时间
                _instrument_heartbeat[instrument_code] = datetime.now()

                instrument = await self._get_instrument(db, instrument_code)
                if not instrument:
                    logger.warning(f"Instrument not found: {instrument_code}")
                    return

                specimen = await self._get_specimen(db, barcode)
                if not specimen:
                    logger.warning(f"Specimen not found: {barcode}")
                    return

                saved_count = 0
                for result in results:
                    item_code = result.get("item_code")
                    channel = result.get("channel")

                    # 方式1: 直接用 item_code 查找
                    test_item = None
                    if item_code:
                        test_item = await self._get_test_item(db, item_code)

                    # 方式2: 用通道号 + 仪器ID 查找
                    if not test_item and channel:
                        test_item = await self._get_test_item_by_channel(db, instrument.id, channel)
                        if test_item:
                            logger.info(f"Channel mapping: instrument={instrument_code} channel={channel} → {test_item.code}")

                    if not test_item:
                        logger.warning(f"Test item not found: item_code={item_code}, channel={channel}")
                        continue

                    value_str = result["value"]
                    result_numeric = None
                    try:
                        result_numeric = float(value_str)
                    except (ValueError, TypeError):
                        pass

                    abnormal_flag = result.get("flag", "N")
                    if abnormal_flag == "N" and result_numeric is not None:
                        abnormal_flag = judge_abnormal(
                            result_numeric,
                            float(test_item.ref_range_low) if test_item.ref_range_low else None,
                            float(test_item.ref_range_high) if test_item.ref_range_high else None,
                        )

                    # 危急值判断
                    is_critical = False
                    if result_numeric is not None:
                        if test_item.critical_high is not None and result_numeric >= float(test_item.critical_high):
                            is_critical = True
                            abnormal_flag = "C"
                        if test_item.critical_low is not None and result_numeric <= float(test_item.critical_low):
                            is_critical = True
                            abnormal_flag = "C"

                    ref_range = format_ref_range(test_item.ref_range_low, test_item.ref_range_high)

                    test_result = TestResult(
                        specimen_id=specimen.id,
                        order_id=specimen.order_id,
                        test_item_id=test_item.id,
                        instrument_id=instrument.id,
                        result_value=value_str,
                        result_numeric=result_numeric,
                        unit=result.get("unit", test_item.unit),
                        ref_range=ref_range,
                        abnormal_flag=abnormal_flag,
                        status="AUTO",
                        raw_data=json.dumps(data, ensure_ascii=False),
                    )
                    db.add(test_result)
                    saved_count += 1

                if saved_count > 0:
                    specimen.status = "TESTING"
                    if specimen.instrument_id is None:
                        specimen.instrument_id = instrument.id

                await db.commit()
                logger.info(f"✅ Saved {saved_count} results for specimen {barcode}")

            except Exception as e:
                logger.error(f"Error processing MQTT message: {e}", exc_info=True)
                await db.rollback()

    async def _get_instrument(self, db: AsyncSession, code: str):
        result = await db.execute(
            select(Instrument).where(Instrument.code == code, Instrument.is_active == True)
        )
        return result.scalar_one_or_none()

    async def _get_specimen(self, db: AsyncSession, barcode: str):
        result = await db.execute(select(Specimen).where(Specimen.barcode == barcode))
        return result.scalar_one_or_none()

    async def _get_test_item(self, db: AsyncSession, code: str):
        result = await db.execute(
            select(TestItem).where(TestItem.code == code, TestItem.is_active == True)
        )
        return result.scalar_one_or_none()

    async def _get_test_item_by_channel(self, db: AsyncSession, instrument_id: int, channel: str):
        """通过仪器ID + 通道号查找检验项目"""
        from app.models.instrument import InstrumentTestItem
        result = await db.execute(
            select(TestItem)
            .join(InstrumentTestItem, InstrumentTestItem.test_item_id == TestItem.id)
            .where(
                InstrumentTestItem.instrument_id == instrument_id,
                InstrumentTestItem.channel_code == str(channel),
                TestItem.is_active == True,
            )
        )
        return result.scalar_one_or_none()


mqtt_service = MqttService()
