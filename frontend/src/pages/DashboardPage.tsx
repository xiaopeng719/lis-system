import { useEffect, useState } from 'react';
import { Card, Col, Row, Typography, Tag, Spin, Badge, Tooltip, Button } from 'antd';
import {
  FileTextOutlined, ExperimentOutlined, CheckCircleOutlined,
  AlertOutlined, ThunderboltOutlined, WarningOutlined, CloseCircleOutlined,
  ScanOutlined, FileSearchOutlined, ToolOutlined, PrinterOutlined,
  DashboardOutlined, ClockCircleOutlined, WifiOutlined, DisconnectOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { dashboardApi } from '../services/api';

interface Stats {
  today_orders: number;
  today_specimens: number;
  today_results: number;
  pending_review: number;
  urgent_count: number;
  abnormal_count: number;
  critical_count: number;
}

interface TATStat {
  label: string;
  count: number;
  avg_minutes: number;
}

interface InstrumentStatus {
  instrument_id: number;
  instrument_name: string;
  is_online: boolean;
  last_heartbeat: string;
}

const gradientCards = [
  { key: 'today_orders', title: '今日申请单', icon: <FileTextOutlined />, gradient: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)' },
  { key: 'today_specimens', title: '今日标本', icon: <ExperimentOutlined />, gradient: 'linear-gradient(135deg, #52c41a 0%, #389e0d 100%)' },
  { key: 'today_results', title: '今日结果', icon: <CheckCircleOutlined />, gradient: 'linear-gradient(135deg, #722ed1 0%, #531dab 100%)' },
  { key: 'pending_review', title: '待审核', icon: <AlertOutlined />, gradient: 'linear-gradient(135deg, #faad14 0%, #d48806 100%)' },
  { key: 'urgent_count', title: '急诊/加急', icon: <ThunderboltOutlined />, gradient: 'linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%)' },
  { key: 'abnormal_count', title: '异常结果', icon: <WarningOutlined />, gradient: 'linear-gradient(135deg, #fa8c16 0%, #d46b08 100%)' },
  { key: 'critical_count', title: '危急值', icon: <CloseCircleOutlined />, gradient: 'linear-gradient(135deg, #f5222d 0%, #a8071a 100%)' },
];

const quickActions = [
  { title: '标本接收', desc: '扫描条码接收标本', link: '/specimens', icon: <ScanOutlined style={{ fontSize: 28 }} />, color: '#1890ff' },
  { title: '结果审核', desc: '审核待处理的检验结果', link: '/results', icon: <FileSearchOutlined style={{ fontSize: 28 }} />, color: '#52c41a' },
  { title: '报告打印', desc: '查看和打印检验报告', link: '/reports', icon: <PrinterOutlined style={{ fontSize: 28 }} />, color: '#722ed1' },
  { title: '仪器监控', desc: '查看仪器连接状态', link: '/instruments', icon: <ToolOutlined style={{ fontSize: 28 }} />, color: '#fa8c16' },
];

const instrumentStatusStyles: Record<string, { color: string; bg: string; icon: React.ReactNode; label: string }> = {
  online: { color: '#52c41a', bg: '#f6ffed', icon: <WifiOutlined />, label: '在线' },
  offline: { color: '#ff4d4f', bg: '#fff2f0', icon: <DisconnectOutlined />, label: '离线' },
  standby: { color: '#faad14', bg: '#fffbe6', icon: <ClockCircleOutlined />, label: '待机' },
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats | null>(null);
  const [tatStats, setTatStats] = useState<TATStat[]>([]);
  const [instruments, setInstruments] = useState<InstrumentStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [statsRes, tatRes, instrRes] = await Promise.allSettled([
          dashboardApi.stats(),
          dashboardApi.tat(),
          dashboardApi.instruments(),
        ]);
        if (statsRes.status === 'fulfilled') setStats(statsRes.value.data);
        if (tatRes.status === 'fulfilled') setTatStats(tatRes.value.data);
        if (instrRes.status === 'fulfilled') setInstruments(instrRes.value.data);
      } catch { /* partial failure is ok */ }
      setLoading(false);
    };
    load();
  }, []);

  const tatData: TATStat[] = tatStats;
  const instrData: InstrumentStatus[] = instruments;

  const maxTatCount = Math.max(...tatData.map(t => t.count), 1);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24 }}>
        <DashboardOutlined style={{ fontSize: 24, color: '#1890ff', marginRight: 12 }} />
        <Typography.Title level={4} style={{ margin: 0 }}>检验工作台</Typography.Title>
      </div>

      {/* ====== 渐变统计卡片 ====== */}
      <Row gutter={[16, 16]}>
        {gradientCards.map(card => {
          const value = (stats as any)?.[card.key] || 0;
          const isDanger = card.key === 'critical_count' && value > 0;
          return (
            <Col xs={24} sm={12} lg={8} xl={6} key={card.key}>
              <div
                style={{
                  background: card.gradient,
                  borderRadius: 12,
                  padding: '20px 24px',
                  color: '#fff',
                  position: 'relative',
                  overflow: 'hidden',
                  boxShadow: isDanger
                    ? '0 4px 16px rgba(255, 77, 79, 0.4)'
                    : '0 2px 8px rgba(0, 0, 0, 0.1)',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  cursor: 'default',
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)';
                  (e.currentTarget as HTMLElement).style.boxShadow = isDanger
                    ? '0 6px 20px rgba(255, 77, 79, 0.5)'
                    : '0 4px 16px rgba(0, 0, 0, 0.15)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.transform = 'translateY(0)';
                  (e.currentTarget as HTMLElement).style.boxShadow = isDanger
                    ? '0 4px 16px rgba(255, 77, 79, 0.4)'
                    : '0 2px 8px rgba(0, 0, 0, 0.1)';
                }}
              >
                <div style={{ position: 'absolute', right: 20, top: 20, opacity: 0.2, fontSize: 64 }}>
                  {card.icon}
                </div>
                <div style={{ fontSize: 14, opacity: 0.9, marginBottom: 8 }}>{card.title}</div>
                <div style={{ fontSize: 32, fontWeight: 700, lineHeight: 1 }}>{value}</div>
                {isDanger && (
                  <Badge dot style={{ position: 'absolute', top: 12, right: 12 }}>
                    <Tag color="#fff" style={{ color: '#cf1322', marginTop: 8, fontWeight: 600, fontSize: 12 }}>
                      需要处理
                    </Tag>
                  </Badge>
                )}
              </div>
            </Col>
          );
        })}
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        {/* ====== TAT 统计柱状图 ====== */}
        <Col xs={24} lg={14}>
          <Card
            title={<span><ClockCircleOutlined style={{ marginRight: 8, color: '#1890ff' }} />TAT 统计（平均周转时间）</span>}
            style={{ borderRadius: 12 }}
            styles={{ body: { padding: '16px 24px' } }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {tatData.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 70, fontSize: 13, color: '#595959', textAlign: 'right', flexShrink: 0 }}>
                    {item.label}
                  </div>
                  <div style={{ flex: 1, background: '#f0f0f0', borderRadius: 6, height: 28, position: 'relative', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${Math.min((item.count / maxTatCount) * 100, 100)}%`,
                        height: '100%',
                        background: item.avg_minutes > 50
                          ? 'linear-gradient(90deg, #ff7a45, #ff4d4f)'
                          : item.avg_minutes > 30
                            ? 'linear-gradient(90deg, #ffc53d, #faad14)'
                            : 'linear-gradient(90deg, #95de64, #52c41a)',
                        borderRadius: 6,
                        transition: 'width 0.6s ease',
                        display: 'flex',
                        alignItems: 'center',
                        paddingLeft: 8,
                      }}
                    >
                      <span style={{ fontSize: 12, color: '#fff', fontWeight: 600 }}>
                        {item.count} 标本
                      </span>
                    </div>
                  </div>
                  <div style={{ width: 80, fontSize: 13, fontWeight: 600, color: '#262626', flexShrink: 0 }}>
                    <Tooltip title="平均周转时间">
                      {item.avg_minutes} min
                    </Tooltip>
                  </div>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 16, marginTop: 16, fontSize: 12, color: '#8c8c8c' }}>
              <span><span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 3, background: '#52c41a', marginRight: 4 }} />≤30 min</span>
              <span><span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 3, background: '#faad14', marginRight: 4 }} />30-50 min</span>
              <span><span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 3, background: '#ff4d4f', marginRight: 4 }} />&gt;50 min</span>
            </div>
          </Card>
        </Col>

        {/* ====== 仪器在线状态 ====== */}
        <Col xs={24} lg={10}>
          <Card
            title={<span><ToolOutlined style={{ marginRight: 8, color: '#1890ff' }} />仪器状态</span>}
            style={{ borderRadius: 12 }}
            styles={{ body: { padding: '8px 24px' } }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
              {instrData.length === 0 && (
                <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>
                  暂无仪器数据
                </div>
              )}
              {instrData.map(instr => {
                const status = instr.is_online ? 'online' : 'offline';
                const style = instrumentStatusStyles[status];
                return (
                  <div
                    key={instr.instrument_id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '12px 0',
                      borderBottom: '1px solid #f0f0f0',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div
                        style={{
                          width: 8, height: 8, borderRadius: '50%',
                          background: style.color,
                          boxShadow: instr.is_online ? `0 0 6px ${style.color}` : 'none',
                        }}
                      />
                      <span style={{ fontSize: 14, color: '#262626' }}>{instr.instrument_name}</span>
                    </div>
                    <Tag
                      color={style.color}
                      style={{
                        background: style.bg,
                        border: `1px solid ${style.color}20`,
                        color: style.color,
                        fontWeight: 500,
                      }}
                    >
                      {style.icon} {style.label}
                    </Tag>
                  </div>
                );
              })}
            </div>
            <div style={{ textAlign: 'right', marginTop: 12 }}>
              <Button type="link" size="small" onClick={() => navigate('/instruments')}>
                查看全部 <RightOutlined />
              </Button>
            </div>
          </Card>
        </Col>
      </Row>

      {/* ====== 快捷操作 ====== */}
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            title={<span><ThunderboltOutlined style={{ marginRight: 8, color: '#faad14' }} />快捷操作</span>}
            style={{ borderRadius: 12 }}
          >
            <Row gutter={[16, 16]}>
              {quickActions.map((action, idx) => (
                <Col xs={12} sm={12} md={6} key={idx}>
                  <div
                    onClick={() => navigate(action.link)}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      padding: '24px 16px',
                      borderRadius: 12,
                      border: '1px solid #f0f0f0',
                      background: '#fafafa',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      gap: 12,
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.borderColor = action.color;
                      (e.currentTarget as HTMLElement).style.background = '#fff';
                      (e.currentTarget as HTMLElement).style.boxShadow = `0 4px 12px ${action.color}20`;
                      (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)';
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.borderColor = '#f0f0f0';
                      (e.currentTarget as HTMLElement).style.background = '#fafafa';
                      (e.currentTarget as HTMLElement).style.boxShadow = 'none';
                      (e.currentTarget as HTMLElement).style.transform = 'translateY(0)';
                    }}
                  >
                    <div
                      style={{
                        width: 56, height: 56, borderRadius: 14,
                        background: `${action.color}10`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        color: action.color,
                      }}
                    >
                      {action.icon}
                    </div>
                    <div style={{ fontSize: 15, fontWeight: 600, color: '#262626' }}>{action.title}</div>
                    <div style={{ fontSize: 12, color: '#8c8c8c', textAlign: 'center' }}>{action.desc}</div>
                  </div>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
