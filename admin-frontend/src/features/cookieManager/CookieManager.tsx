import React from 'react';
import {
  Button,
  Table, TableColumnProps, Typography, Space, Popconfirm,
} from '@arco-design/web-react';
import { useParams } from 'react-router-dom';
import { IconDelete, IconEdit } from '@arco-design/web-react/icon';
import { useAppSelector } from '../../app/hooks';
import { useGetCookiesQuery, useDeleteCookieMutation } from './cookieConfigSlice';
import './CookieManager.css';
import { selectPlatformConf, selectSiteConf } from '../globalConf/globalConfSlice';
import { Cookie, PlatformConfig } from '../../utils/type';
import CookieTargetModal from '../cookieTargetManager/CookieTargetModal';
import CookieAddModal from './CookieAddModal';
import CookieEditModal from './CookieEditModal';

export default function CookieManager() {
  const { siteName } = useParams();
  const siteConf = useAppSelector(selectSiteConf);
  const platformConf = useAppSelector(selectPlatformConf);
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
    data = cookiesList.filter((tSite) => tSite.site_name === siteName);
  }
  const platformThatSiteSupport: Record<string, string> = Object.values(platformConf).reduce((p, c) => {
    p[c.siteName] = c.platformName;
    return p;
  }, {} as Record<string, string>);
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
            title={`确定删除 Cookie ${record.friendly_name} ？`}
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
