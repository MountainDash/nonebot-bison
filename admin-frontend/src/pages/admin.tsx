import React, { FC, useContext, useState } from "react";
import { LoginContext, GlobalConfContext } from "../utils/context";
import { Layout, Menu } from 'antd';
import { SubscribeConfig } from '../utils/type';
import { SettingOutlined, BugOutlined } from '@ant-design/icons';
import './admin.css';

export function Admin() {
  const { login } = useContext(LoginContext);
  const [ tab, changeTab ] = useState("manage");
  const globalConfContext = useContext(GlobalConfContext);
  return (
  <Layout style={{ minHeight: '100vh' }}>
    <Layout.Sider className="layout-side">
      <div className="user">
      </div>
      <Menu mode="inline" theme="dark" defaultSelectedKeys={[tab]}
        onClick={({key}) => changeTab(key)}>
        <Menu.Item key="manage" icon={<SettingOutlined />}>订阅管理</Menu.Item>
        { login.type == 'admin' &&
        <Menu.Item key="log" icon={<BugOutlined />}>查看日志</Menu.Item>
        }
      </Menu>
    </Layout.Sider>
    <Layout.Content>
      <div style={{margin: '24px', background: '#fff', minHeight: '640px'}}>
      {
        tab == 'manage' ? 
        <div>123</div>
        : null
      }
      </div>
    </Layout.Content>
  </Layout>
  )
}

function ConfigPage() {
  const [ configData, setConfigData ] = useState<Array<SubscribeConfig>>([
    {
      platform: 'weibo',
      target: '123333',
      catetories: [1, 2],
      tags: []
    }
  ]);
}
