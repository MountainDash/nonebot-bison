import React, { useState } from 'react';
import {
  Button, Empty, Message, Popconfirm, Space, Table, Tag, Typography,
} from '@arco-design/web-react';
import { useParams } from 'react-router-dom';
import { useDeleteSubMutation, useGetSubsQuery } from './subscribeConfigSlice';
import { useAppSelector } from '../../app/hooks';
import { selectPlatformConf } from '../globalConf/globalConfSlice';
import { SubscribeConfig } from '../../utils/type';
import SubscribeModal from './SubscribeModal';

export default function SubscribeManager() {
  const { data: subs } = useGetSubsQuery();
  const [deleteSub, { isLoading: deleteIsLoading }] = useDeleteSubMutation();
  const { groupNumber } = useParams();
  const platformConf = useAppSelector(selectPlatformConf);

  const isLoading = deleteIsLoading;
  const [showModal, setShowModal] = useState(false);
  const [formInitVal, setFormInitVal] = useState(null as SubscribeConfig | null);

  const handleNewSub = () => {
    setFormInitVal(null);
    setShowModal(true);
  };

  const handleEdit = (sub: SubscribeConfig) => () => {
    setFormInitVal(sub);
    setShowModal(true);
  };

  const columns = [
    {
      title: '平台名称',
      dataIndex: 'platformName',
      render: (col: any, record: SubscribeConfig) => (
        <span>{platformConf[record.platformName].name}</span>
      ),
    },
    { title: '帐号名称', dataIndex: 'targetName' },
    { title: '订阅帐号', dataIndex: 'target' },
    {
      title: '订阅分类',
      dataIndex: 'cats',
      render: (col: any, record: SubscribeConfig) => (
        <span>
          <Space>
            {
            record.cats.map((catNumber: number) => (
              <Tag>{platformConf[record.platformName].categories[catNumber]}</Tag>
            ))
            }
          </Space>
        </span>
      ),
    },
    {
      title: '订阅标签',
      dataIndex: 'tags',
      render: (col: any, record: SubscribeConfig) => (
        <span>
          <Space>
            {
              record.tags.length === 0 ? <Tag color="green">全部标签</Tag>
                : record.tags.map((tag: string) => (
                  <Tag color="blue">{tag}</Tag>
                ))
            }
          </Space>
        </span>
      ),
    },
    {
      title: '操作',
      dataIndex: 'op',
      render: (_: any, record: SubscribeConfig) => (
        <Space>
          <Button type="text" onClick={handleEdit(record)}>编辑</Button>
          <Button type="text" status="success" onClick={() => Message.error('懒得写了')}>复制</Button>
          <Popconfirm
            title={`确认删除订阅 ${record.targetName} ?`}
            onOk={() => {
              deleteSub({
                groupNumber: parseInt(groupNumber!, 10),
                target: record.target,
                platformName: record.platformName,
              });
            }}
          >
            <Button type="text" status="danger">删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (subs && groupNumber) {
    return (
      <>
        <span>
          <Typography.Title heading={3}>{subs[groupNumber].name}</Typography.Title>
          <Typography.Text type="secondary">{groupNumber}</Typography.Text>
        </span>
        <Button style={{ width: '90px', margin: '20px 10px' }} type="primary" onClick={handleNewSub}>添加</Button>
        <Table
          columns={columns}
          data={subs[groupNumber].subscribes}
          rowKey={(record: SubscribeConfig) => `${record.platformName}-${record.target}`}
          loading={isLoading}
        />
        <SubscribeModal
          visible={showModal}
          setVisible={setShowModal}
          groupNumber={groupNumber}
          initval={formInitVal}
        />
      </>
    );
  }
  return <Empty />;
}
