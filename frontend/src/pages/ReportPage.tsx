import { useEffect, useState } from 'react';
import { Table, Button, Tag, Space, Modal, message, Typography, Card, Tooltip } from 'antd';
import { FileTextOutlined, EyeOutlined, CheckOutlined, PrinterOutlined, CopyOutlined } from '@ant-design/icons';
import { reportApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

export default function ReportPage() {
  const { user } = useAuth();
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewReportId, setPreviewReportId] = useState<number | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [batchPrinting, setBatchPrinting] = useState(false);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const res = await reportApi.list({ page_size: 50 });
      setReports(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchReports(); }, []);

  const handlePreview = async (reportId: number) => {
    try {
      const res = await reportApi.get(reportId);
      setPreviewHtml(res.data.report_html);
      setPreviewReportId(reportId);
      setPreviewVisible(true);
    } catch {
      message.error('获取报告失败');
    }
  };

  const handleReview = async (reportId: number) => {
    try {
      await reportApi.review(reportId, user?.real_name || user?.username || '');
      message.success('审核通过');
      fetchReports();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '审核失败');
    }
  };

  const handlePrint = () => {
    if (!previewHtml) return;
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(previewHtml);
      printWindow.document.close();
      setTimeout(() => printWindow.print(), 300);
    }
  };

  const handlePrintDirect = async (reportId: number) => {
    try {
      const res = await reportApi.get(reportId);
      const printWindow = window.open('', '_blank');
      if (printWindow) {
        printWindow.document.write(res.data.report_html);
        printWindow.document.close();
        setTimeout(() => printWindow.print(), 300);
      }
    } catch {
      message.error('获取报告失败');
    }
  };

  // 批量打印
  const handleBatchPrint = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要打印的报告');
      return;
    }
    setBatchPrinting(true);
    try {
      let allHtml = '';
      let successCount = 0;
      for (const reportId of selectedRowKeys) {
        try {
          const res = await reportApi.get(reportId);
          allHtml += `<div style="page-break-after: always;">${res.data.report_html}</div>`;
          successCount++;
        } catch {
          // skip failed ones
        }
      }
      if (allHtml) {
        const printWindow = window.open('', '_blank');
        if (printWindow) {
          printWindow.document.write(allHtml);
          printWindow.document.close();
          setTimeout(() => printWindow.print(), 500);
        }
        message.success(`已准备 ${successCount} 份报告打印`);
      } else {
        message.error('获取报告内容失败');
      }
    } catch {
      message.error('批量打印失败');
    }
    setBatchPrinting(false);
  };

  // 计算年龄的辅助函数
  const calcAge = (birthDate: string | null | undefined): string => {
    if (!birthDate) return '-';
    const birth = new Date(birthDate);
    const now = new Date();
    let age = now.getFullYear() - birth.getFullYear();
    const m = now.getMonth() - birth.getMonth();
    if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) age--;
    return `${age}岁`;
  };

  const statusColors: Record<string, string> = {
    DRAFT: 'blue', REVIEWED: 'green', PRINTED: 'purple', REVOKED: 'red',
  };
  const statusLabels: Record<string, string> = {
    DRAFT: '草稿', REVIEWED: '已审核', PRINTED: '已打印', REVOKED: '已作废',
  };

  const columns = [
    { title: '报告单号', dataIndex: 'report_no', key: 'report_no', width: 200 },
    { title: '患者姓名', dataIndex: 'patient_name', key: 'patient_name', width: 100 },
    { title: '患者编号', dataIndex: 'patient_no', key: 'patient_no', width: 120 },
    {
      title: '性别', dataIndex: 'patient_gender', key: 'patient_gender', width: 70,
      render: (v: string) => {
        if (v === '男') return <Tag color="blue">男</Tag>;
        if (v === '女') return <Tag color="magenta">女</Tag>;
        return <Tag>{v || '-'}</Tag>;
      },
    },
    {
      title: '年龄', dataIndex: 'patient_age', key: 'patient_age', width: 80,
      render: (v: number | null, record: any) => {
        if (v != null) return `${v}岁`;
        // 尝试用 birth_date 计算
        if (record.patient_birth_date) return calcAge(record.patient_birth_date);
        return '-';
      },
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => <Tag color={statusColors[s]}>{statusLabels[s] || s}</Tag>,
    },
    { title: '审核人', dataIndex: 'reviewed_by', key: 'reviewed_by', width: 100 },
    {
      title: '生成时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作', key: 'action', width: 280,
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => handlePreview(record.id)}>
            预览
          </Button>
          {record.status === 'DRAFT' && (
            <Button size="small" type="primary" icon={<CheckOutlined />}
              onClick={() => handleReview(record.id)}>
              审核
            </Button>
          )}
          <Button size="small" icon={<PrinterOutlined />}
            onClick={() => handlePrintDirect(record.id)}>
            打印
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>📄 报告管理</Typography.Title>
      <Card>
        {/* 工具栏 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
          <Space>
            <Typography.Text type="secondary">
              共 {reports.length} 份报告
              {selectedRowKeys.length > 0 && ` · 已选 ${selectedRowKeys.length} 份`}
            </Typography.Text>
          </Space>
          <Space>
            <Tooltip title="批量打印所选报告">
              <Button
                type="primary"
                icon={<PrinterOutlined />}
                onClick={handleBatchPrint}
                loading={batchPrinting}
                disabled={selectedRowKeys.length === 0}
              >
                批量打印 ({selectedRowKeys.length})
              </Button>
            </Tooltip>
          </Space>
        </div>
        <Table
          columns={columns}
          dataSource={reports}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys as number[]),
          }}
        />
      </Card>

      {/* 报告预览 Modal（A4 样式） */}
      <Modal
        title={null}
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        width={850}
        styles={{ body: { padding: 0, background: '#f0f0f0' } }}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>关闭</Button>,
          <Button key="print" type="primary" icon={<PrinterOutlined />} onClick={handlePrint}>
            打印
          </Button>,
        ]}
      >
        <div style={{
          background: '#fff',
          boxShadow: '0 2px 12px rgba(0,0,0,0.15)',
          margin: '16px auto',
          maxWidth: '210mm',
          minHeight: '297mm',
        }}>
          <div dangerouslySetInnerHTML={{ __html: previewHtml }} />
        </div>
      </Modal>
    </div>
  );
}
