import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Button, Empty, Table, Typography,
} from '@arco-design/web-react';
import { useGetCookieTargetsQuery } from '../cookieManager/cookieConfigSlice';
import { SubscribeConfig } from '../../utils/type';
import { useDeleteSubMutation } from '../subsribeConfigManager/subscribeConfigSlice';
import CookieTargetModal from './CookieTargetModal';

export default function () {
  const { cookieId } = useParams();
  const { data: cookieTargets } = useGetCookieTargetsQuery(cookieId);

  console.log(cookieTargets);
  const [{ isLoading: deleteIsLoading }] = useDeleteSubMutation();
  const isLoading = deleteIsLoading;
  const [showModal, setShowModal] = useState(false);
  const handleAdd = () => {
    setShowModal(true);
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
          rowKey={(record: SubscribeConfig) => `${record.platformName}-${record.target}`}
          loading={isLoading}
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
