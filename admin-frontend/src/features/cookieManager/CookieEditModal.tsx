import React, { useState } from 'react';
import {
  Button, Empty, Form, Input, Modal, Space, Table,
} from '@arco-design/web-react';
import { useDeleteCookieTargetMutation, useGetCookieTargetsQuery } from './cookieConfigSlice';
import { Cookie, CookieTarget } from '../../utils/type';
import CookieTargetModal from '../cookieTargetManager/CookieTargetModal';

interface CookieEditModalProps {
  visible: boolean;
  setVisible: (arg0: boolean) => void;
  cookie: Cookie | null
}

function CookieEditModal({ visible, setVisible, cookie }: CookieEditModalProps) {
  if (!cookie) {
    return <Empty />;
  }
  const FormItem = Form.Item;
  // const [confirmLoading, setConfirmLoading] = useState(false);
  const [deleteCookieTarget] = useDeleteCookieTargetMutation();
  // 获取 Cookie Target
  const { data: cookieTargets } = useGetCookieTargetsQuery({ cookieId: cookie.id });

  // 添加 Cookie Target
  const [showAddCookieTargetModal, setShowAddCookieTargetModal] = useState(false);
  const handleAddCookieTarget = () => () => {
    setShowAddCookieTargetModal(true);
  };

  // 删除 Cookie Target
  const handleDelete = (record: CookieTarget) => () => {
    deleteCookieTarget({
      cookieId: record.cookie_id,
      target: record.target.target,
      platformName: record.target.platform_name,
    });
  };
  const columns = [
    {
      title: '平台名称',
      dataIndex: 'target.platform_name',
    },
    {
      title: '订阅名称',
      dataIndex: 'target.target_name',

    },
    {
      title: 'Cookie ID',
      dataIndex: 'cookie_id',
    },
    {
      title: '操作',
      dataIndex: 'op',
      render: (_: null, record: CookieTarget) => (
        <Space size="small">
          <Button type="text" status="danger" onClick={handleDelete(record)}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Modal
        title="编辑 Cookie"
        visible={visible}
        onCancel={() => setVisible(false)}
        // confirmLoading={confirmLoading}
        onOk={() => setVisible(false)}
        style={{ maxWidth: '90vw', minWidth: '50vw' }}
      >
        <Form autoComplete="off">
          <FormItem label="Cookie ID">
            <Input disabled value={cookie.id.toString()} />
          </FormItem>
          <FormItem label="Cookie 名称">
            <Input value={cookie.cookie_name} disabled />
          </FormItem>
          <FormItem label="所属站点">
            <Input value={cookie.site_name} disabled />
          </FormItem>
          <FormItem label="内容">
            <Input.TextArea
              value={cookie.content}
              disabled
            />
          </FormItem>

          <FormItem label="标签">
            <Input.TextArea
              value={JSON.stringify(cookie.tags)}
              disabled
            />
          </FormItem>

          <FormItem label="最后使用时间">
            <Input value={cookie.last_usage.toString()} disabled />
          </FormItem>
          <FormItem label="状态">
            <Input value={cookie.status} disabled />
          </FormItem>
          <FormItem label="冷却时间（毫秒）">
            <Input value={cookie.cd_milliseconds.toString()} disabled />
          </FormItem>

        </Form>

        <Button type="primary" onClick={handleAddCookieTarget()}>关联 Cookie</Button>
        <Table
          columns={columns}
          data={cookieTargets}
          rowKey={(record: CookieTarget) => `${record.target.platform_name}-${record.target.target}`}
          scroll={{ x: true }}
        />
      </Modal>

      <CookieTargetModal
        cookie={cookie}
        visible={showAddCookieTargetModal}
        setVisible={setShowAddCookieTargetModal}
      />
    </>
  );
}

export default CookieEditModal;
