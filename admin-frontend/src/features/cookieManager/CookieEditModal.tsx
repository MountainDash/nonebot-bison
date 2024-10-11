import React, { useState } from 'react';
import { Form, Input, Modal } from '@arco-design/web-react';
import { useNewCookieMutation } from './cookieConfigSlice';

interface CookieModalProps {
  visible: boolean;
  setVisible: (arg0: boolean) => void;
  siteName: string;
}

function CookieEditModal({ visible, setVisible, siteName }: CookieModalProps) {
  const FormItem = Form.Item;
  const [content, setContent] = useState<string>('');
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [newCoookie] = useNewCookieMutation();

  const onSubmit = () => {
    const postPromise: ReturnType<typeof newCoookie> = newCoookie({ siteName, content });
    setConfirmLoading(true);
    postPromise.then(() => {
      setConfirmLoading(false);
      setVisible(false);
      setContent('');
    });
  };

  return (
    <Modal
      title="编辑 Cookie"
      visible={visible}
      onCancel={() => setVisible(false)}
      confirmLoading={confirmLoading}
      onOk={onSubmit}
      style={{ maxWidth: '90vw' }}
    >

      <Form autoComplete="off">
        <FormItem label="Site Name" required>
          <Input placeholder="Please enter site name" value={siteName} disabled />
        </FormItem>
        <FormItem label="Content" required>
          <Input.TextArea
            placeholder="Please enter content"
            value={content}
            onChange={setContent}
          />
        </FormItem>

      </Form>
    </Modal>
  );
}

export default CookieEditModal;
