import {Form, Input, Modal, Select, Tag} from 'antd';
import React, {useEffect, useState} from "react";
import {useSelector} from 'react-redux';
import {addSubscribe, getTargetName, updateSubscribe} from 'src/api/config';
import {InputTag} from 'src/component/inputTag';
import {platformConfSelector} from 'src/store/globalConfSlice';
import {CategoryConfig, SubscribeConfig} from 'src/utils/type';

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
  useEffect(() => {
    if (prop.value) {
      setValue(prop.value);
    }
  }, [prop.value])
  return (
    <>
      {
        prop.disabled ? <Tag color="default">不支持标签</Tag>: 
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
  initVal?: SubscribeConfig
}
export function AddModal({
  showModal, groupNumber, setShowModal, refresh, initVal
}: AddModalProp) {
  const [ confirmLoading, setConfirmLoading ] = useState<boolean>(false);
  const platformConf = useSelector(platformConfSelector)
  const [ hasTarget, setHasTarget ] = useState(false);
  const [ categories, setCategories ] = useState({} as CategoryConfig);
  const [ enabledTag, setEnableTag ] = useState(false);
  const [ form ] = Form.useForm();
  const [ inited, setInited ] = useState(false);
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
    if (typeof newVal.tags !== 'object') {
      newVal.tags = []
    }
    if (typeof newVal.cats !== 'object') {
      newVal.cats = []
    }
    if (newVal.target === '') {
      newVal.target = 'default'
    }
    if (initVal) { // patch
      updateSubscribe(groupNumber, newVal)
        .then(() => {
          setConfirmLoading(false);
          setShowModal(false);
          form.resetFields();
          refresh();
        });
    } else {
      addSubscribe(groupNumber, newVal)
      .then(() => {
        setConfirmLoading(false);
        setShowModal(false);
        form.resetFields();
        refresh();
        });
    }
  }
  const handleModleFinish = () => {
    form.submit();
    setConfirmLoading(() => true);
  }
  useEffect(() => {
    if (initVal && !inited) {
      const platformName = initVal.platformName;
      setHasTarget(platformConf[platformName].hasTarget);
      setCategories(platformConf[platformName].categories);
      setEnableTag(platformConf[platformName].enabledTag);
      setInited(true)
      form.setFieldsValue(initVal)
    }
  }, [initVal, form, platformConf, inited])
  return <Modal title="添加订阅" visible={showModal} 
    confirmLoading={confirmLoading} onCancel={() => setShowModal(false)}
    onOk={handleModleFinish}>
    <Form form={form} labelCol={{ span: 6 }} name="b" onFinish={handleSubmit} >
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
      <Form.Item label="订阅分类" name="cats" rules={[
        {required: Object.keys(categories).length > 0, message: "请至少选择一个分类进行订阅"}
      ]}>
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
