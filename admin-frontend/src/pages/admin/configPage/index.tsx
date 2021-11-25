import {CopyOutlined, DeleteOutlined} from '@ant-design/icons';
import {Button, Card, Col, Collapse, Empty, Form, Input, message, Modal, Popconfirm, Row, Select, Tag, Tooltip} from 'antd';
import React, {ReactElement, ReactNode, useContext, useEffect, useState} from "react";
import {addSubscribe, delSubscribe, getSubscribe, getTargetName} from 'src/api/config';
import {InputTag} from 'src/component/inputTag';
import {GlobalConfContext} from "src/utils/context";
import {CategoryConfig, PlatformConfig, SubscribeConfig, SubscribeResp} from 'src/utils/type';

interface ConfigPageProp {
  tab: string
}
export function ConfigPage(prop: ConfigPageProp) {
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
