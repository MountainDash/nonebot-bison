import React, { ReactElement, useContext, useEffect, useState } from "react";
import { LoginContext, GlobalConfContext } from "../utils/context";
import { Layout, Menu, Empty, Collapse, Card, Tag, Row, Col, Form, Tooltip, Button, Modal, Select,
  Input, Popconfirm} from 'antd';
import { SubscribeConfig, SubscribeResp, PlatformConfig, CategoryConfig } from '../utils/type';
import { SettingOutlined, BugOutlined, DeleteOutlined, CopyOutlined } from '@ant-design/icons';
import { getSubscribe, getTargetName, addSubscribe, delSubscribe } from '../api/config';
import { InputTag } from '../component/inputTag';
import './admin.css';

export function Admin() {
  const { login } = useContext(LoginContext);
  const [ tab, changeTab ] = useState("manage");
  return (
  <Layout style={{ minHeight: '100vh' }}>
    <Layout.Sider className="layout-side">
      <div className="user">
      </div>
      <Menu mode="inline" theme="dark" defaultSelectedKeys={[tab]}
        onClick={({key}) => changeTab(key)}>
        <Menu.Item key="manage" icon={<SettingOutlined />}>订阅管理</Menu.Item>
        { login.type === 'admin' &&
        <Menu.Item key="log" icon={<BugOutlined />}>查看日志</Menu.Item>
        }
      </Menu>
    </Layout.Sider>
    <Layout.Content>
      <div style={{margin: '24px', background: '#fff', minHeight: '640px'}}>
      {
        tab === 'manage' ? 
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
  const [ currentAddingGroupNumber, setCurrentAddingGroupNumber ] = useState('');
  const globalConf = useContext(GlobalConfContext);
  const loadData = () => {
    getSubscribe()
      .then(res => {
          setConfigData(_ => res);
        });
  }
  useEffect(() => {
    loadData()
  }, [prop.tab]);
  const clickNew = (groupNumber: string) => (e: React.MouseEvent<HTMLButtonElement>) => {
    setShowModal(_ => true);
    setCurrentAddingGroupNumber(groupNumber);
    e.stopPropagation();
  }
  const handleDelete = (groupNumber: string, platformName: string, target: string) => () => {
    delSubscribe(groupNumber, platformName, target).then(() => {
      loadData() 
    })
  }
  const genCard = (groupNumber: string) => (config: SubscribeConfig) => {
    const platformConf = globalConf.platformConf[config.platformName] as PlatformConfig;
    return (
    <Col span={6} key={`${config.platformName}-${config.target}`}> 
      <Card title={`${platformConf.name} - ${config.targetName}`}
        actions={[
          <Popconfirm title={`确定要删除 ${platformConf.name} - ${config.targetName}`}
            onConfirm={handleDelete(groupNumber, config.platformName, config.target || 'default')}>
            <Tooltip title="删除" ><DeleteOutlined /></Tooltip>
          </Popconfirm>, 
          <Tooltip title="添加到其他群"><CopyOutlined /></Tooltip>
          ]}>
        <Form labelCol={{ span: 6 }}>
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
        <Collapse.Panel header={
          <span>{`${key} - ${value.name}`}<Button style={{float: "right"}} onClick={clickNew(key)}>添加</Button></span>
          } key={key}>
          <Row gutter={{ xs: 8, sm: 16, md: 24, lg: 32 }} align="middle">
            {value.subscribes.map(genCard(key))}
          </Row>
        </Collapse.Panel>
        )
    }
    return (
    <div>
      <Collapse>
        {groups}
      </Collapse>
      <AddModal groupNumber={currentAddingGroupNumber} showModal={showModal} 
        refresh={loadData} setShowModal={(s: boolean) => setShowModal(_ => s)} />
    </div>
    )
  }
}

interface InputTagCustomProp {
  value?: Array<string>,
  onChange?: (value: Array<string>) => void,
  disabled?: boolean
}
function InputTagCustom(prop: InputTagCustomProp) {
  const [value, setValue] = useState(prop.value || []);
  const handleSetValue = (newVal: Array<string>) => {
    setValue(() => newVal);
    if (prop.onChange) {
      prop.onChange(newVal);
    }
  }
  return (
    <>
      {
        prop.disabled ? <Tag color="red">不支持标签</Tag>: 
        <>
        {value.length === 0 &&
          <Tag color="green">全部标签</Tag>
        }
        <InputTag color="blue" addText="添加标签" value={value} onChange={handleSetValue} />
      </>
      } 
    </>
  )
}

interface AddModalProp {
  showModal: boolean,
  groupNumber: string,
  setShowModal: (s: boolean) => void,
  refresh: () => void
}
function AddModal(prop: AddModalProp) {
  const [ confirmLoading, setConfirmLoading ] = useState<boolean>(false);
  const { platformConf } = useContext(GlobalConfContext);
  const [ hasTarget, setHasTarget ] = useState(false);
  const [ categories, setCategories ] = useState({} as CategoryConfig);
  const [ enabledTag, setEnableTag ] = useState(false);
  const [ form ] = Form.useForm();
  const changePlatformSelect = (platform: string) => {
    setHasTarget(_ => platformConf[platform].hasTarget);
    setCategories(_ => platformConf[platform].categories);
    setEnableTag(platformConf[platform].enabledTag)
    if (! platformConf[platform].hasTarget) {
      getTargetName(platform, 'default')
        .then(res => {
          console.log(res)
          form.setFieldsValue({
            targetName: res.targetName,
            target: ''
          })
        })
    } else {
      form.setFieldsValue({
        targetName: '',
        target: ''
      })
    }
  }
  const handleSubmit = (value: any) => {
    let newVal = Object.assign({}, value)
    if (typeof newVal.tags != 'object') {
      newVal.tags = []
    }
    if (newVal.target === '') {
      newVal.target = 'default'
    }
    addSubscribe(prop.groupNumber, newVal)
    .then(() => {
      setConfirmLoading(false);
      prop.setShowModal(false);
      prop.refresh();
      });
  }
  const handleModleFinish = () => {
    form.submit();
    setConfirmLoading(() => true);
  }

  return <Modal title="添加订阅" visible={prop.showModal} 
    confirmLoading={confirmLoading} onCancel={() => prop.setShowModal(false)}
    onOk={handleModleFinish}>
    <Form form={form} labelCol={{ span: 6 }} name="b" onFinish={handleSubmit}
      initialValues={{tags: [], categories: []}}>
      <Form.Item label="平台" name="platformName" rules={[]}>
        <Select style={{ width: '80%' }} onChange={changePlatformSelect}>
          {Object.keys(platformConf).map(platformName => 
            <Select.Option key={platformName} value={platformName}>{platformConf[platformName].name}</Select.Option>
            )}
        </Select>
      </Form.Item>
      <Form.Item label="账号" name="target" rules={[
        {required: hasTarget, message: "请输入账号"},
        {validator: async (_, value) => {
          try {
            const res = await getTargetName(form.getFieldValue('platformName'), value);
            if (res.targetName) {
                form.setFieldsValue({
                  targetName: res.targetName
                })
                return Promise.resolve()
            } else {
                form.setFieldsValue({
                  targetName: ''
                })
              return Promise.reject("账号不正确，请重新检查账号")
            }
          } catch {
            return Promise.reject('服务器错误，请稍后再试')
          }
        }
        }
      ]}>
        <Input placeholder={hasTarget ? "获取方式见文档" : "此平台不需要账号"} 
          disabled={! hasTarget} style={{ width: "80%" }}/>
      </Form.Item>
      <Form.Item label="账号名称" name="targetName">
        <Input style={{ width: "80%" }} disabled />
      </Form.Item>
      <Form.Item label="订阅分类" name="categories">
        <Select style={{ width: '80%' }} mode="multiple" 
          disabled={Object.keys(categories).length === 0}
          placeholder={Object.keys(categories).length > 0 ?
            "请选择要订阅的分类" : "本平台不支持分类"}>
          {Object.keys(categories).length > 0 &&
            Object.keys(categories).map((indexStr) => 
              <Select.Option key={indexStr} value={parseInt(indexStr)}>
                {categories[parseInt(indexStr)]}
              </Select.Option>
            )
          }
        </Select>
      </Form.Item>
      <Form.Item label="订阅Tag" name="tags">
        <InputTagCustom disabled={!enabledTag}/>
      </Form.Item>
    </Form>
    </Modal>
}
