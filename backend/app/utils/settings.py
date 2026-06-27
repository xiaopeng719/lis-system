import json
import os


SETTINGS_PATH = "/root/workspace/backend/data/settings.json"

DEFAULT_SETTINGS = {
    "hospital_name": "XX医院检验科",
    "mqtt_host": "localhost",
    "mqtt_port": 1883,
    "tat_warning_minutes": 60,
    "auto_review_enabled": True,
}


def _ensure_data_dir():
    """确保数据目录存在"""
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)


def _load_settings() -> dict:
    """从文件加载配置，若文件不存在则返回默认配置"""
    if not os.path.exists(SETTINGS_PATH):
        return dict(DEFAULT_SETTINGS)
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_settings(settings: dict):
    """将配置保存到文件"""
    _ensure_data_dir()
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def get_setting(key: str):
    """获取单个配置项"""
    settings = _load_settings()
    return settings.get(key)


def set_setting(key: str, value):
    """设置单个配置项并自动保存到文件"""
    settings = _load_settings()
    settings[key] = value
    _save_settings(settings)


def get_all_settings() -> dict:
    """获取所有配置"""
    return _load_settings()
