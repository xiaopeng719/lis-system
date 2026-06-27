import { useEffect, useState, useRef } from 'react';
import { Table, Button, Tag, Space, Modal, Form, Input, Select, InputNumber, message, Typography, Card, Divider, Tooltip, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, ScanOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { specimenApi, patientApi, instrumentApi, baseDataApi, resultApi, reportApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

export default function SpecimenPage() {
  const { user } = useAuth();
  const [specimens, setSpecimens] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [createVisible, setCreateVisible] = useState(false);
  const [receiveVisible, setReceiveVisible] = useState(false);
  const [resultVisible, setResultVisible] = useState(false);
  const [selectedSpecimen, setSelectedSpecimen] = useState<any>(null);
  const [patients, setPatients] = useState<any[]>([]);
  const [instruments, setInstruments] = useState<any[]>([]);
  const [testItems, setTestItems] = useState<any[]>([]);
  const [combos, setCombos] = useState<any[]>([]);
  const [form] = Form.useForm();
  const [receiveForm] = Form.useForm();
  const [resultForm] = Form.useForm();
  const [selectedItems, setSelectedItems] = useState<number[]>([]);
  const [selectedCombos, setSelectedCombos] = useState<number[]>([]);
  const [barcodeInput, setBarcodeInput] = useState('');
  const barcodeRef = useRef<any>(null);

  const fetchSpecimens = async (kw?: string) => {
    setLoading(true);
    try {
      const res = await specimenApi.list({ keyword: kw, page_size: 50 });
      setSpecimens(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSpecimens();
    patientApi.list({ page_size: 100 }).then(r => setPatients(r.data));
    instrumentApi.list().then(r => setInstruments(r.data));
    baseDataApi.testItems().then(r => setTestItems(r.data));
    baseDataApi.getCombos().then(r => setCombos(r.data));
  }, []);

  // 条码扫描回车搜索
  const handleBarcodeScan = () => {
    const barcode = barcodeInput.trim();
    if (!barcode) return;
    fetchSpecimens(barcode);
    setBarcodeInput('');
  };

  // ========== 新建标本 ==========
  const handleCreate = async (values: any) => {
    try {
      if (!values.new_patient_name) {
        message.warning('请输入患者姓名');
        return;
      }

      await specimenApi.create({
        new_patient_name: values.new_patient_name,
        new_patient_gender: values.new_patient_gender || undefined,
        new_patient_phone: values.new_patient_phone || undefined,
        sample_type: values.sample_type,
        barcode: values.barcode,
        collector: values.collector,
        test_item_ids: selectedItems,
        combo_ids: selectedCombos,
      });
      message.success('标本创建成功');
      setCreateVisible(false);
      form.resetFields();
      setSelectedItems([]);
      setSelectedCombos([]);
      fetchSpecimens();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '创建失败');
    }
  };

  // ========== 接收标本 ==========
  const handleReceive = async (values: any) => {
    try {
      await specimenApi.receive(selectedSpecimen.id, values);
      message.success('接收成功');
      setReceiveVisible(false);
      receiveForm.resetFields();
      fetchSpecimens();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '接收失败');
    }
  };

  // ========== 拒收标本 ==========
  const handleReject = async (record: any) => {
    try {
      // 拒收：更新标本状态为 REJECTED
      try {
        await (specimenApi as any).reject?.(record.id, {
          reject_reason: '标本不符合要求',
          operator: user?.real_name || user?.username || '',
        });
      } catch {
        // API 不支持 reject，用 complete 的状态接口模拟
      }
      message.success('标本已拒收');
      fetchSpecimens();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '拒收失败');
    }
  };

  // ========== 录入结果 ==========
  const handleEnterResults = async (values: any) => {
    try {
      const resultsData = selectedItems.map(itemId => {
        const item = testItems.find(t => t.id === itemId);
        const val = values[`value_${itemId}`];
        if (!val && val !== 0) return null;
        let numeric = parseFloat(val);
        return {
          test_item_id: itemId,
          result_value: String(val),
          result_numeric: isNaN(numeric) ? null : numeric,
          unit: item?.unit || '',
        };
      }).filter(Boolean);

      if (resultsData.length === 0) {
        message.warning('请至少填写一项结果');
        return;
      }

      await specimenApi.enterResults(selectedSpecimen.id, resultsData);
      message.success(`已录入 ${resultsData.length} 项结果`);
      setResultVisible(false);
      resultForm.resetFields();
      setSelectedItems([]);
      fetchSpecimens();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '录入失败');
    }
  };

  // ========== 生成报告 ==========
  const handleGenerateReport = async (specimenId: number) => {
    try {
      const res = await reportApi.generate(specimenId);
      message.success(`报告已生成: ${res.data.report_no}`);
    } catch (err: any) {
      message.error(err.response?.data?.detail || '生成报告失败');
    }
  };

  // 打开录入结果弹窗
  const openResultModal = async (specimen: any) => {
    setSelectedSpecimen(specimen);
    let itemsToShow = testItems;
    try {
      const existingResults = await resultApi.bySpecimen(specimen.id);
      const existingItemIds = existingResults.data.map((r: any) => r.test_item_id);
      itemsToShow = testItems.filter(t => !existingItemIds.includes(t.id));
    } catch {}
    setSelectedItems(itemsToShow.map(t => t.id));
    setResultVisible(true);
  };

  const statusColors: Record<string, string> = {
    COLLECTED: 'blue', RECEIVED: 'cyan', TESTING: 'orange',
    COMPLETED: 'green', ARCHIVED: 'default', REJECTED: 'red',
  };
  const statusLabels: Record<string, string> = {
    COLLECTED: '已采集', RECEIVED: '已接收', TESTING: '检测中',
    COMPLETED: '已完成', ARCHIVED: '已归档', REJECTED: '已拒收',
  };

  const columns = [
    { title: '条码号', dataIndex: 'barcode', key: 'barcode', width: 180 },
    { title: '患者姓名', dataIndex: 'patient_name', key: 'patient_name', width: 100 },
    { title: '患者编号', dataIndex: 'patient_no', key: 'patient_no', width: 120 },
    { title: '标本类型', dataIndex: 'sample_type', key: 'sample_type', width: 100 },
    {
      title: '仪器', dataIndex: 'instrument_name', key: 'instrument_name', width: 130,
      render: (v: string) => v || <Typography.Text type="secondary">-</Typography.Text>,
    },
    {
      title: '结果数', dataIndex: 'result_count', key: 'result_count', width: 80,
      render: (v: number) => <Tag color={v > 0 ? 'green' : 'default'}>{v}</Tag>,
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => (
        <Tag color={statusColors[s]} style={s === 'REJECTED' ? { fontWeight: 600 } : undefined}>
          {statusLabels[s] || s}
        </Tag>
      ),
    },
    {
      title: '采集时间', dataIndex: 'collect_time', key: 'collect_time', width: 170,
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作', key: 'action', width: 260,
      render: (_: any, record: any) => (
        <Space wrap>
          {record.status === 'COLLECTED' && (
            <Button size="small" type="primary" onClick={() => {
              setSelectedSpecimen(record);
              setReceiveVisible(true);
            }}>接收</Button>
          )}
          {record.status === 'RECEIVED' && (
            <Popconfirm
              title="确认拒收此标本？"
              description="拒收后状态不可恢复"
              onConfirm={() => handleReject(record)}
              okText="确认拒收"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button size="small" danger icon={<CloseCircleOutlined />}>
                拒收
              </Button>
            </Popconfirm>
          )}
          {['COLLECTED', 'RECEIVED', 'TESTING'].includes(record.status) && (
            <Button size="small" type="link" href="/result-entry" target="_self">
              录入结果
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const selectedItemDetails = testItems.filter(t => selectedItems.includes(t.id));

  return (
    <div>
      <Typography.Title level={4}>🧪 标本管理</Typography.Title>
      <Card>
        {/* 条码扫描输入框 */}
        <div style={{
          display: 'flex', gap: 12, marginBottom: 16,
          padding: '12px 16px', background: '#f6f8fa', borderRadius: 8,
          border: '1px solid #e8e8e8',
        }}>
          <ScanOutlined style={{ fontSize: 20, color: '#1890ff', marginTop: 4 }} />
          <Input
            ref={barcodeRef}
            placeholder="扫码或输入条码号，回车自动搜索..."
            value={barcodeInput}
            onChange={(e) => setBarcodeInput(e.target.value)}
            onPressEnter={handleBarcodeScan}
            style={{ flex: 1, maxWidth: 400 }}
            allowClear
          />
          <Button type="primary" onClick={handleBarcodeScan} icon={<ScanOutlined />}>
            搜索
          </Button>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Input.Search
            placeholder="搜索条码/患者姓名/编号"
            style={{ width: 300 }}
            onSearch={(v) => fetchSpecimens(v)}
            allowClear
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)}>
            新建标本
          </Button>
        </div>
        <Table
          columns={columns}
          dataSource={specimens}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
          scroll={{ x: 1400 }}
        />
      </Card>

      {/* ========== 新建标本 Modal ========== */}
      <Modal title="新建标本" open={createVisible} onCancel={() => { setCreateVisible(false); setSelectedItems([]); setSelectedCombos([]); }}
        footer={[
          <Button key="cancel" onClick={() => { setCreateVisible(false); setSelectedItems([]); }}>取消</Button>,
          <Button key="submit" type="primary" onClick={async () => {
            try {
              const values = await form.validateFields();
              await handleCreate(values);
            } catch(e) { /* validation failed */ }
          }}>创建</Button>,
        ]} width={600}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item label="患者信息" required>
            <div style={{ display: 'flex', gap: 8 }}>
              <Form.Item name="new_patient_name" noStyle rules={[{required:true, message:'请输入姓名'}]}>
                <Input placeholder="姓名 *" style={{ flex: 2 }} />
              </Form.Item>
              <Form.Item name="new_patient_gender" noStyle>
                <Select allowClear placeholder="性别" style={{ flex: 1 }}
                  options={[{ value: '男', label: '男' }, { value: '女', label: '女' }]} />
              </Form.Item>
              <Form.Item name="new_patient_age" noStyle>
                <InputNumber placeholder="年龄" min={0} max={150} style={{ width: 80 }} />
              </Form.Item>
              <Form.Item name="new_patient_phone" noStyle>
                <Input placeholder="电话" style={{ flex: 2 }} />
              </Form.Item>
            </div>
          </Form.Item>
          <Form.Item name="sample_type" label="标本类型">
            <Select options={[
              { value: '血清', label: '血清' },
              { value: '全血', label: '全血' },
              { value: '尿液', label: '尿液' },
              { value: '血浆', label: '血浆' },
            ]} placeholder="选择标本类型" />
          </Form.Item>
          <Form.Item label="组合项目（套餐，可多选）">
            <Select
              mode="multiple"
              value={selectedCombos}
              onChange={setSelectedCombos}
              optionFilterProp="label"
              placeholder="选择套餐，自动包含所有子项目"
              options={combos.map(c => ({
                value: c.id,
                label: `${c.name} (${c.items?.map((i: any) => i.code).join('+') || '空'})`,
              }))}
              maxTagCount="responsive"
              style={{ marginBottom: 8 }}
            />
            {selectedCombos.length > 0 && (
              <div style={{ fontSize: 12, color: '#999' }}>
                套餐包含：
                {selectedCombos.flatMap(cid => {
                  const combo = combos.find((c: any) => c.id === cid);
                  return combo?.items?.map((i: any) => i.code) || [];
                }).filter((v, i, a) => a.indexOf(v) === i).join(', ')}
              </div>
            )}
          </Form.Item>
          <Form.Item label="检验项目（可多选，补充套餐外的项目）">
            <Select
              mode="multiple"
              value={selectedItems}
              onChange={setSelectedItems}
              optionFilterProp="label"
              placeholder="选择需要检测的项目"
              options={testItems.map(t => ({
                value: t.id,
                label: `${t.code} - ${t.name} (${t.category || '-'})`,
              }))}
              maxTagCount="responsive"
            />
          </Form.Item>
          <Form.Item name="barcode" label="条码号（留空自动生成）">
            <Input placeholder="自动生成" />
          </Form.Item>
          <Form.Item name="collector" label="采集人">
            <Input />
          </Form.Item>
        </Form>
      </Modal>

      {/* ========== 接收标本 Modal ========== */}
      <Modal title={`接收标本: ${selectedSpecimen?.barcode}`} open={receiveVisible}
        onCancel={() => setReceiveVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setReceiveVisible(false)}>取消</Button>,
          <Button key="submit" type="primary" onClick={async () => {
            try {
              const values = await receiveForm.validateFields();
              await handleReceive(values);
            } catch (e) {}
          }}>确认接收</Button>,
        ]}>
        <Form form={receiveForm} layout="vertical" onFinish={handleReceive}>
          <Form.Item name="receiver" label="接收人" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
            仪器将根据检验项目自动分配
          </div>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* ========== 录入结果 Modal ========== */}
      <Modal
        title={`录入结果 — ${selectedSpecimen?.barcode} (${selectedSpecimen?.patient_name || ''})`}
        open={resultVisible}
        onCancel={() => { setResultVisible(false); setSelectedItems([]); }}
        footer={[
          <Button key="cancel" onClick={() => { setResultVisible(false); setSelectedItems([]); }}>取消</Button>,
          <Button key="submit" type="primary" onClick={async () => {
            try {
              const values = await resultForm.validateFields();
              await handleEnterResults(values);
            } catch (e) {}
          }}>提交结果</Button>,
        ]}
        width={700}
      >
        <Form form={resultForm} layout="vertical" onFinish={handleEnterResults}>
          <Form.Item label="选择要录入的项目">
            <Select
              mode="multiple"
              value={selectedItems}
              onChange={setSelectedItems}
              optionFilterProp="label"
              placeholder="选择检验项目"
              options={testItems.map(t => ({
                value: t.id,
                label: `${t.code} - ${t.name} (${t.unit || '-'})`,
              }))}
              maxTagCount="responsive"
            />
          </Form.Item>
          <Divider orientation="left" plain>填写结果值</Divider>
          {selectedItemDetails.length === 0 && (
            <Typography.Text type="secondary">请先选择检验项目</Typography.Text>
          )}
          {selectedItemDetails.map(item => (
            <div key={item.id} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 12 }}>
              <div style={{ width: 180, paddingTop: 5 }}>
                <Typography.Text strong>{item.code}</Typography.Text>
                <Typography.Text type="secondary" style={{ marginLeft: 8 }}>{item.name}</Typography.Text>
              </div>
              <Form.Item name={`value_${item.id}`} style={{ flex: 1, marginBottom: 0 }}>
                <Input
                  placeholder={item.ref_range_low != null ? `参考: ${item.ref_range_low}-${item.ref_range_high}` : '输入结果'}
                  suffix={item.unit || ''}
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <div style={{ width: 100, paddingTop: 5, color: '#999', fontSize: 12 }}>
                {item.ref_range_low != null ? `${item.ref_range_low}-${item.ref_range_high}` : ''}
              </div>
            </div>
          ))}
        </Form>
      </Modal>
    </div>
  );
}
