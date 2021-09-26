import React, { ReactElement, useContext, useEffect, useState } from "react";
import { LoginContext, GlobalConfContext } from "../utils/context";
import { Layout, Menu, Empty, Collapse, Card, Tag, Row, Col, Form, Tooltip, Button, Modal, Select,
  Input} from 'antd';
import { SubscribeConfig, SubscribeResp, PlatformConfig } from '../utils/type';
import { SettingOutlined, BugOutlined, DeleteOutlined, CopyOutlined, PlusOutlined } from '@ant-design/icons';
import { getSubscribe, getTargetName } from '../api/config';
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
        <ConfigPage tab={tab}/>
        : null
      }
      </div>
    </Layout.Content>
  </Layout>
  )
}

interface ConfigPageProp {
  tab: string
}
function ConfigPage(prop: ConfigPageProp) {
  const [ configData, setConfigData ] = useState<SubscribeResp>({});
  const [ showModal, setShowModal ] = useState<boolean>(false);
  const globalConf = useContext(GlobalConfContext);
  useEffect(() => {
    getSubscribe()
      .then(res => {
          setConfigData(_ => res);
        });
  }, [prop.tab]);
  const clickNew = (e: React.MouseEvent<HTMLButtonElement>) => {
    setShowModal(_ => true);
    e.stopPropagation();
  }
  const genCard = (config: SubscribeConfig) => {
    const platformConf = globalConf.platformConf[config.targetType] as PlatformConfig;
    return (
    <Col span={6} key={`${config.targetType}-${config.target}`}> 
      <Card title={`${platformConf.name} - ${config.targetName}`}
        actions={[
          <Tooltip title="删除"><DeleteOutlined /></Tooltip>,
          <Tooltip title="添加到其他群"><CopyOutlined /></Tooltip>
          ]}>
        <Form labelCol={{ span: 4 }}>
        <Form.Item label="订阅类型">
          {Object.keys(platformConf.categories).length > 0 ? 
          config.cats.map((catKey: number) => (<Tag color="green" key={catKey}>{platformConf.categories[catKey]}</Tag>)) :
          <Tag color="red">不支持类型</Tag>}
        </Form.Item>
        <Form.Item label="订阅Tag">
          {platformConf.enabledTag ? config.tags.length > 0 ? config.tags.map(tag => (<Tag color="green" key={tag}>{tag}</Tag>)) : (<Tag color="blue">全部标签</Tag>) :
          <Tag color="red">不支持Tag</Tag>}
        </Form.Item>
        </Form>
      </Card>
    </Col>
    )
  }
  if (Object.keys(configData).length === 0) {
    return <Empty />
  } else {
    let groups: Array<ReactElement> = [];
    for (let key of Object.keys(configData)) {
      let value = configData[key];
      groups.push(
        <Collapse.Panel header={<span>{`${key} - ${value.name}`}<Button style={{float: "right"}} onClick={clickNew}>添加</Button></span>} key={key}>
          <Row gutter={{ xs: 8, sm: 16, md: 24, lg: 32 }} align="middle">
            {value.subscribes.map(genCard)}
          </Row>
        </Collapse.Panel>
        )
    }
    return (
    <div>
      <Collapse>
        {groups}
      </Collapse>
      <AddModal showModal={showModal} setShowModal={(s: boolean) => setShowModal(_ => s)} />
    </div>
    )
  }
}

interface AddModalProp {
  showModal: boolean,
  setShowModal: (s: boolean) => void
}
function AddModal(prop: AddModalProp) {
  const [ confirmLoading, setConfirmLoading ] = useState<boolean>(false);
  const { platformConf } = useContext(GlobalConfContext);
  const [ hasTarget, setHasTarget ] = useState(false);
  const [ form ] = Form.useForm();
  const changePlatformSelect = (platform: string) => {
    setHasTarget(_ => platformConf[platform].hasTarget);
    if (! platformConf[platform].hasTarget) {
      getTargetName(platform, 'default')
        .then(res => {
          console.log(res)
          form.setFieldsValue(() => { return {
            targetName: res.targetName
          }})
          })
    }
  }
  const handleSubmit = (value: any) => {
    console.log(value);
  }

  return <Modal title="添加订阅" visible={prop.showModal} 
    confirmLoading={confirmLoading} onCancel={() => prop.setShowModal(false)}>
    <Form form={form} labelCol={{ span: 6 }} name="b">
      <Form.Item label="平台" name="platformType" rules={[]}>
        <Select style={{ width: '80%' }} onChange={changePlatformSelect}>
          {Object.keys(platformConf).map(platformName => 
            <Select.Option key={platformName} value={platformName}>{platformConf[platformName].name}</Select.Option>
            )}
        </Select>
      </Form.Item>
      <Form.Item label="账号" name="target" rules={[]}>
        <Input placeholder={hasTarget ? "获取方式见文档" : "此平台不需要账号"} disabled={! hasTarget} style={{ width: "80%" }} />
      </Form.Item>
      <Form.Item label="账号名称" name="targetName">
        <Input style={{ width: "80%" }} />
      </Form.Item>
    </Form>
    </Modal>
}
