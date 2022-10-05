import React, { ReactNode, useEffect, useState } from 'react';
import { Breadcrumb, Layout, Menu } from '@arco-design/web-react';
import { IconRobot, IconDashboard } from '@arco-design/web-react/icon';
import './Home.css';
// import SubscribeManager from '../features/subsribeConfigManager/SubscribeManager';
import {
  Link, Outlet, useLocation, useNavigate,
} from 'react-router-dom';

export function homeLoader() {
}

export default function Home() {
  const location = useLocation();
  const navigate = useNavigate();

  const path = location.pathname;
  useEffect(() => {
    if (path === '/home') {
      navigate('/home/groups');
    }

    if (path !== '/home/groups' && !path.startsWith('/home/groups/')) {
      console.log(path);
      navigate('/home/groups');
    }
  }, [path]);

  let currentKey: string = '';
  if (path === '/home/groups') {
    currentKey = 'groups';
  } else if (path.startsWith('/home/groups/')) {
    currentKey = 'subs';
  }

  const [selectedTab, changeSelectTab] = useState(currentKey);

  const handleTabSelect = (tab: string) => {
    changeSelectTab(tab);
    if (tab === 'groups') {
      navigate('/home/navigate');
    } else if (tab === 'weight') {
      navigate('/home/weight');
    }
  };

  let breadcrumbContent: ReactNode;
  if (selectedTab === 'groups') {
    breadcrumbContent = (
      <Breadcrumb style={{ margin: '16px 0' }}>
        <Breadcrumb.Item>
          <IconRobot />
          订阅管理
        </Breadcrumb.Item>
      </Breadcrumb>
    );
  } else if (selectedTab === 'subs') {
    breadcrumbContent = (
      <Breadcrumb style={{ margin: '16px 0' }}>
        <Breadcrumb.Item>
          <Link to="/home/groups">
            <IconRobot />
            订阅管理
          </Link>
        </Breadcrumb.Item>
        <Breadcrumb.Item>
          groupman
        </Breadcrumb.Item>
      </Breadcrumb>
    );
  }
  return (
    <Layout className="layout-collapse-demo">
      <Layout.Header>
        <div className="logo" />
      </Layout.Header>
      <Layout className="layout-collapse-demo">
        <Layout.Sider>
          <Menu
            defaultSelectedKeys={[selectedTab]}
            onClickMenuItem={(key) => { handleTabSelect(key); }}
          >
            <Menu.Item key="groups">
              <IconRobot />
              订阅管理
            </Menu.Item>
            <Menu.Item key="weight">
              <IconDashboard />
              调度权重
            </Menu.Item>
          </Menu>
        </Layout.Sider>
        <Layout.Content style={{ padding: '0 24px' }}>
          <Layout style={{ height: '100%' }}>
            { breadcrumbContent }
            <Layout.Content style={{ margin: '10px', padding: '40px' }}>
              <Outlet />
            </Layout.Content>
          </Layout>
        </Layout.Content>
      </Layout>
    </Layout>
  );
}
