import React, { useState } from 'react';
import { Form, Input, Modal } from '@arco-design/web-react';
import { useNewCookieMutation } from './cookieConfigSlice';
import { Cookie } from '../../utils/type';

interface CookieEditModalProps {
  visible: boolean;
  setVisible: (arg0: boolean) => void;
  cookie: Cookie | null
}

function CookieEditModal({ visible, setVisible, cookie }: CookieEditModalProps) {
  const FormItem = Form.Item;
  const [confirmLoading, setConfirmLoading] = useState(false);

  return (
    <Modal
      title="编辑 Cookie"
      visible={visible}
      onCancel={() => setVisible(false)}
      confirmLoading={confirmLoading}
      // onOk={onSubmit}
      style={{ maxWidth: '90vw', minWidth: '50vw' }}
    >
      {cookie
      && (
      <Form autoComplete="off">
        <FormItem label="Cookie ID">
          <Input disabled value={cookie.id.toString()} />
        </FormItem>
        <FormItem label="Cookie 名称">
          <Input value={cookie.friendly_name} disabled />
        </FormItem>
        <FormItem label="所属站点">
          <Input value={cookie.site_name} disabled />
        </FormItem>

        <FormItem label="标签">
          <Input.TextArea
            value={JSON.stringify(cookie.tags)}
            disabled
          />
        </FormItem>

        <FormItem label="最后使用时间">
          <Input value={cookie.last_usage.toString()} disabled />
        </FormItem>
        <FormItem label="状态">
          <Input value={cookie.status} disabled />
        </FormItem>
        <FormItem label="冷却时间（毫秒）">
          <Input value={cookie.cd_milliseconds.toString()} disabled />
        </FormItem>

      </Form>
      )}
    </Modal>
  );
}

export default CookieEditModal;
