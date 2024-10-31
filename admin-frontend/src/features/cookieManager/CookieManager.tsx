import React from 'react';
import {
  Button,
  Table, TableColumnProps, Typography, Space, Popconfirm,
} from '@arco-design/web-react';
import { useParams } from 'react-router-dom';
import { useGetCookiesQuery, useDeleteCookieMutation } from './cookieConfigSlice';
import './CookieManager.css';
import { Cookie } from '../../utils/type';
import CookieAddModal from './CookieAddModal';
import CookieEditModal from './CookieEditModal';

export default function CookieManager() {
  const { siteName } = useParams();
  const { data: cookieDict } = useGetCookiesQuery();
  const cookiesList = cookieDict ? Object.values(cookieDict) : [];

  // 添加cookie
  const [showAddModal, setShowAddModal] = React.useState(false);
  const handleAddCookie = () => () => {
    setShowAddModal(true);
  };

  // 删除cookie
  const [deleteCookie] = useDeleteCookieMutation();
  const handleDelCookie = (cookieId: string) => () => {
    deleteCookie({
      cookieId,
    });
  };

  // 编辑cookie
  const [showEditModal, setShowEditModal] = React.useState(false);
  const [editCookie, setEditCookie] = React.useState<Cookie | null>(null);
  const handleEditCookie = (cookie: Cookie) => () => {
    setEditCookie(cookie);
    setShowEditModal(true);
  };

  let data = [];
  if (siteName) {
    data = cookiesList.filter((tSite) => tSite.site_name === siteName);
  }

  const columns: TableColumnProps[] = [
    {
      title: 'ID',
      dataIndex: 'id',
    },
    {
      title: 'Cookie 名称',
      dataIndex: 'cookie_name',
    },
    {
      title: '所属站点',
      dataIndex: 'site_name',
    },
    {
      title: '最后使用时间',
      dataIndex: 'last_usage',
    },
    {
      title: '状态',
      dataIndex: 'status',
    },
    {
      title: 'CD',
      dataIndex: 'cd_milliseconds',
    }, {
      title: '操作',
      dataIndex: 'op',
      render: (_: null, record: Cookie) => (
        <Space size="small">
          <Popconfirm
            title={`确定删除 Cookie ${record.cookie_name} ？`}
            onOk={handleDelCookie(record.id.toString())}
          >
            <span className="list-actions-icon">
              {/* <IconDelete /> */}
              <Button type="text" status="danger">删除</Button>
            </span>
          </Popconfirm>
          <Button type="text" onClick={handleEditCookie(record)}>编辑</Button>
        </Space>
      ),

    },

  ];

  return (
    <>
      <div>

        <Typography.Title heading={4} style={{ margin: '15px' }}>Cookie 管理</Typography.Title>

        <Button
          style={{ width: '90px', margin: '20px 10px' }}
          type="primary"
          onClick={handleAddCookie()}
        >
          添加
        </Button>
      </div>

      <Table columns={columns} data={data} />
      <CookieAddModal visible={showAddModal} setVisible={setShowAddModal} siteName={siteName || ''} />
      <CookieEditModal visible={showEditModal} setVisible={setShowEditModal} cookie={editCookie} />
    </>
  );
}
