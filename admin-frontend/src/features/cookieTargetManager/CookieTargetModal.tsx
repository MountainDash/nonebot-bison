import React
  from 'react';
import { Modal, Select } from '@arco-design/web-react';
import { SubscribeConfig, SubscribeGroupDetail } from '../../utils/type';
import { useNewCookieTargetMutation } from '../cookieManager/cookieConfigSlice';
import { useGetSubsQuery } from '../subsribeConfigManager/subscribeConfigSlice';

interface SubscribeModalProp {
  cookieId: number;
  visible: boolean;
  setVisible: (arg0: boolean) => void;
}

export default function CookieTargetModal({ cookieId, visible, setVisible }: SubscribeModalProp) {
  const [newCookieTarget] = useNewCookieTargetMutation();

  const { data: subs } = useGetSubsQuery();
  const pureSubs:SubscribeConfig[] = subs ? Object.values(subs)
    .reduce((
      pv:Array<SubscribeConfig>,
      cv:SubscribeGroupDetail,
    ) => pv.concat(cv.subscribes), []) : [];
  const [index, setIndex] = React.useState(-1);
  const handleSubmit = (idx:number) => {
    const postPromise: ReturnType<typeof newCookieTarget> = newCookieTarget({
      cookieId,
      platformName: pureSubs[idx].platformName,
      target: pureSubs[idx].target,
    });
    postPromise.then(() => {
      setVisible(false);
    });
  };
  const { Option } = Select;
  return (
    <Modal
      title="关联 Cookie"
      visible={visible}
      onCancel={() => setVisible(false)}
      onOk={() => handleSubmit(index)}
    >
      <Select
        placeholder="选择要关联的 target"
        style={{ width: '100%' }}
        onChange={setIndex}
      >
        {pureSubs.length
          && pureSubs.map((sub, idx) => (
            <Option
              key={JSON.stringify(sub)}
              value={idx}
            >
              {JSON.stringify(sub)}
            </Option>
          ))}
      </Select>

    </Modal>
  );
}
