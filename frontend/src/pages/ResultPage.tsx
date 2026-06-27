import { useEffect, useState } from 'react';
import { Table, Button, Tag, Space, Select, message, Typography, Card, InputNumber, Modal, Form, Input, Tooltip, Badge } from 'antd';
import { CheckOutlined, LineChartOutlined, ThunderboltOutlined, SearchOutlined, AuditOutlined } from '@ant-design/icons';
import { resultApi, baseDataApi, reportApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

export default function ResultPage() {
  const { user } = useAuth();
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [patientSearch, setPatientSearch] = useState<string>('');
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [manualVisible, setManualVisible] = useState(false);
  const [manualForm] = Form.useForm();
  const [testItems, setTestItems] = useState<any[]>([]);
  const [autoReviewing, setAutoReviewing] = useState(false);
  const [trendVisible, setTrendVisible] = useState(false);
  const [trendData, setTrendData] = useState<any[]>([]);
  const [trendItemName, setTrendItemName] = useState('');

  const fetchResults = async (status?: string) => {
    setLoading(true);
    try {
      const params: any = { page_size: 200 };
      const s = status !== undefined ? status : statusFilter;
      if (s) params.status = s;
      if (patientSearch) params.patient_name = patientSearch;
      const res = await resultApi.list(params);
      setResults(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
    baseDataApi.testItems().then(r => setTestItems(r.data));
  }, [statusFilter]);

  const handleReview = async (action: 'approve' | 'reject') => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要审核的结果');
      return;
    }
    try {
      await resultApi.review({
        result_ids: selectedRowKeys,
        reviewer: user?.real_name || user?.username,
        action,
      });
      message.success(action === 'approve' ? '审核通过' : '已退回');

      if (action === 'approve') {
        const specimenIds = [...new Set(
          results.filter(r => selectedRowKeys.includes(r.id)).map(r => r.specimen_id)
        )];
        let reportCount = 0;
        for (const sid of specimenIds) {
          try {
            await reportApi.generate(sid);
            reportCount++;
          } catch {}
        }
        if (reportCount > 0) {
          message.info(`已自动生成 ${reportCount} 份报告，请前往「报告管理」查看`);
        }
      }

      setSelectedRowKeys([]);
      fetchResults();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '操作失败');
    }
  };

  // 自动审核：审核所有符合条件的结果
  const handleAutoReview = async () => {
    setAutoReviewing(true);
    try {
      const autoResults = results.filter(r => r.status === 'AUTO');
      if (autoResults.length === 0) {
        message.info('没有可自动审核的结果');
        return;
      }

      // 过滤出无异常的结果
      const normalResults = autoResults.filter(
        r => !r.abnormal_flag || r.abnormal_flag === 'N'
      );
      if (normalResults.length === 0) {
        message.warning('所有待审核结果均存在异常标记，需人工审核');
        return;
      }

      const ids = normalResults.map(r => r.id);
      await resultApi.review({
        result_ids: ids,
        reviewer: user?.real_name || user?.username,
        action: 'approve',
      });
      message.success(`自动审核通过 ${ids.length} 条正常结果`);

      // 自动生成报告
      const specimenIds = [...new Set(normalResults.map(r => r.specimen_id))];
      let reportCount = 0;
      for (const sid of specimenIds) {
        try {
          await reportApi.generate(sid);
          reportCount++;
        } catch {}
      }
      if (reportCount > 0) {
        message.info(`已自动生成 ${reportCount} 份报告`);
      }

      fetchResults();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '自动审核失败');
    }
    setAutoReviewing(false);
  };

  // 查看趋势
  const handleViewTrend = (record: any) => {
    const itemName = record.item_name || record.item_code || '未知项目';
    setTrendItemName(itemName);

    // 模拟趋势数据（实际应调用 API）
    const mockTrend = Array.from({ length: 7 }, (_, i) => {
      const date = new Date();
      date.setDate(date.getDate() - (6 - i));
      const base = parseFloat(record.result_value) || 10;
      return {
        date: `${date.getMonth() + 1}/${date.getDate()}`,
        value: +(base + (Math.random() - 0.5) * base * 0.3).toFixed(2),
      };
    });
    setTrendData(mockTrend);
    setTrendVisible(true);
  };

  const handleManual = async (values: any) => {
    try {
      await resultApi.manual({
        ...values,
        operator: user?.real_name || user?.username,
      });
      message.success('录入成功');
      setManualVisible(false);
      manualForm.resetFields();
      fetchResults();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '录入失败');
    }
  };

  // 获取行的样式 —— 危急值红色底、异常橙色底
  const getRowClassName = (record: any) => {
    if (record.is_critical) return 'row-critical';
    if (record.abnormal_flag === 'H' || record.abnormal_flag === 'L' || record.abnormal_flag === 'A') return 'row-abnormal';
    return '';
  };

  const columns = [
    { title: '条码号', dataIndex: 'barcode', key: 'barcode', width: 170 },
    { title: '患者姓名', dataIndex: 'patient_name', key: 'patient_name', width: 90 },
    { title: '患者编号', dataIndex: 'patient_no', key: 'patient_no', width: 110 },
    { title: '项目编码', dataIndex: 'item_code', key: 'item_code', width: 90 },
    { title: '项目名称', dataIndex: 'item_name', key: 'item_name', width: 130 },
    {
      title: '结果', dataIndex: 'result_value', key: 'result_value', width: 120,
      render: (v: string, r: any) => {
        const isAbnormal = r.abnormal_flag === 'H' || r.abnormal_flag === 'L' || r.abnormal_flag === 'A';
        const isCritical = r.is_critical;
        return (
          <span style={{
            color: isCritical ? '#cf1322' : isAbnormal ? '#ff4d4f' : undefined,
            fontWeight: isAbnormal ? 700 : 400,
            fontSize: isCritical ? 15 : undefined,
          }}>
            {isCritical && <ThunderboltOutlined style={{ marginRight: 4 }} />}
            {v || '-'}
          </span>
        );
      },
    },
    { title: '单位', dataIndex: 'unit', key: 'unit', width: 100 },
    { title: '参考范围', dataIndex: 'ref_range', key: 'ref_range', width: 120 },
    {
      title: '异常标记', dataIndex: 'abnormal_flag', key: 'abnormal_flag', width: 90,
      render: (v: string, r: any) => {
        if (r.is_critical) return <Tag color="#cf1322" style={{ fontWeight: 700 }}>⚡ 危急</Tag>;
        if (v === 'H') return <Tag color="red">↑ 偏高</Tag>;
        if (v === 'L') return <Tag color="orange">↓ 偏低</Tag>;
        if (v === 'A') return <Tag color="red">异常</Tag>;
        return <Tag color="green">正常</Tag>;
      },
    },
    { title: '仪器', dataIndex: 'instrument_name', key: 'instrument_name', width: 120 },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 90,
      render: (s: string) => {
        const map: Record<string, { color: string; text: string }> = {
          AUTO: { color: 'blue', text: '待审核' },
          MANUAL: { color: 'cyan', text: '手工' },
          REVIEWED: { color: 'green', text: '已审核' },
          REJECTED: { color: 'red', text: '已退回' },
        };
        const info = map[s] || { color: 'default', text: s };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    {
      title: '时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作', key: 'action', width: 100, fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Tooltip title="查看趋势图">
          <Button
            type="link"
            size="small"
            icon={<LineChartOutlined />}
            onClick={() => handleViewTrend(record)}
          >
            趋势
          </Button>
        </Tooltip>
      ),
    },
  ];

  // 趋势图渲染（使用 div 实现的简易折线图）
  const renderTrendChart = () => {
    if (trendData.length === 0) return null;
    const values = trendData.map(d => d.value);
    const maxVal = Math.max(...values);
    const minVal = Math.min(...values);
    const range = maxVal - minVal || 1;
    const chartHeight = 200;
    const chartWidth = 500;
    const padding = 40;
    const plotWidth = chartWidth - padding * 2;
    const plotHeight = chartHeight - padding * 2;

    const points = trendData.map((d, i) => {
      const x = padding + (i / (trendData.length - 1)) * plotWidth;
      const y = padding + plotHeight - ((d.value - minVal) / range) * plotHeight;
      return { x, y, ...d };
    });

    const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
    const areaD = pathD + ` L ${points[points.length - 1].x} ${padding + plotHeight} L ${points[0].x} ${padding + plotHeight} Z`;

    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
        <Typography.Text strong style={{ fontSize: 16 }}>{trendItemName} — 历史趋势</Typography.Text>
        <svg width={chartWidth} height={chartHeight} style={{ overflow: 'visible' }}>
          {/* 网格线 */}
          {[0, 0.25, 0.5, 0.75, 1].map(ratio => {
            const y = padding + plotHeight - ratio * plotHeight;
            const val = (minVal + ratio * range).toFixed(1);
            return (
              <g key={ratio}>
                <line x1={padding} y1={y} x2={padding + plotWidth} y2={y} stroke="#f0f0f0" />
                <text x={padding - 8} y={y + 4} textAnchor="end" fontSize={11} fill="#8c8c8c">{val}</text>
              </g>
            );
          })}
          {/* 面积填充 */}
          <path d={areaD} fill="#1890ff10" />
          {/* 折线 */}
          <path d={pathD} fill="none" stroke="#1890ff" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
          {/* 数据点 */}
          {points.map((p, i) => (
            <g key={i}>
              <circle cx={p.x} cy={p.y} r={4} fill="#fff" stroke="#1890ff" strokeWidth={2} />
              <text x={p.x} y={p.y - 12} textAnchor="middle" fontSize={11} fill="#262626" fontWeight={600}>{p.value}</text>
            </g>
          ))}
          {/* X 轴标签 */}
          {points.map((p, i) => (
            <text key={`label-${i}`} x={p.x} y={padding + plotHeight + 20} textAnchor="middle" fontSize={11} fill="#8c8c8c">{p.date}</text>
          ))}
        </svg>
      </div>
    );
  };

  return (
    <div>
      <style>{`
        .row-critical td { background: #fff2f0 !important; }
        .row-abnormal td { background: #fff7e6 !important; }
        .row-critical:hover td { background: #ffebe8 !important; }
        .row-abnormal:hover td { background: #fff1d6 !important; }
      `}</style>

      <Typography.Title level={4}>📋 结果审核</Typography.Title>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
          <Space wrap>
            <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 120 }}
              options={[
                { value: '', label: '全部' },
                { value: 'AUTO', label: '待审核' },
                { value: 'REVIEWED', label: '已审核' },
                { value: 'MANUAL', label: '手工录入' },
              ]} />
            <Input.Search
              placeholder="搜索患者姓名"
              style={{ width: 200 }}
              value={patientSearch}
              onChange={(e) => setPatientSearch(e.target.value)}
              onSearch={() => fetchResults()}
              allowClear
              prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
            />
          </Space>
          <Space wrap>
            <Button
              type="primary"
              icon={<AuditOutlined />}
              onClick={handleAutoReview}
              loading={autoReviewing}
              style={{ background: '#722ed1', borderColor: '#722ed1' }}
            >
              自动审核
            </Button>
            <Button type="primary" icon={<CheckOutlined />}
              onClick={() => handleReview('approve')}
              disabled={selectedRowKeys.length === 0}>
              批量审核通过 ({selectedRowKeys.length})
            </Button>
            <Button danger onClick={() => handleReview('reject')}
              disabled={selectedRowKeys.length === 0}>
              批量退回
            </Button>
            <Button onClick={() => setManualVisible(true)}>手工录入</Button>
          </Space>
        </div>
        <Table
          columns={columns}
          dataSource={results}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 50 }}
          scroll={{ x: 1600 }}
          rowClassName={getRowClassName}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys as number[]),
          }}
        />
      </Card>

      {/* 手工录入 Modal */}
      <Modal title="手工录入结果" open={manualVisible}
        onCancel={() => setManualVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setManualVisible(false)}>取消</Button>,
          <Button key="submit" type="primary" onClick={async () => {
            try {
              const values = await manualForm.validateFields();
              await handleManual(values);
            } catch (e) {}
          }}>提交</Button>,
        ]}>
        <Form form={manualForm} layout="vertical" onFinish={handleManual}>
          <Form.Item name="specimen_id" label="标本 ID" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="test_item_id" label="检验项目" rules={[{ required: true }]}>
            <Select
              showSearch optionFilterProp="label"
              options={testItems.map(t => ({ value: t.id, label: `${t.code} - ${t.name}` }))}
              placeholder="选择项目" />
          </Form.Item>
          <Form.Item name="result_value" label="结果值" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="result_numeric" label="数值结果">
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="unit" label="单位">
            <Input />
          </Form.Item>
        </Form>
      </Modal>

      {/* 查看趋势 Modal */}
      <Modal
        title={null}
        open={trendVisible}
        onCancel={() => setTrendVisible(false)}
        footer={[<Button key="close" onClick={() => setTrendVisible(false)}>关闭</Button>]}
        width={600}
      >
        {renderTrendChart()}
      </Modal>
    </div>
  );
}
