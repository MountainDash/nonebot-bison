import {CopyOutlined, DeleteOutlined, EditOutlined} from '@ant-design/icons';
import {Card, Col, Form, message, Popconfirm, Select, Tag, Tooltip} from 'antd';
import Modal from 'antd/lib/modal/Modal';
import React, {useContext, useState} from "react";
import {addSubscribe, delSubscribe} from 'src/api/config';
import {GlobalConfContext} from "src/utils/context";
import {PlatformConfig, SubscribeConfig, SubscribeResp} from 'src/utils/type';
import {AddModal} from './addSubsModal';

interface CopyModalProp {
  setShowModal: (modalShow: boolean) => void
  showModal: boolean
  config: SubscribeConfig,
  groups: SubscribeResp
  currentGroupNumber: string
  reload: () => void
}
function CopyModal({setShowModal,config,
    currentGroupNumber,groups,showModal,reload}: CopyModalProp) {
  const [confirmLoading, setConfirmLoading] = useState(false)
  const [ selectedGroups, setSelectGroups ] = useState<Array<string>>([]);
  const postReqs = async (selectedGroups: Array<string>, config: SubscribeConfig) => {
    for(let selectedGroup of selectedGroups) {
      await addSubscribe(selectedGroup, config);
    }
  }
  const handleOk = () => {
    if (selectedGroups.length === 0) {
      message.error("请至少选择一个目标群");
    } else{
      setConfirmLoading(true)
      postReqs(selectedGroups, config).then(() => {
        setConfirmLoading(false)
        setShowModal(false)
        return reload() 
      })
    }
  }
  return <Modal title="复制订阅" visible={showModal} confirmLoading={confirmLoading}
    onCancel={() => setShowModal(false)} onOk={handleOk}>
        <Select mode="multiple" onChange={(value: Array<string>) => setSelectGroups(value)} 
          style={{width: '80%'}}>
          {
            Object.keys(groups).filter(groupNumber => groupNumber !== currentGroupNumber)
              .map((groupNumber) =>
              <Select.Option value={groupNumber} key={groupNumber}>
                {`${groupNumber} - ${groups[groupNumber].name}`}
              </Select.Option>)
            }
        </Select>
    </Modal>
}
interface SubscribeCardProp {
  groupNumber: string
  config: SubscribeConfig
  groupSubscribes: SubscribeResp
  reload: () => void
}
export function SubscribeCard({groupNumber, config, reload, groupSubscribes}: SubscribeCardProp) {
  const globalConf = useContext(GlobalConfContext);
  const [showModal, setShowModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const platformConf = globalConf.platformConf[config.platformName] as PlatformConfig;
  const handleDelete = (groupNumber: string, platformName: string, target: string) => () => {
    delSubscribe(groupNumber, platformName, target).then(() => {
      reload() 
    })
  }
  return (
  <Col span={6} key={`${config.platformName}-${config.target}`}> 
    <Card title={`${platformConf.name} - ${config.targetName}`}
      actions={[
        <Tooltip title="编辑">
          <EditOutlined onClick={()=>{setShowEditModal(state => !state)}}/>
        </Tooltip>,
        <Tooltip title="添加到其他群">
          <CopyOutlined onClick={()=>{setShowModal(state => !state)}}/>
        </Tooltip>,
        <Popconfirm title={`确定要删除 ${platformConf.name} - ${config.targetName}`}
          onConfirm={handleDelete(groupNumber, config.platformName, config.target || 'default')}>
          <Tooltip title="删除" ><DeleteOutlined /></Tooltip>
        </Popconfirm>, 
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
    <CopyModal setShowModal={setShowModal} reload={reload} currentGroupNumber={groupNumber}
      showModal={showModal} config={config} groups={groupSubscribes}/>
    <AddModal showModal={showEditModal} setShowModal={setShowEditModal} 
      groupNumber={groupNumber} refresh={reload} initVal={config}/>
  </Col>
  )
}
