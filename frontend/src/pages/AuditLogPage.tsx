import { useEffect, useState } from 'react';
import { Table, Typography, Card, Tag, Space, Input, DatePicker } from 'antd';
import api from '../services/api';

export default function AuditLogPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchLogs = async (kw?: string) => {
    setLoading(true);
    try {
      const res = await api.get('/audit-logs', { params: { page_size: 100, keyword: kw } });
      setLogs(res.data);
    } catch {
      // API 可能还不存在
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLogs(); }, []);

  const actionColors: Record<string, string> = {
    '创建': 'green', '修改': 'blue', '删除': 'red', '登录': 'purple',
    '审核通过': 'green', '审核退回': 'orange',
    CREATE: 'green', UPDATE: 'blue', DELETE: 'red', LOGIN: 'purple', REVIEW: 'orange',
  };

  const columns = [
    { title: '时间', dataIndex: 'created_at', width: 180,
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    { title: '操作人', dataIndex: 'username', width: 100 },
    { title: '操作类型', dataIndex: 'action', width: 100,
      render: (v: string) => <Tag color={actionColors[v] || 'default'}>{v}</Tag>,
    },
    { title: '目标表', dataIndex: 'target_table', width: 120 },
    { title: '目标ID', dataIndex: 'target_id', width: 80 },
    { title: '操作详情', dataIndex: 'detail', ellipsis: true },
    { title: 'IP地址', dataIndex: 'ip_address', width: 130 },
  ];

  return (
    <div>
      <Typography.Title level={4}>📋 操作日志</Typography.Title>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Input.Search placeholder="搜索操作详情..." allowClear style={{ width: 300 }}
            onSearch={(v) => fetchLogs(v)} />
        </div>
        <Table columns={columns} dataSource={logs} rowKey="id" size="small" loading={loading}
          pagination={{ pageSize: 30 }} />
      </Card>
    </div>
  );
}
