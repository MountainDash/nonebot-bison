import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Button, Empty, Space, Table, Typography,
} from '@arco-design/web-react';
import { useDeleteCookieTargetMutation, useGetCookieTargetsQuery } from '../cookieManager/cookieConfigSlice';
import { CookieTarget } from '../../utils/type';
import CookieTargetModal from './CookieTargetModal';

export default function () {
  const { cookieId } = useParams();
  const { data: cookieTargets } = useGetCookieTargetsQuery(cookieId);

  console.log(cookieTargets);
  const [showModal, setShowModal] = useState(false);
  const [deleteCookieTarget] = useDeleteCookieTargetMutation();
  const handleAdd = () => {
    setShowModal(true);
  };
  const handleDelete = (record: CookieTarget) => () => {
    deleteCookieTarget({
      cookieId: record.cookieId,
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
  if (cookieId) {
    return (
      <>
        <span>
          <Typography.Title heading={3}>{`Cookie ${cookieId}`}</Typography.Title>
        </span>
        <Button style={{ width: '90px', margin: '20px 10px' }} type="primary" onClick={handleAdd}>添加</Button>
        <Table
          columns={columns}
          data={cookieTargets}
          rowKey={(record: CookieTarget) => `${record.target.platform_name}-${record.target.target}`}
          scroll={{ x: true }}
        />
        {
          cookieTargets && cookieTargets.length > 0
        && (
        <CookieTargetModal
          visible={showModal}
          setVisible={setShowModal}
          cookieId={cookieId}
        />
        )
        }
      </>
    );
  }
  return <Empty />;
}
