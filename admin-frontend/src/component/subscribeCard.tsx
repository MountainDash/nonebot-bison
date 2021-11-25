import {CopyOutlined, DeleteOutlined} from '@ant-design/icons';
import {Card, Col, Form, message, Popconfirm, Select, Tag, Tooltip} from 'antd';
import React, {ReactNode, useContext, useState} from "react";
import {addSubscribe, delSubscribe} from 'src/api/config';
import {GlobalConfContext} from "src/utils/context";
import {PlatformConfig, SubscribeConfig, SubscribeResp} from 'src/utils/type';

interface TargetGroupSelectionProp {
  config: SubscribeConfig,
  groups: SubscribeResp
  children: ReactNode
}

function TargetGroupSelection({ config, groups, children }: TargetGroupSelectionProp) {
  let [ selectedGroups, setSelectGroups ] = useState<Array<string>>([]);
  const submitCopy = () => {
    let promise = null
    for (let selectGroup of selectedGroups) {
      if (! promise) {
        promise = addSubscribe(selectGroup, config)
      } else {
        promise = promise.then(() => addSubscribe(selectGroup, config))
      }
    }
    if (promise) {
      promise.then(() => message.success("复制订阅成功"))
    }
    return promise;
  }
  return <>
    <Popconfirm title={
        <Select mode="multiple" onChange={(value: Array<string>) => setSelectGroups(value)}>
          {
            Object.keys(groups).map((groupNumber) => 
              <Select.Option value={groupNumber} key={groupNumber}>
                {`${groupNumber} - ${groups[groupNumber].name}`}
              </Select.Option>)
            }
        </Select>
      } onConfirm={submitCopy} >
      { children }
    </Popconfirm>
  </>
}
interface SubscribeCardProp {
  groupNumber: string
  config: SubscribeConfig
  groupSubscribes: SubscribeResp
  reload: () => null
}
export function SubscribeCard({groupNumber, config, reload, groupSubscribes}: SubscribeCardProp) {
  const globalConf = useContext(GlobalConfContext);
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
        <Popconfirm title={`确定要删除 ${platformConf.name} - ${config.targetName}`}
          onConfirm={handleDelete(groupNumber, config.platformName, config.target || 'default')}>
          <Tooltip title="删除" ><DeleteOutlined /></Tooltip>
        </Popconfirm>, 
        <TargetGroupSelection config={config} groups={groupSubscribes}>
          <Tooltip title="添加到其他群"><CopyOutlined /></Tooltip>
        </TargetGroupSelection>
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
