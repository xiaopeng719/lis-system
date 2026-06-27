import { useEffect, useState } from 'react';
import { Table, Button, Tag, Space, Modal, Form, Input, Select, message, Typography, Card, Popconfirm, InputNumber } from 'antd';
import { PlusOutlined, DeleteOutlined, SettingOutlined } from '@ant-design/icons';
import { instrumentApi, baseDataApi } from '../services/api';

export default function InstrumentPage() {
  const [instruments, setInstruments] = useState<any[]>([]);
  const [testItems, setTestItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [createVisible, setCreateVisible] = useState(false);
  const [channelVisible, setChannelVisible] = useState(false);
  const [selectedInstrument, setSelectedInstrument] = useState<any>(null);
  const [channels, setChannels] = useState<any[]>([]);
  const [form] = Form.useForm();
  const [channelForm] = Form.useForm();

  const fetchInstruments = async () => {
    setLoading(true);
    try {
      const res = await instrumentApi.list();
      setInstruments(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInstruments();
    baseDataApi.testItems().then(r => setTestItems(r.data));
  }, []);

  const handleCreate = async (values: any) => {
    try {
      await instrumentApi.create(values);
      message.success('仪器添加成功');
      setCreateVisible(false);
      form.resetFields();
      fetchInstruments();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '添加失败');
    }
  };

  // ---- 通道号管理 ----
  const openChannels = async (instrument: any) => {
    setSelectedInstrument(instrument);
    try {
      const res = await instrumentApi.getChannels(instrument.id);
      setChannels(res.data);
    } catch {
      setChannels([]);
    }
    setChannelVisible(true);
  };

  const handleCreateChannel = async (values: any) => {
    try {
      await instrumentApi.createChannel(selectedInstrument.id, values);
      message.success('通道号创建成功');
      channelForm.resetFields();
      const res = await instrumentApi.getChannels(selectedInstrument.id);
      setChannels(res.data);
    } catch (err: any) {
      message.error(err.response?.data?.detail || '创建失败');
    }
  };

  const handleDeleteChannel = async (channelId: number) => {
    try {
      await instrumentApi.deleteChannel(selectedInstrument.id, channelId);
      message.success('已删除');
      const res = await instrumentApi.getChannels(selectedInstrument.id);
      setChannels(res.data);
    } catch (err: any) {
      message.error(err.response?.data?.detail || '删除失败');
    }
  };

  const columns = [
    { title: '编码', dataIndex: 'code', key: 'code', width: 120 },
    { title: '名称', dataIndex: 'name', key: 'name', width: 160 },
    { title: '型号', dataIndex: 'model', key: 'model', width: 120 },
    { title: '厂商', dataIndex: 'manufacturer', key: 'manufacturer', width: 140 },
    { title: '数据格式', dataIndex: 'data_format', key: 'data_format', width: 100,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    { title: '状态', dataIndex: 'is_active', key: 'is_active', width: 80,
      render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '启用' : '停用'}</Tag>,
    },
    {
      title: '操作', key: 'action', width: 120,
      render: (_: any, record: any) => (
        <Button size="small" icon={<SettingOutlined />} onClick={() => openChannels(record)}>
          通道号
        </Button>
      ),
    },
  ];

  const channelColumns = [
    { title: '通道号', dataIndex: 'channel_code', width: 100,
      render: (v: string) => <Tag color="blue">{v}</Tag>,
    },
    { title: '项目编码', dataIndex: 'item_code', width: 100 },
    { title: '项目名称', dataIndex: 'item_name', width: 120 },
    { title: '单位', dataIndex: 'unit', width: 80 },
    {
      title: '操作', key: 'action', width: 80,
      render: (_: any, record: any) => (
        <Popconfirm title="确认删除此通道号映射？" onConfirm={() => handleDeleteChannel(record.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>🔧 仪器管理</Typography.Title>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)}>
            添加仪器
          </Button>
        </div>
        <Table columns={columns} dataSource={instruments} rowKey="id" loading={loading} size="small" />
      </Card>

      {/* 添加仪器 */}
      <Modal title="添加仪器" open={createVisible} onCancel={() => setCreateVisible(false)}
        onOk={async () => { try { const v = await form.validateFields(); await handleCreate(v); } catch(e){} }}
        okText="添加" destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="code" label="仪器编码" rules={[{ required: true }]}>
            <Input placeholder="如 CBC-001" />
          </Form.Item>
          <Form.Item name="name" label="仪器名称" rules={[{ required: true }]}>
            <Input placeholder="如 迈瑞BC-6800" />
          </Form.Item>
          <Form.Item name="model" label="型号"><Input /></Form.Item>
          <Form.Item name="manufacturer" label="厂商"><Input /></Form.Item>
          <Form.Item name="data_format" label="数据格式" initialValue="JSON">
            <Input placeholder="JSON / ASTM / HL7" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 通道号管理 */}
      <Modal
        title={`通道号管理 — ${selectedInstrument?.name} (${selectedInstrument?.code})`}
        open={channelVisible}
        onCancel={() => { setChannelVisible(false); setSelectedInstrument(null); setChannels([]); }}
        footer={null}
        width={700}
        destroyOnClose
      >
        <div style={{ marginBottom: 16, padding: 12, background: '#f0f5ff', borderRadius: 6, fontSize: 13 }}>
          <strong>说明：</strong>为仪器的每个通道号绑定对应的 LIS 检验项目。
          仪器发送数据时用通道号（如 1、2、3），LIS 自动映射到项目编码（如 ALT、WBC）。
          <br />
          <strong>MQTT 格式：</strong><code>{'{"results": [{"channel": "1", "value": "25"}]}'}</code>
        </div>

        <Form form={channelForm} layout="inline" style={{ marginBottom: 16 }}
          onFinish={handleCreateChannel}>
          <Form.Item name="channel_code" rules={[{ required: true, message: '请输入通道号' }]}>
            <Input placeholder="通道号 (如 1, 2, 3)" style={{ width: 120 }} />
          </Form.Item>
          <Form.Item name="test_item_id" rules={[{ required: true, message: '请选择项目' }]}>
            <Select placeholder="选择检验项目" style={{ width: 200 }} showSearch optionFilterProp="label"
              options={testItems.map(t => ({ value: t.id, label: `${t.code} - ${t.name}` }))} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>添加</Button>
          </Form.Item>
        </Form>

        <Table columns={channelColumns} dataSource={channels} rowKey="id" size="small" pagination={false} />
      </Modal>
    </div>
  );
}
