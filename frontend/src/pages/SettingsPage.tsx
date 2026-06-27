import { useEffect, useState } from 'react';
import { Card, Form, Input, InputNumber, Switch, Button, message, Typography, Divider, Space } from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import api from '../services/api';

export default function SettingsPage() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const res = await api.get('/settings');
      form.setFieldsValue(res.data);
    } catch {
      message.error('获取设置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSettings(); }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const values = form.getFieldsValue();
      await api.put('/settings', values);
      message.success('设置已保存');
    } catch (err: any) {
      message.error(err.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <Typography.Title level={4}>⚙️ 系统设置</Typography.Title>

      <Card loading={loading}>
        <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
          <Divider orientation="left">报告单设置</Divider>
          <Form.Item name="hospital_name" label="医院名称" extra="显示在检验报告单的抬头">
            <Input placeholder="如：XX市人民医院检验科" />
          </Form.Item>

          <Divider orientation="left">MQTT 设置</Divider>
          <Form.Item name="mqtt_host" label="MQTT Broker 地址">
            <Input placeholder="localhost" />
          </Form.Item>
          <Form.Item name="mqtt_port" label="MQTT 端口">
            <InputNumber min={1} max={65535} style={{ width: 200 }} />
          </Form.Item>

          <Divider orientation="left">业务设置</Divider>
          <Form.Item name="tat_warning_minutes" label="TAT 预警时间（分钟）" extra="超过此时间的标本会标红提醒">
            <InputNumber min={1} max={1440} style={{ width: 200 }} />
          </Form.Item>
          <Form.Item name="auto_review_enabled" label="自动审核" valuePropName="checked" extra="结果全部正常时自动通过审核">
            <Switch />
          </Form.Item>

          <Divider />
          <Form.Item>
            <Space>
              <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
                保存设置
              </Button>
              <Button onClick={fetchSettings}>重置</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
