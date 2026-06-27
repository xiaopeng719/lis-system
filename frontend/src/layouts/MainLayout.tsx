import { useState, useEffect } from 'react';
import { Layout, Menu, Button, Avatar, Dropdown, Typography, Tag, Badge, List, Empty, Popover, message } from 'antd';
import {
  DashboardOutlined,
  ExperimentOutlined,
  EditOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  ToolOutlined,
  DatabaseOutlined,
  LogoutOutlined,
  UserOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BugOutlined,
  AuditOutlined,
  TeamOutlined,
  BellOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { dashboardApi } from '../services/api';

const { Header, Sider, Content } = Layout;

const allMenuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '检验工作台', perm: null },
  { key: '/specimens', icon: <ExperimentOutlined />, label: '标本管理', perm: 'specimen:view' },
  { key: '/result-entry', icon: <EditOutlined />, label: '结果录入', perm: 'result:enter' },
  { key: '/results', icon: <FileSearchOutlined />, label: '结果审核', perm: 'result:review' },
  { key: '/reports', icon: <FileTextOutlined />, label: '报告管理', perm: 'report:view' },
  { key: '/instruments', icon: <ToolOutlined />, label: '仪器管理', perm: 'instrument:manage' },
  { key: '/qc', icon: <BugOutlined />, label: '质控管理', perm: 'qc:manage' },
  { key: '/base-data', icon: <DatabaseOutlined />, label: '基础数据', perm: 'base_data:edit' },
  { key: '/users', icon: <TeamOutlined />, label: '员工管理', perm: 'user:manage' },
  { key: '/settings', icon: <SettingOutlined />, label: '系统设置', perm: 'base_data:edit' },
  { key: '/audit-logs', icon: <AuditOutlined />, label: '操作日志', perm: 'audit:view' },
];

interface Notification {
  id: number;
  type: 'critical' | 'warning';
  title: string;
  message: string;
  time: string;
  read: boolean;
}

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [notiOpen, setNotiOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, roleLabel, hasPermission, logout } = useAuth();

  // 从 API 获取真实危急值/异常通知
  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const res = await dashboardApi.notifications();
        setNotifications(res.data || []);
      } catch {
        setNotifications([]);
      }
    };
    fetchNotifications();
    // 每 60 秒刷新一次
    const timer = setInterval(fetchNotifications, 60000);
    return () => clearInterval(timer);
  }, []);

  const unreadCount = notifications.filter(n => !n.read).length;

  // 根据权限过滤菜单
  const menuItems = allMenuItems
    .filter(item => !item.perm || hasPermission(item.perm))
    .map(({ perm, ...rest }) => rest);

  const userMenu = {
    items: [
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: logout },
    ],
  };

  const roleColors: Record<string, string> = {
    ADMIN: 'red',
    DIRECTOR: 'purple',
    REVIEWER: 'green',
    TECHNICIAN: 'blue',
  };

  const markAsRead = (id: number) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const clearAll = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    message.success('已全部标记为已读');
  };

  // 通知弹出面板
  const notificationPanel = (
    <div style={{ width: 340, maxHeight: 400, overflow: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f0f0f0', marginBottom: 8 }}>
        <Typography.Text strong style={{ fontSize: 14 }}>通知提醒</Typography.Text>
        {unreadCount > 0 && (
          <Button type="link" size="small" onClick={clearAll}>全部已读</Button>
        )}
      </div>
      {notifications.length === 0 ? (
        <Empty description="暂无通知" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <List
          dataSource={notifications}
          renderItem={(item) => (
            <List.Item
              style={{
                padding: '10px 4px',
                background: item.read ? 'transparent' : '#fff7e6',
                borderRadius: 6,
                marginBottom: 4,
                cursor: 'pointer',
                borderLeft: item.type === 'critical' ? '3px solid #ff4d4f' : '3px solid #faad14',
              }}
              onClick={() => {
                markAsRead(item.id);
                if (item.type === 'critical') navigate('/results');
              }}
            >
              <List.Item.Meta
                avatar={
                  item.type === 'critical'
                    ? <CloseCircleOutlined style={{ fontSize: 20, color: '#ff4d4f' }} />
                    : <WarningOutlined style={{ fontSize: 20, color: '#faad14' }} />
                }
                title={
                  <span style={{ fontSize: 13 }}>
                    {!item.read && <Badge dot style={{ marginRight: 6 }} />}
                    {item.title}
                  </span>
                }
                description={
                  <div>
                    <div style={{ fontSize: 12, color: '#595959', lineHeight: 1.5 }}>{item.message}</div>
                    <div style={{ fontSize: 11, color: '#bfbfbf', marginTop: 4 }}>{item.time}</div>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      )}
    </div>
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        style={{ background: '#001529' }}
      >
        {/* Logo 区域 */}
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: collapsed ? 'column' : 'row',
          gap: collapsed ? 2 : 10,
          background: 'linear-gradient(135deg, #002140 0%, #001529 100%)',
          borderBottom: '1px solid #ffffff15',
          padding: '0 16px',
          transition: 'all 0.3s',
        }}>
          <div style={{
            width: collapsed ? 32 : 36,
            height: collapsed ? 32 : 36,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(24, 144, 255, 0.3)',
            flexShrink: 0,
          }}>
            <BugOutlined style={{ color: '#fff', fontSize: collapsed ? 16 : 18 }} />
          </div>
          {!collapsed && (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{
                color: '#fff',
                fontSize: 18,
                fontWeight: 700,
                letterSpacing: 2,
                lineHeight: 1.2,
              }}>
                LIS
              </span>
              <span style={{
                color: '#ffffff60',
                fontSize: 11,
                letterSpacing: 1,
              }}>
                检验信息系统
              </span>
            </div>
          )}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 1px 4px rgba(0,0,0,.08)',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: 16 }}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {/* 通知铃铛 */}
            <Popover
              content={notificationPanel}
              title={null}
              trigger="click"
              open={notiOpen}
              onOpenChange={setNotiOpen}
              placement="bottomRight"
              overlayStyle={{ padding: 0 }}
            >
              <Badge count={unreadCount} size="small" offset={[-2, 2]}>
                <Button
                  type="text"
                  icon={<BellOutlined style={{ fontSize: 18, color: unreadCount > 0 ? '#ff4d4f' : '#595959' }} />}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 36,
                    height: 36,
                    borderRadius: '50%',
                    background: unreadCount > 0 ? '#fff2f0' : 'transparent',
                  }}
                />
              </Badge>
            </Popover>

            <Tag color={roleColors[user?.role || ''] || 'default'}>{roleLabel}</Tag>
            <Dropdown menu={userMenu} placement="bottomRight">
              <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Avatar icon={<UserOutlined />} style={{ background: '#1890ff' }} />
                <Typography.Text>{user?.real_name || user?.username}</Typography.Text>
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#f5f5f5', borderRadius: 8, minHeight: 280 }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
