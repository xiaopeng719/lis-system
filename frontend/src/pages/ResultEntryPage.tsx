import { useEffect, useState } from 'react';
import { Card, Select, Table, Button, Input, Tag, message, Typography, Space, Alert, Divider, Empty } from 'antd';
import { SaveOutlined, SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { specimenApi, resultApi, reportApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

export default function ResultEntryPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [specimens, setSpecimens] = useState<any[]>([]);
  const [selectedSpecimenId, setSelectedSpecimenId] = useState<number | null>(null);
  const [specimenInfo, setSpecimenInfo] = useState<any>(null);
  const [testItems, setTestItems] = useState<any[]>([]);
  const [resultValues, setResultValues] = useState<Record<number, string>>({});
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [specimenKeyword, setSpecimenKeyword] = useState('');

  // 加载标本列表（只显示可录入的）
  const fetchSpecimens = async (kw?: string) => {
    try {
      const res = await specimenApi.list({ keyword: kw, page_size: 100 });
      // 只显示可录入结果的状态
      setSpecimens(res.data.filter((s: any) =>
        ['COLLECTED', 'RECEIVED', 'TESTING'].includes(s.status)
      ));
    } catch {}
  };

  useEffect(() => { fetchSpecimens(); }, []);

  // 选择标本后加载关联项目
  const handleSelectSpecimen = async (specimenId: number) => {
    setSelectedSpecimenId(specimenId);
    setResultValues({});
    setLoading(true);
    try {
      const res = await specimenApi.getTestItems(specimenId);
      setSpecimenInfo(res.data);
      setTestItems(res.data.test_items.filter((t: any) => !t.already_entered));
    } catch (err: any) {
      message.error('获取检验项目失败');
      setTestItems([]);
      setSpecimenInfo(null);
    } finally {
      setLoading(false);
    }
  };

  // 提交结果
  const handleSubmit = async () => {
    if (!selectedSpecimenId) return;

    const entries = testItems
      .filter(item => resultValues[item.id] !== undefined && resultValues[item.id] !== '')
      .map(item => {
        const val = resultValues[item.id];
        let numeric = parseFloat(val);
        return {
          test_item_id: item.id,
          result_value: val,
          result_numeric: isNaN(numeric) ? null : numeric,
          unit: item.unit || '',
        };
      });

    if (entries.length === 0) {
      message.warning('请至少填写一项结果');
      return;
    }

    setSaving(true);
    try {
      await specimenApi.enterResults(selectedSpecimenId, entries);
      message.success(`已录入 ${entries.length} 项结果`);

      // 刷新：重新获取关联项目（排除已录入的）
      const res = await specimenApi.getTestItems(selectedSpecimenId);
      setSpecimenInfo(res.data);
      const remaining = res.data.test_items.filter((t: any) => !t.already_entered);
      setTestItems(remaining);
      setResultValues({});

      // 刷新标本列表
      fetchSpecimens(specimenKeyword || undefined);

      return remaining.length === 0; // 返回是否全部录入完毕
    } catch (err: any) {
      message.error(err.response?.data?.detail || '录入失败');
      return false;
    } finally {
      setSaving(false);
    }
  };

  // 提交并跳转审核
  const handleSubmitAndReview = async () => {
    const allDone = await handleSubmit();
    if (allDone !== false) {
      navigate('/results');
    }
  };

  // 一键生成报告
  const handleGenerateReport = async () => {
    if (!selectedSpecimenId) return;
    try {
      const res = await reportApi.generate(selectedSpecimenId);
      message.success(`报告已生成: ${res.data.report_no}`);
    } catch (err: any) {
      message.error(err.response?.data?.detail || '生成报告失败');
    }
  };

  const statusColors: Record<string, string> = {
    COLLECTED: 'blue', RECEIVED: 'cyan', TESTING: 'orange', COMPLETED: 'green',
  };
  const statusLabels: Record<string, string> = {
    COLLECTED: '已采集', RECEIVED: '已接收', TESTING: '检测中', COMPLETED: '已完成',
  };

  const specimenOptions = specimens.map(s => ({
    value: s.id,
    label: `${s.barcode}  ${s.patient_name || ''}  ${s.patient_no || ''}  [${statusLabels[s.status] || s.status}]`,
  }));

  const columns = [
    {
      title: '项目编码', dataIndex: 'code', key: 'code', width: 100,
      render: (v: string) => <Typography.Text strong>{v}</Typography.Text>,
    },
    { title: '项目名称', dataIndex: 'name', key: 'name', width: 140 },
    { title: '单位', dataIndex: 'unit', key: 'unit', width: 120 },
    {
      title: '参考范围', key: 'ref_range', width: 140,
      render: (_: any, record: any) => {
        if (record.ref_range_low != null && record.ref_range_high != null)
          return `${record.ref_range_low} - ${record.ref_range_high}`;
        if (record.ref_range_low != null) return `≥ ${record.ref_range_low}`;
        if (record.ref_range_high != null) return `≤ ${record.ref_range_high}`;
        return '-';
      },
    },
    {
      title: '结果值', key: 'result', width: 250,
      render: (_: any, record: any) => (
        <Input
          value={resultValues[record.id] || ''}
          onChange={e => setResultValues(prev => ({ ...prev, [record.id]: e.target.value }))}
          placeholder={record.ref_range_low != null ? `参考: ${record.ref_range_low}-${record.ref_range_high}` : '输入结果'}
          suffix={record.unit || ''}
          onPressEnter={handleSubmit}
          style={{ width: '100%' }}
        />
      ),
    },
  ];

  // 已有结果的项目
  const alreadyEnteredItems = specimenInfo?.test_items?.filter((t: any) => t.already_entered) || [];

  return (
    <div>
      <Typography.Title level={4}>✏️ 结果录入</Typography.Title>

      {/* 标本选择区 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <Typography.Text strong style={{ whiteSpace: 'nowrap' }}>选择标本：</Typography.Text>
          <Select
            showSearch
            style={{ flex: 1, minWidth: 400 }}
            placeholder="搜索条码/患者姓名/编号"
            value={selectedSpecimenId}
            onChange={handleSelectSpecimen}
            options={specimenOptions}
            filterOption={(input, option) =>
              (option?.label as string)?.toLowerCase().includes(input.toLowerCase()) ?? false
            }
            notFoundContent="暂无可录入的标本"
            allowClear
            onClear={() => {
              setSelectedSpecimenId(null);
              setSpecimenInfo(null);
              setTestItems([]);
              setResultValues({});
            }}
          />
          {specimenInfo && (
            <Space>
              <Tag color={statusColors[specimenInfo.status]}>
                {statusLabels[specimenInfo.status] || specimenInfo.status}
              </Tag>
              <Typography.Text type="secondary">
                条码: {specimenInfo.barcode}
              </Typography.Text>
            </Space>
          )}
        </div>
      </Card>

      {/* 结果录入区 */}
      {selectedSpecimenId && (
        <Card
          title={
            <Space>
              <span>检验项目录入</span>
              {specimenInfo && (
                <Tag color="blue">
                  已录入 {alreadyEnteredItems.length} 项 / 待录入 {testItems.length} 项
                </Tag>
              )}
            </Space>
          }
          extra={
            <Space>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSubmitAndReview}
                loading={saving}
                disabled={testItems.length === 0}
              >
                保存并审核
              </Button>
              <Button
                onClick={handleSubmit}
                loading={saving}
                disabled={testItems.length === 0}
              >
                仅保存
              </Button>
            </Space>
          }
        >
          {testItems.length === 0 && alreadyEnteredItems.length > 0 ? (
            <Alert
              message="所有项目已录入完毕"
              description="可以前往「结果审核」页面审核，或直接生成报告。"
              type="success"
              showIcon
            />
          ) : testItems.length === 0 ? (
            <Empty description="该标本没有关联的检验项目" />
          ) : (
            <Table
              columns={columns}
              dataSource={testItems}
              rowKey="id"
              loading={loading}
              size="middle"
              pagination={false}
              scroll={{ x: 800 }}
            />
          )}

          {/* 已录入的项目展示 */}
          {alreadyEnteredItems.length > 0 && (
            <>
              <Divider orientation="left" plain style={{ fontSize: 13, color: '#999' }}>
                已录入的项目
              </Divider>
              <Table
                columns={[
                  { title: '项目编码', dataIndex: 'code', key: 'code', width: 100 },
                  { title: '项目名称', dataIndex: 'name', key: 'name', width: 140 },
                  {
                    title: '结果值', key: 'result', width: 150,
                    render: (_: any, record: any) => {
                      const val = record.result_value;
                      const flag = record.abnormal_flag;
                      const isAbnormal = flag === 'H' || flag === 'L' || flag === 'A';
                      return <span style={{ color: isAbnormal ? '#ff4d4f' : '#333', fontWeight: isAbnormal ? 700 : 400 }}>{val || '-'}</span>;
                    },
                  },
                  { title: '单位', dataIndex: 'unit', key: 'unit', width: 100 },
                  {
                    title: '异常标记', key: 'flag', width: 90,
                    render: (_: any, record: any) => {
                      const flag = record.abnormal_flag;
                      if (flag === 'H') return <Tag color="red">↑ 偏高</Tag>;
                      if (flag === 'L') return <Tag color="orange">↓ 偏低</Tag>;
                      if (flag === 'A') return <Tag color="red">异常</Tag>;
                      return <Tag color="green">正常</Tag>;
                    },
                  },
                ]}
                dataSource={alreadyEnteredItems}
                rowKey="id"
                size="small"
                pagination={false}
              />
            </>
          )}
        </Card>
      )}

      {!selectedSpecimenId && (
        <Card>
          <Empty description="请先选择一个标本开始录入结果" />
        </Card>
      )}
    </div>
  );
}
