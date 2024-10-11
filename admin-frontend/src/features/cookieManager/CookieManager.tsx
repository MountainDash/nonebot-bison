import React from 'react';
import {
  Table, TableColumnProps, Typography,
} from '@arco-design/web-react';
import { useParams } from 'react-router-dom';

import './CookieManager.css';

export default function CookieManager() {
  const { siteName } = useParams();

  let data = [
    {
      id: 3,
      site_name: 'rss',
      friendly_name: 'rss [{"ewqe":"e]',
      last_usage: '1970-01-01T00:00:00',
      status: '',
      cd_milliseconds: 10000,
      is_universal: false,
      is_anonymous: false,
      tags: {},
    },
  ];
  if (siteName) {
    data = data.filter((tSite) => tSite.site_name === siteName);
  }

  const columns: TableColumnProps[] = [
    {
      title: 'ID',
      dataIndex: 'id',
    },
    {
      title: 'Cookie 名称',
      dataIndex: 'friendly_name',
    },
    {
      title: '所属站点',
      dataIndex: 'site_name',
    },

  ];
  console.log(data);

  return (
    <>
      <Typography.Title heading={4} style={{ margin: '15px' }}>Cookie 管理</Typography.Title>

      <Table columns={columns} data={data} />
    </>
  );
}
