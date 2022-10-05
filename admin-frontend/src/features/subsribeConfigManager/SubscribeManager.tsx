import React from 'react';
import {
  Button, Empty, Space, Table, Tag,
} from '@arco-design/web-react';
import { useParams } from 'react-router-dom';
import { useGetSubsQuery } from './subscribeConfigSlice';
import { useAppSelector } from '../../app/hooks';
import { selectPlatformConf } from '../globalConf/globalConfSlice';
import { SubscribeConfig } from '../../utils/type';

export default function SubscribeManager() {
  const { data: subs } = useGetSubsQuery();
  const { groupNumber } = useParams();
  const platformConf = useAppSelector(selectPlatformConf);

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
          <Button type="text">编辑</Button>
          <Button type="text" status="success">复制</Button>
          <Button type="text" status="danger" onClick={() => { console.log(record); }}>删除</Button>
        </Space>
      ),
    },
  ];

  if (subs && groupNumber) {
    return (
      <>
        <span>
          {subs[groupNumber].name}
          {groupNumber}
        </span>
        <Button style={{ width: '90px', margin: '20px' }} type="primary">添加</Button>
        <Table
          columns={columns}
          data={subs[groupNumber].subscribes}
          rowKey={(record: SubscribeConfig) => `${record.platformName}-${record.target}`}
        />
      </>
    );
  }
  return <Empty />;
}
