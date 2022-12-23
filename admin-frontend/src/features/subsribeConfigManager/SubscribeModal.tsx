import React, { useEffect, useState } from 'react';
import {
  Form, Input, InputTag, Modal, Select, Space, Tag,
} from '@arco-design/web-react';
import useForm from '@arco-design/web-react/es/Form/useForm';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import { selectPlatformConf } from '../globalConf/globalConfSlice';
import { CategoryConfig, SubscribeConfig } from '../../utils/type';
import getTargetName from '../targetName/targetNameReq';
import { useUpdateSubMutation, useNewSubMutation } from './subscribeConfigSlice';
import useWindowDimensions from '../../utils/hooks';

function SubscribeTag({
  value, onChange, disabled,
}: {
  value?: string[];
  onChange?: (arg0: string[]) => void;
  disabled?: boolean;
}) {
  const [valueState, setValueState] = useState(value || []);
  const handleSetValue = (newVal: string[]) => {
    setValueState(newVal);
    if (onChange) {
      onChange(newVal);
    }
  };
  useEffect(() => {
    if (value) {
      setValueState(value);
    }
  }, [value]);

  if (disabled) {
    return <Tag color="gray">不支持标签</Tag>;
  }
  return (
    <Space>
      { valueState.length === 0 && <Tag color="green">全部标签</Tag> }
      <InputTag
        allowClear
        placeholder="添加标签"
        value={value}
        onChange={handleSetValue}
      />
    </Space>
  );
}

SubscribeTag.defaultProps = {
  value: [],
  onChange: null,
  disabled: false,
};

interface SubscribeModalProp {
  visible: boolean;
  setVisible: (arg0: boolean) => void;
  groupNumber: string;
  initval?: SubscribeConfig | null;
}

function SubscribeModal({
  visible, setVisible, groupNumber, initval,
}: SubscribeModalProp) {
  const [form] = useForm();
  const [confirmLoading, setConfirmLoading] = useState(false);
  const platformConf = useAppSelector(selectPlatformConf);
  const [updateSub] = useUpdateSubMutation();
  const [newSub] = useNewSubMutation();
  const dispatch = useAppDispatch();
  const { width } = useWindowDimensions();

  const onSubmit = () => {
    form.validate().then((value: SubscribeConfig) => {
      const newVal = { ...value };
      if (typeof newVal.tags !== 'object') {
        newVal.tags = [];
      }
      if (typeof newVal.cats !== 'object') {
        newVal.cats = [];
      }
      if (newVal.target === '') {
        newVal.target = 'default';
      }
      let postPromise: ReturnType<typeof updateSub>;
      if (initval) {
        postPromise = updateSub({
          groupNumber: parseInt(groupNumber, 10),
          sub: newVal,
        });
      } else {
        postPromise = newSub({
          groupNumber: parseInt(groupNumber, 10),
          sub: newVal,
        });
      }
      setConfirmLoading(true);
      postPromise.then(() => {
        setConfirmLoading(false);
        setVisible(false);
      });
    });
  };

  const [hasTarget, setHasTarget] = useState(false);
  const [categories, setCategories] = useState({} as CategoryConfig);
  const [enableTags, setEnableTags] = useState(false);

  const setPlatformStates = (platform: string) => {
    setHasTarget(platformConf[platform].hasTarget);
    setCategories(platformConf[platform].categories);
    setEnableTags(platformConf[platform].enabledTag);
  };

  const handlePlatformSelected = (platform: string) => {
    setPlatformStates(platform);
    form.setFieldValue('cats', []);
    if (!platformConf[platform].hasTarget) {
      dispatch(getTargetName(platform, 'default')).then((res) => {
        form.setFieldsValue({
          targetName: res,
          target: '',
        });
      });
    } else {
      form.setFieldsValue({
        targetName: '',
        target: '',
      });
    }
  };

  useEffect(() => {
    if (initval) {
      const { platformName } = initval;
      setPlatformStates(platformName);
      form.setFieldsValue(initval);
    } else {
      form.clearFields();
    }
  }, [initval, form, platformConf]);

  return (
    <Modal
      title="编辑订阅"
      visible={visible}
      onCancel={() => setVisible(false)}
      confirmLoading={confirmLoading}
      onOk={onSubmit}
      style={{ maxWidth: '90vw' }}
    >
      <Form
        form={form}
        layout={width > 520 ? 'horizontal' : 'vertical'}
      >
        <Form.Item label="平台" field="platformName">
          <Select placeholder="平台" onChange={handlePlatformSelected}>
            { Object.keys(platformConf).map(
              (platformName: string) => (
                <Select.Option value={platformName} key={platformName}>
                  {platformConf[platformName].name}
                </Select.Option>
              ),
            ) }
          </Select>
        </Form.Item>
        <Form.Item
          label="帐号"
          field="target"
          rules={[
            { required: hasTarget, message: '请输入账号' },
            {
              validator: (value, callback) => new Promise<void>((resolve) => {
                dispatch(getTargetName(form.getFieldValue('platformName'), value))
                  .then((res) => {
                    if (res) {
                      form.setFieldsValue({
                        targetName: res,
                      });
                      resolve();
                    } else {
                      form.setFieldsValue({
                        targetName: '',
                      });
                      callback('账号不正确，请重新检查账号');
                      resolve();
                    }
                  })
                  .catch(() => {
                    callback('服务器错误，请稍后再试');
                    resolve();
                  });
              }),
            },
          ]}
        >
          <Input
            disabled={!hasTarget || !!initval}
            suffix={<IconInfoCircle />}
            placeholder={hasTarget ? '获取方式见文档' : '此平台不需要账号'}
          />
        </Form.Item>
        <Form.Item label="帐号名称" field="targetName">
          <Input disabled />
        </Form.Item>
        <Form.Item
          label="订阅分类"
          field="cats"
          rules={[
            {
              required: Object.keys(categories).length > 0,
              message: '请至少选择一个分类进行订阅',
            },
          ]}
        >
          <Select
            mode="multiple"
            disabled={Object.keys(categories).length === 0}
            placeholder={
              Object.keys(categories).length > 0
                ? '请选择要订阅的分类'
                : '本平台不支持分类'
            }
          >
            { Object.keys(categories).length > 0
              && Object.keys(categories).map((indexStr) => (
                <Select.Option key={indexStr} value={parseInt(indexStr, 10)}>
                  { categories[parseInt(indexStr, 10)] }
                </Select.Option>
              ))}
          </Select>

        </Form.Item>
        <Form.Item label="标签" field="tags">
          <SubscribeTag disabled={!enableTags} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
SubscribeModal.defaultProps = {
  initval: null,
};
export default SubscribeModal;
