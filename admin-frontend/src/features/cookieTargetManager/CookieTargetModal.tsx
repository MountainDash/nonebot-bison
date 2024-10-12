import React
  from 'react';
import {
  Empty, Form, Modal, Select,
} from '@arco-design/web-react';
import { Cookie, SubscribeConfig, SubscribeGroupDetail } from '../../utils/type';
import { useNewCookieTargetMutation } from '../cookieManager/cookieConfigSlice';
import { useGetSubsQuery } from '../subsribeConfigManager/subscribeConfigSlice';
import { useAppSelector } from '../../app/hooks';
import { selectPlatformConf } from '../globalConf/globalConfSlice';

interface SubscribeModalProp {
  cookie:Cookie| null
  visible: boolean;
  setVisible: (arg0: boolean) => void;
}

export default function CookieTargetModal({
  cookie, visible, setVisible,
}: SubscribeModalProp) {
  if (!cookie) {
    return <Empty />;
  }
  const [newCookieTarget] = useNewCookieTargetMutation();
  const FormItem = Form.Item;

  // 筛选出当前Cookie支持的平台
  const platformConf = useAppSelector(selectPlatformConf);
  const platformThatSiteSupport = Object.values(platformConf).reduce((p, c) => {
    if (c.siteName in p) {
      p[c.siteName].push(c.platformName);
    } else {
      p[c.siteName] = [c.platformName];
    }
    return p;
  }, {} as Record<string, string[]>);
  const supportedPlatform = platformThatSiteSupport[cookie.site_name];

  const { data: subs } = useGetSubsQuery();
  const pureSubs:SubscribeConfig[] = subs ? Object.values(subs)
    .reduce((
      pv:Array<SubscribeConfig>,
      cv:SubscribeGroupDetail,
    ) => pv.concat(cv.subscribes), []) : [];
  const filteredSubs = pureSubs.filter((sub) => supportedPlatform.includes(sub.platformName));
  const [index, setIndex] = React.useState(-1);

  const handleSubmit = (idx:number) => {
    const postPromise: ReturnType<typeof newCookieTarget> = newCookieTarget({
      cookieId: cookie.id,
      platformName: filteredSubs[idx].platformName,
      target: filteredSubs[idx].target,
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

      <Form>
        <FormItem label="平台">

          <Select
            placeholder="选择要关联的平台"
            style={{ width: '100%' }}
            onChange={setIndex}
          >
            {supportedPlatform.length
          && supportedPlatform.map((sub, idx) => (
            <Option
              key={JSON.stringify(sub)}
              value={idx}
            >
              {sub}
            </Option>
          ))}
          </Select>

        </FormItem>
        <FormItem label="订阅目标" required>
          <Select
            placeholder="选择要关联的订阅目标"
            style={{ width: '100%' }}
            onChange={setIndex}
          >
            {filteredSubs.length
          && filteredSubs.map((sub, idx) => (
            <Option
              key={JSON.stringify(sub)}
              value={idx}
            >
              {sub.targetName}
            </Option>
          ))}
          </Select>
        </FormItem>

      </Form>
    </Modal>
  );
}
