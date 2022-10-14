import React, { ReactNode, useEffect, useState } from 'react';
import { Breadcrumb, Layout, Menu } from '@arco-design/web-react';
import { IconRobot, IconDashboard } from '@arco-design/web-react/icon';
import './Home.css';
// import SubscribeManager from '../features/subsribeConfigManager/SubscribeManager';
import {
  Link, Navigate, Outlet, useLocation, useNavigate,
} from 'react-router-dom';
import { useAppSelector } from '../app/hooks';
import { selectIsLogin } from '../features/auth/authSlice';

export default function Home() {
  const location = useLocation();
  const navigate = useNavigate();
  const isLogin = useAppSelector(selectIsLogin);

  const path = location.pathname;
  useEffect(() => {
    if (path === '/home') {
      navigate('/home/groups');
    }

    if (path !== '/home/groups' && !path.startsWith('/home/groups/') && path !== '/home/weight') {
      navigate('/home/groups');
    }
  }, [path]);

  let currentKey = '';
  if (path === '/home/groups') {
    currentKey = 'groups';
  } else if (path.startsWith('/home/groups/')) {
    currentKey = 'subs';
  }

  const [selectedTab, changeSelectTab] = useState(currentKey);

  const handleTabSelect = (tab: string) => {
    changeSelectTab(tab);
    if (tab === 'groups') {
      navigate('/home/groups');
    } else if (tab === 'weight') {
      navigate('/home/weight');
    }
  };

  if (!isLogin) {
    return <Navigate to="/unauthed" />;
  }

  let breadcrumbContent: ReactNode;
  if (path === '/home/groups') {
    breadcrumbContent = (
      <Breadcrumb style={{ margin: '16px 0' }}>
        <Breadcrumb.Item>
          <IconRobot />
          订阅管理
        </Breadcrumb.Item>
      </Breadcrumb>
    );
  } else if (path.startsWith('/home/groups/')) {
    breadcrumbContent = (
      <Breadcrumb style={{ margin: '16px 0' }}>
        <Breadcrumb.Item>
          <Link to="/home/groups">
            <IconRobot />
            订阅管理
          </Link>
        </Breadcrumb.Item>
        <Breadcrumb.Item>
          群管理
        </Breadcrumb.Item>
      </Breadcrumb>
    );
  } else if (path === '/home/weight') {
    breadcrumbContent = (
      <Breadcrumb style={{ margin: '16px 0' }}>
        <Breadcrumb.Item>
          <IconDashboard />
          调度权重
        </Breadcrumb.Item>
      </Breadcrumb>
    );
  }
  return (
    <Layout className="layout-collapse-demo">
      <Layout.Header>
        <span>
          Nonebot Bison
        </span>
      </Layout.Header>
      <Layout className="layout-collapse-demo">
        <Layout.Sider
          collapsible
          breakpoint="lg"
        >
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
        <Layout.Content style={{ padding: '0 1em' }}>
          <Layout style={{ height: '100%' }}>
            { breadcrumbContent }
            <Layout.Content style={{ margin: '0.5em', padding: '2em' }}>
              <Outlet />
            </Layout.Content>
          </Layout>
        </Layout.Content>
      </Layout>
    </Layout>
  );
}
