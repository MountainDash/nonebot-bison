import React, { useState } from 'react';
import { Form, Input, Modal } from '@arco-design/web-react';

interface CookieModalProps {
  visible: boolean;
  setVisible: (arg0: boolean) => void;
  siteName: string;
}

function CookieModal({ visible, setVisible, siteName }: CookieModalProps) {
  const FormItem = Form.Item;
  const [content, setContent] = useState<string>('');
  // const [confirmLoading, setConfirmLoading] = useState(false);
  const [confirmLoading] = useState(false);
  return (
    <Modal
      title="添加 Cookie"
      visible={visible}
      onCancel={() => setVisible(false)}
      confirmLoading={confirmLoading}
      onOk={() => setVisible(false)}
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

export default CookieModal;
