import { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, Space, Modal, Form, Input, Select, InputNumber, message, Typography, Row, Col, Statistic, Divider } from 'antd';
import { PlusOutlined, LineChartOutlined } from '@ant-design/icons';
import { baseDataApi, instrumentApi } from '../services/api';
import api from '../services/api';

export default function QCPage() {
  const [qcRecords, setQcRecords] = useState<any[]>([]);
  const [testItems, setTestItems] = useState<any[]>([]);
  const [instruments, setInstruments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [createVisible, setCreateVisible] = useState(false);
  const [form] = Form.useForm();
  const [selectedItem, setSelectedItem] = useState<number | null>(null);
  const [chartData, setChartData] = useState<any[]>([]);

  const fetchQC = async () => {
    setLoading(true);
    try {
      const res = await api.get('/qc/records', { params: { page_size: 100 } });
      setQcRecords(res.data);
    } catch {
      // API 可能还不存在
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQC();
    baseDataApi.testItems().then(r => setTestItems(r.data));
    instrumentApi.list().then(r => setInstruments(r.data));
  }, []);

  const handleCreate = async (values: any) => {
    try {
      await api.post('/qc/records', values);
      message.success('质控数据录入成功');
      setCreateVisible(false);
      form.resetFields();
      fetchQC();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '录入失败');
    }
  };

  // 简单的 L-J 图数据（最近20条同项目记录）
  const loadChartData = async (itemId: number) => {
    setSelectedItem(itemId);
    try {
      const res = await api.get('/qc/records', { params: { test_item_id: itemId, page_size: 20 } });
      setChartData(res.data);
    } catch {}
  };

  const columns = [
    { title: '仪器', dataIndex: 'instrument_name', width: 120 },
    { title: '项目', dataIndex: 'item_name', width: 120 },
    { title: '质控水平', dataIndex: 'qc_level', width: 80, render: (v: string) => <Tag>{v}</Tag> },
    { title: '质控批号', dataIndex: 'qc_lot', width: 100 },
    { title: '结果值', dataIndex: 'result_value', width: 100, render: (v: number) => v?.toFixed(2) },
    { title: '靶值', dataIndex: 'mean_value', width: 80, render: (v: number) => v?.toFixed(2) },
    { title: 'SD', dataIndex: 'sd_value', width: 80, render: (v: number) => v?.toFixed(2) },
    { title: '偏差', dataIndex: 'deviation', width: 80, render: (v: number) => v ? `${v.toFixed(2)}%` : '-' },
    {
      title: '状态', dataIndex: 'is_in_control', width: 80,
      render: (v: boolean, record: any) => v
        ? <Tag color="green">在控</Tag>
        : <Tag color="red">失控{record.rule_violated ? ` (${record.rule_violated})` : ''}</Tag>,
    },
    { title: '操作人', dataIndex: 'operator', width: 80 },
    {
      title: '时间', dataIndex: 'record_time', width: 160,
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
  ];

  // 统计
  const totalRecords = qcRecords.length;
  const inControlCount = qcRecords.filter(r => r.is_in_control).length;
  const outControlCount = totalRecords - inControlCount;

  return (
    <div>
      <Typography.Title level={4}>🧪 质控管理</Typography.Title>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card><Statistic title="总记录数" value={totalRecords} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="在控" value={inControlCount} valueStyle={{ color: '#52c41a' }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="失控" value={outControlCount} valueStyle={{ color: outControlCount > 0 ? '#ff4d4f' : undefined }} /></Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="在控率" value={totalRecords > 0 ? ((inControlCount / totalRecords) * 100).toFixed(1) : '0'} suffix="%" />
          </Card>
        </Col>
      </Row>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Space>
            <Select placeholder="查看 L-J 图" allowClear style={{ width: 200 }}
              onChange={(v) => v ? loadChartData(v) : setChartData([])}
              options={testItems.map(t => ({ value: t.id, label: `${t.code} - ${t.name}` }))} />
            {chartData.length > 0 && (
              <span style={{ fontSize: 12, color: '#999' }}>
                最近 {chartData.length} 条记录，在控 {chartData.filter(r => r.is_in_control).length} 条
              </span>
            )}
          </Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)}>录入质控</Button>
        </div>

        {/* 简易 L-J 图 */}
        {chartData.length > 0 && (
          <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }} title={<><LineChartOutlined /> Levey-Jennings 趋势图</>}>
            <div style={{ display: 'flex', alignItems: 'flex-end', height: 120, gap: 4, padding: '0 20px' }}>
              {(() => {
                const mean = chartData[0]?.mean_value || 0;
                const sd = chartData[0]?.sd_value || 1;
                const min = mean - 3 * sd;
                const max = mean + 3 * sd;
                const range = max - min || 1;
                return chartData.map((r, i) => {
                  const val = r.result_value || 0;
                  const pct = Math.max(5, Math.min(95, ((val - min) / range) * 100));
                  let color = '#52c41a';
                  if (Math.abs(val - mean) > 2 * sd) color = '#faad14';
                  if (Math.abs(val - mean) > 3 * sd) color = '#ff4d4f';
                  if (!r.is_in_control) color = '#ff4d4f';
                  return (
                    <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <span style={{ fontSize: 10, color: '#999' }}>{val.toFixed(1)}</span>
                      <div style={{
                        width: '60%', height: `${pct}%`, minHeight: 4,
                        background: color, borderRadius: 2,
                        marginTop: 'auto',
                      }} />
                    </div>
                  );
                });
              })()}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#999', marginTop: 4, padding: '0 20px' }}>
              <span>+3SD</span>
              <span>+2SD</span>
              <span>靶值</span>
              <span>-2SD</span>
              <span>-3SD</span>
            </div>
          </Card>
        )}

        <Table columns={columns} dataSource={qcRecords} rowKey="id" size="small" loading={loading}
          pagination={{ pageSize: 20 }} />
      </Card>

      <Modal title="录入质控数据" open={createVisible}
        onCancel={() => { setCreateVisible(false); form.resetFields(); }}
        onOk={async () => { try { const v = await form.validateFields(); await handleCreate(v); } catch(e){} }}
        okText="录入" destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="instrument_id" label="仪器" rules={[{required:true}]}>
            <Select options={instruments.map(i => ({value: i.id, label: `${i.name} (${i.code})`}))} />
          </Form.Item>
          <Form.Item name="test_item_id" label="检验项目" rules={[{required:true}]}>
            <Select showSearch optionFilterProp="label"
              options={testItems.map(t => ({value: t.id, label: `${t.code} - ${t.name}`}))} />
          </Form.Item>
          <Form.Item name="qc_level" label="质控水平" rules={[{required:true}]}>
            <Select options={[{value:'L1',label:'水平1 (正常)'},{value:'L2',label:'水平2 (异常)'}]} />
          </Form.Item>
          <Form.Item name="qc_lot" label="质控批号"><Input /></Form.Item>
          <Space>
            <Form.Item name="result_value" label="结果值" rules={[{required:true}]}><InputNumber style={{width:120}} /></Form.Item>
            <Form.Item name="mean_value" label="靶值" rules={[{required:true}]}><InputNumber style={{width:120}} /></Form.Item>
            <Form.Item name="sd_value" label="SD" rules={[{required:true}]}><InputNumber style={{width:120}} step={0.01} /></Form.Item>
          </Space>
          <Form.Item name="operator" label="操作人"><Input /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
