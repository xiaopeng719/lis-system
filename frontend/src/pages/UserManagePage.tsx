import { useEffect, useState } from 'react';
import { Table, Button, Tag, Space, Modal, Form, Input, Select, message, Typography, Card, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, UserOutlined } from '@ant-design/icons';
import { authApi } from '../services/api';

export default function UserManagePage() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [createVisible, setCreateVisible] = useState(false);
  const [editVisible, setEditVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<any>(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await authApi.listUsers();
      setUsers(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleCreate = async (values: any) => {
    try {
      await authApi.createUser(values);
      message.success('员工创建成功');
      setCreateVisible(false);
      createForm.resetFields();
      fetchUsers();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '创建失败');
    }
  };

  const handleEdit = (user: any) => {
    setEditingUser(user);
    editForm.setFieldsValue({
      real_name: user.real_name,
      role: user.role,
      department: user.department,
    });
    setEditVisible(true);
  };

  const handleUpdate = async (values: any) => {
    try {
      await authApi.updateUser(editingUser.id, values);
      message.success('修改成功');
      setEditVisible(false);
      editForm.resetFields();
      fetchUsers();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '修改失败');
    }
  };

  const roleLabels: Record<string, string> = {
    ADMIN: '管理员',
    TECHNICIAN: '检验师',
    REVIEWER: '审核员',
    DIRECTOR: '科室主任',
  };
  const roleColors: Record<string, string> = {
    ADMIN: 'red',
    TECHNICIAN: 'blue',
    REVIEWER: 'green',
    DIRECTOR: 'purple',
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '用户名', dataIndex: 'username', width: 120 },
    { title: '姓名', dataIndex: 'real_name', width: 100 },
    {
      title: '角色', dataIndex: 'role', width: 100,
      render: (v: string) => <Tag color={roleColors[v]}>{roleLabels[v] || v}</Tag>,
    },
    { title: '科室', dataIndex: 'department', width: 120 },
    {
      title: '状态', dataIndex: 'is_active', width: 80,
      render: (v: boolean) => v ? <Tag color="green">启用</Tag> : <Tag color="red">禁用</Tag>,
    },
    {
      title: '创建时间', dataIndex: 'created_at', width: 170,
      render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作', key: 'action', width: 100,
      render: (_: any, record: any) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
          编辑
        </Button>
      ),
    },
  ];

  const roleOptions = [
    { value: 'ADMIN', label: '管理员' },
    { value: 'TECHNICIAN', label: '检验师' },
    { value: 'REVIEWER', label: '审核员' },
    { value: 'DIRECTOR', label: '科室主任' },
  ];

  const deptOptions = [
    { value: '检验科', label: '检验科' },
    { value: 'ICU', label: 'ICU' },
    { value: '急诊科', label: '急诊科' },
    { value: '内科', label: '内科' },
    { value: '外科', label: '外科' },
  ];

  return (
    <div>
      <Typography.Title level={4}>👥 员工管理</Typography.Title>
      <Card>
        <div style={{ marginBottom: 16, textAlign: 'right' }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)}>
            添加员工
          </Button>
        </div>
        <Table columns={columns} dataSource={users} rowKey="id" size="small" loading={loading}
          pagination={false} />
      </Card>

      {/* 创建员工 */}
      <Modal title="添加员工" open={createVisible}
        onCancel={() => { setCreateVisible(false); createForm.resetFields(); }}
        onOk={async () => { try { const v = await createForm.validateFields(); await handleCreate(v); } catch(e){} }}
        okText="创建" destroyOnClose>
        <Form form={createForm} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{required:true}]}>
            <Input placeholder="登录用户名" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{required:true},{min:6,message:'至少6位'}]}>
            <Input.Password placeholder="登录密码" />
          </Form.Item>
          <Form.Item name="real_name" label="姓名">
            <Input placeholder="真实姓名" />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{required:true}]}>
            <Select options={roleOptions} />
          </Form.Item>
          <Form.Item name="department" label="科室">
            <Select options={deptOptions} allowClear placeholder="选择科室" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑员工 */}
      <Modal title={`编辑员工: ${editingUser?.username}`} open={editVisible}
        onCancel={() => { setEditVisible(false); editForm.resetFields(); }}
        onOk={async () => { try { const v = await editForm.validateFields(); await handleUpdate(v); } catch(e){} }}
        okText="保存" destroyOnClose>
        <Form form={editForm} layout="vertical">
          <Form.Item name="real_name" label="姓名"><Input /></Form.Item>
          <Form.Item name="role" label="角色"><Select options={roleOptions} /></Form.Item>
          <Form.Item name="department" label="科室"><Select options={deptOptions} allowClear /></Form.Item>
          <Form.Item name="password" label="重置密码（留空不修改）"><Input.Password placeholder="留空则不修改" /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
