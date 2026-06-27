import { useEffect, useState } from 'react';
import { Tabs, Table, Button, Space, Modal, Form, Input, Select, Tag, message, Popconfirm, InputNumber, Transfer } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import { baseDataApi, instrumentApi } from '../services/api';

export default function BaseDataPage() {
  // ========== 科室 ==========
  const [departments, setDepartments] = useState<any[]>([]);
  const [deptVisible, setDeptVisible] = useState(false);
  const [deptForm] = Form.useForm();

  // ========== 检验项目 ==========
  const [testItems, setTestItems] = useState<any[]>([]);
  const [instruments, setInstruments] = useState<any[]>([]);
  const [itemVisible, setItemVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<any>(null);
  const [itemForm] = Form.useForm();

  // ========== 组合项目 ==========
  const [combos, setCombos] = useState<any[]>([]);
  const [comboVisible, setComboVisible] = useState(false);
  const [editingCombo, setEditingCombo] = useState<any>(null);
  const [comboForm] = Form.useForm();
  const [comboItemKeys, setComboItemKeys] = useState<string[]>([]);

  useEffect(() => {
    loadDepartments();
    loadTestItems();
    loadInstruments();
    loadCombos();
  }, []);

  const loadDepartments = async () => {
    const res = await baseDataApi.departments();
    setDepartments(res.data);
  };
  const loadTestItems = async () => {
    const res = await baseDataApi.testItems();
    setTestItems(res.data);
  };
  const loadInstruments = async () => {
    const res = await instrumentApi.list();
    setInstruments(res.data);
  };
  const loadCombos = async () => {
    const res = await baseDataApi.getCombos();
    setCombos(res.data);
  };

  // ---- 科室 ----
  const handleCreateDept = async (values: any) => {
    await baseDataApi.createDepartment(values);
    message.success('科室添加成功');
    setDeptVisible(false);
    deptForm.resetFields();
    loadDepartments();
  };

  // ---- 项目 ----
  const openCreateItem = () => {
    setEditingItem(null);
    itemForm.resetFields();
    setItemVisible(true);
  };

  const openEditItem = (item: any) => {
    setEditingItem(item);
    itemForm.setFieldsValue({
      code: item.code, name: item.name, category: item.category,
      sample_type: item.sample_type, unit: item.unit,
      ref_range_low: item.ref_range_low, ref_range_high: item.ref_range_high,
      critical_low: item.critical_low, critical_high: item.critical_high,
      decimal_places: item.decimal_places, instrument_id: item.instrument_id,
      sort_order: item.sort_order,
    });
    setItemVisible(true);
  };

  const handleSaveItem = async (values: any) => {
    try {
      if (editingItem) {
        await baseDataApi.updateTestItem(editingItem.id, values);
        message.success('修改成功');
      } else {
        await baseDataApi.createTestItem(values);
        message.success('添加成功');
      }
      setItemVisible(false);
      itemForm.resetFields();
      setEditingItem(null);
      loadTestItems();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '操作失败');
    }
  };

  const handleDeleteItem = async (id: number) => {
    try {
      await baseDataApi.deleteTestItem(id);
      message.success('已删除');
      loadTestItems();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '删除失败');
    }
  };

  // ---- 组合项目 ----
  const openCreateCombo = () => {
    setEditingCombo(null);
    comboForm.resetFields();
    setComboItemKeys([]);
    setComboVisible(true);
  };

  const openEditCombo = (combo: any) => {
    setEditingCombo(combo);
    comboForm.setFieldsValue({
      code: combo.code, name: combo.name, category: combo.category,
      sample_type: combo.sample_type, remark: combo.remark,
    });
    setComboItemKeys(combo.items?.map((i: any) => String(i.test_item_id)) || []);
    setComboVisible(true);
  };

  const handleSaveCombo = async (values: any) => {
    if (comboItemKeys.length === 0) {
      message.warning('请选择包含的项目');
      return;
    }
    const data = { ...values, test_item_ids: comboItemKeys.map(Number) };
    try {
      if (editingCombo) {
        await baseDataApi.updateCombo(editingCombo.id, data);
        message.success('修改成功');
      } else {
        await baseDataApi.createCombo(data);
        message.success('创建成功');
      }
      setComboVisible(false);
      comboForm.resetFields();
      setComboItemKeys([]);
      setEditingCombo(null);
      loadCombos();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '操作失败');
    }
  };

  const handleDeleteCombo = async (id: number) => {
    await baseDataApi.deleteCombo(id);
    message.success('已删除');
    loadCombos();
  };

  // Transfer 数据源
  const transferDataSource = testItems.map(item => ({
    key: String(item.id),
    title: `${item.code} - ${item.name}`,
    description: `${item.unit || ''} [${item.instrument_name || '未绑定'}]`,
  }));

  const deptColumns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '编码', dataIndex: 'code', width: 100 },
    { title: '名称', dataIndex: 'name' },
    { title: '状态', dataIndex: 'is_active', width: 80, render: (v: boolean) => v ? <Tag color="green">启用</Tag> : <Tag>禁用</Tag> },
  ];

  const itemColumns = [
    { title: '编码', dataIndex: 'code', width: 80 },
    { title: '名称', dataIndex: 'name', width: 120 },
    { title: '分类', dataIndex: 'category', width: 80 },
    { title: '单位', dataIndex: 'unit', width: 80 },
    { title: '参考范围', key: 'ref', width: 140,
      render: (_: any, r: any) => r.ref_range_low != null && r.ref_range_high != null
        ? `${r.ref_range_low} - ${r.ref_range_high}` : '-'
    },
    { title: '危急值', key: 'critical', width: 130,
      render: (_: any, r: any) => (r.critical_low != null || r.critical_high != null)
        ? `${r.critical_low ?? '-'} ~ ${r.critical_high ?? '-'}` : '-'
    },
    { title: '绑定仪器', dataIndex: 'instrument_name', width: 120,
      render: (v: string) => v || <Tag>未绑定</Tag>
    },
    { title: '操作', key: 'action', width: 140,
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEditItem(record)}>编辑</Button>
          <Popconfirm title="确认删除该项目？" onConfirm={() => handleDeleteItem(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const comboColumns = [
    { title: '编码', dataIndex: 'code', width: 80 },
    { title: '名称', dataIndex: 'name', width: 120 },
    { title: '分类', dataIndex: 'category', width: 80 },
    { title: '包含项目', dataIndex: 'items', width: 300,
      render: (items: any[]) => items?.map((i: any) => <Tag key={i.code} color="blue">{i.code}</Tag>)
    },
    { title: '操作', key: 'action', width: 140,
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEditCombo(record)}>编辑</Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDeleteCombo(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Tabs items={[
      {
        key: 'items', label: '检验项目',
        children: (
          <>
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 13, color: '#999' }}>
                在「仪器管理」页面添加仪器后，这里可以给每个项目绑定仪器。
              </span>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreateItem}>添加项目</Button>
            </div>
            <Table columns={itemColumns} dataSource={testItems} rowKey="id" size="small" pagination={false} />

            <Modal title={editingItem ? '编辑检验项目' : '添加检验项目'} open={itemVisible}
              onCancel={() => { setItemVisible(false); itemForm.resetFields(); setEditingItem(null); }}
              onOk={async () => { try { const v = await itemForm.validateFields(); await handleSaveItem(v); } catch(e){} }}
              okText={editingItem ? '保存' : '添加'} destroyOnClose>
              <Form form={itemForm} layout="vertical">
                <Form.Item name="code" label="项目编码" rules={[{required:true}]}><Input placeholder="如 WBC、GLU" /></Form.Item>
                <Form.Item name="name" label="项目名称" rules={[{required:true}]}><Input placeholder="如 白细胞计数" /></Form.Item>
                <Form.Item name="category" label="分类"><Select placeholder="选择分类" options={[{value:'血常规',label:'血常规'},{value:'生化',label:'生化'},{value:'免疫',label:'免疫'},{value:'尿液',label:'尿液'}]} /></Form.Item>
                <Form.Item name="sample_type" label="标本类型"><Select placeholder="选择标本" options={[{value:'全血',label:'全血'},{value:'血清',label:'血清'},{value:'血浆',label:'血浆'},{value:'尿液',label:'尿液'}]} /></Form.Item>
                <Form.Item name="unit" label="单位"><Input placeholder="如 mmol/L" /></Form.Item>
                <Space>
                  <Form.Item name="ref_range_low" label="参考下限"><InputNumber style={{width:120}} /></Form.Item>
                  <Form.Item name="ref_range_high" label="参考上限"><InputNumber style={{width:120}} /></Form.Item>
                </Space>
                <Space>
                  <Form.Item name="critical_low" label="危急下限"><InputNumber style={{width:120}} /></Form.Item>
                  <Form.Item name="critical_high" label="危急上限"><InputNumber style={{width:120}} /></Form.Item>
                </Space>
                <Form.Item name="instrument_id" label="绑定仪器">
                  <Select placeholder="选择仪器（可不选）" allowClear
                    options={instruments.map(i => ({value: i.id, label: `${i.name} (${i.code})`}))} />
                </Form.Item>
              </Form>
            </Modal>
          </>
        ),
      },
      {
        key: 'combos', label: '组合项目',
        children: (
          <>
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 13, color: '#999' }}>
                创建组合项目后，新建标本时可以直接选择套餐，自动包含所有子项目。
              </span>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreateCombo}>添加组合项目</Button>
            </div>
            <Table columns={comboColumns} dataSource={combos} rowKey="id" size="small" pagination={false} />

            <Modal title={editingCombo ? '编辑组合项目' : '添加组合项目'} open={comboVisible} width={700}
              onCancel={() => { setComboVisible(false); comboForm.resetFields(); setComboItemKeys([]); setEditingCombo(null); }}
              onOk={async () => {
                try {
                  const v = await comboForm.validateFields();
                  await handleSaveCombo(v);
                } catch(e){}
              }}
              okText={editingCombo ? '保存' : '创建'} destroyOnClose>
              <Form form={comboForm} layout="vertical">
                <Form.Item name="code" label="编码" rules={[{required:true}]}><Input placeholder="如 CBC、LFT" /></Form.Item>
                <Form.Item name="name" label="名称" rules={[{required:true}]}><Input placeholder="如 血常规、肝功能" /></Form.Item>
                <Space>
                  <Form.Item name="category" label="分类"><Select style={{width:160}} placeholder="选择分类" options={[{value:'血常规',label:'血常规'},{value:'生化',label:'生化'},{value:'免疫',label:'免疫'}]} /></Form.Item>
                  <Form.Item name="sample_type" label="标本类型"><Select style={{width:160}} placeholder="选择标本" options={[{value:'全血',label:'全血'},{value:'血清',label:'血清'},{value:'尿液',label:'尿液'}]} /></Form.Item>
                </Space>
                <Form.Item name="remark" label="备注"><Input /></Form.Item>
                <Form.Item label="包含的检验项目（从左侧选到右侧）" required>
                  <Transfer
                    dataSource={transferDataSource}
                    targetKeys={comboItemKeys}
                    onChange={(keys) => setComboItemKeys(keys as string[])}
                    render={(item) => item.title}
                    listStyle={{ width: 280, height: 300 }}
                    showSearch
                    filterOption={(input, option) => (option?.title as string).toLowerCase().includes(input.toLowerCase())}
                  />
                </Form.Item>
              </Form>
            </Modal>
          </>
        ),
      },
      {
        key: 'depts', label: '科室管理',
        children: (
          <>
            <div style={{ marginBottom: 16, textAlign: 'right' }}>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setDeptVisible(true)}>添加科室</Button>
            </div>
            <Table columns={deptColumns} dataSource={departments} rowKey="id" size="small" pagination={false} />

            <Modal title="添加科室" open={deptVisible}
              onCancel={() => { setDeptVisible(false); deptForm.resetFields(); }}
              onOk={async () => { try { const v = await deptForm.validateFields(); await handleCreateDept(v); } catch(e){} }}
              okText="添加" destroyOnClose>
              <Form form={deptForm} layout="vertical">
                <Form.Item name="code" label="科室编码" rules={[{required:true}]}><Input /></Form.Item>
                <Form.Item name="name" label="科室名称" rules={[{required:true}]}><Input /></Form.Item>
              </Form>
            </Modal>
          </>
        ),
      },
    ]} />
  );
}
