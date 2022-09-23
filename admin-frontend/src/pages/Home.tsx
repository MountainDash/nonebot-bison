import React, { ReactNode, useState } from 'react';
import { Breadcrumb, Layout, Menu } from '@arco-design/web-react';
import { IconRobot, IconDashboard } from '@arco-design/web-react/icon';

export default function Home() {
  const [selectedTab, changeSelectTab] = useState('1');
  let breadcrumbContent: ReactNode;
  if (selectedTab === '1') {
    breadcrumbContent = (
      <Breadcrumb.Item>
        <IconRobot />
        订阅管理
      </Breadcrumb.Item>
    );
  }
  // let content: ReactNode;
  return (
    <Layout style={{ height: '100vh' }}>
      <Layout.Header>
        heade
      </Layout.Header>
      <Layout>
        <Layout.Sider>
          <Menu defaultSelectedKeys={['1']} onClickMenuItem={(key) => { changeSelectTab(key); }}>
            <Menu.Item key="1">
              <IconRobot />
              订阅管理
            </Menu.Item>
            <Menu.Item key="2">
              <IconDashboard />
              调度权重
            </Menu.Item>
          </Menu>
        </Layout.Sider>
        <Layout.Content style={{ padding: '0 24px' }}>
          <Breadcrumb style={{ margin: '16px 0' }}>
            { breadcrumbContent }
          </Breadcrumb>
          <div>123</div>
        </Layout.Content>
      </Layout>
    </Layout>
  );
}
