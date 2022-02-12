import { BugOutlined, SettingOutlined } from "@ant-design/icons";
import { Layout, Menu } from "antd";
import React, { useState } from "react";
import { useSelector } from "react-redux";
import { loginSelector } from "src/store/loginSlice";
import "./admin.css";
import { ConfigPage } from "./configPage";

export function Admin() {
  const login = useSelector(loginSelector);
  const [tab, changeTab] = useState("manage");
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Sider className="layout-side">
        <div className="user"></div>
        <Menu
          mode="inline"
          theme="dark"
          defaultSelectedKeys={[tab]}
          onClick={({ key }) => changeTab(key)}
        >
          <Menu.Item key="manage" icon={<SettingOutlined />}>
            订阅管理
          </Menu.Item>
          {login.type === "admin" && (
            <Menu.Item key="log" icon={<BugOutlined />}>
              查看日志
            </Menu.Item>
          )}
        </Menu>
      </Layout.Sider>
      <Layout.Content>
        <div style={{ margin: "24px", background: "#fff", minHeight: "640px" }}>
          {tab === "manage" ? <ConfigPage tab={tab} /> : null}
        </div>
      </Layout.Content>
    </Layout>
  );
}
