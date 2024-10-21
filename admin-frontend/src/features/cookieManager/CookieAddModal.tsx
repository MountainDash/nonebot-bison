import React, { useState } from 'react';
import { Form, Input, Modal } from '@arco-design/web-react';
import { useNewCookieMutation } from './cookieConfigSlice';
import { useAppDispatch } from '../../app/hooks';
import validateCookie from './cookieValidateReq';

interface CookieAddModalProps {
  visible: boolean;
  setVisible: (arg0: boolean) => void;
  siteName: string;
}

function CookieAddModal({ visible, setVisible, siteName }: CookieAddModalProps) {
  const FormItem = Form.Item;
  const [content, setContent] = useState<string>('');
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [newCookie] = useNewCookieMutation();
  const dispatch = useAppDispatch();

  const onSubmit = () => {
    const postPromise: ReturnType<typeof newCookie> = newCookie({ siteName, content });
    setConfirmLoading(true);
    postPromise.then(() => {
      setConfirmLoading(false);
      setVisible(false);
      setContent('');
    });
  };

  return (
    <Modal
      title="添加 Cookie"
      visible={visible}
      onCancel={() => setVisible(false)}
      confirmLoading={confirmLoading}
      onOk={onSubmit}
      style={{ maxWidth: '90vw' }}
    >

      <Form autoComplete="off">
        <FormItem label="站点" required>
          <Input placeholder="Please enter site name" value={siteName} disabled />
        </FormItem>
        <FormItem
          label="Cookie"
          required
          field="content"
          hasFeedback
          rules={[
            {
              validator: (value, callback) => new Promise<void>((resolve) => {
                dispatch(validateCookie(siteName, value))
                  .then((res) => {
                    if (res) {
                      callback();
                    } else {
                      callback('Cookie 格式错误');
                    }
                    resolve();
                  });
              }),
            },
          ]}

        >
          <Input.TextArea
            placeholder="请输入 Cookie"
            value={content}
            onChange={setContent}
          />
        </FormItem>

      </Form>
    </Modal>
  );
}

export default CookieAddModal;
