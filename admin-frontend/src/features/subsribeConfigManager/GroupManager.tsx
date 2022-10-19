import React, { useState } from 'react';
import {
  Card, Typography, Grid, Button,
} from '@arco-design/web-react';
import { Link } from 'react-router-dom';
import { useGetSubsQuery } from './subscribeConfigSlice';
import SubscribeModal from './SubscribeModal';

export default function GroupManager() {
  const [modalGroupNumber, setModalGroupNumber] = useState('');
  const [showModal, setShowModal] = useState(false);
  const { data: subs } = useGetSubsQuery();

  const handleAddSub = (groupNumber: string) => () => {
    setModalGroupNumber(groupNumber);
    setShowModal(true);
  };

  return (
    <>
      <Typography.Title heading={4} style={{ margin: '15px' }}>群管理</Typography.Title>
      <div>
        { subs && (
          <Grid.Row gutter={20}>
            { Object.keys(subs).map(
              (groupNumber: string) => (
                <Grid.Col xs={24} sm={12} md={8} lg={6} key={groupNumber} style={{ margin: '1em 0' }}>
                  <Card
                    title={subs[groupNumber].name}
                    actions={[
                      <Link to={`/home/groups/${groupNumber}`}><Button>详情</Button></Link>,
                      <Button type="primary" onClick={handleAddSub(groupNumber)}>添加</Button>,
                    ]}
                  >
                    <div>{groupNumber}</div>
                  </Card>
                </Grid.Col>
              ),
            )}
          </Grid.Row>
        )}
      </div>
      <SubscribeModal
        groupNumber={modalGroupNumber}
        visible={showModal}
        setVisible={setShowModal}
      />
    </>
  );
}
