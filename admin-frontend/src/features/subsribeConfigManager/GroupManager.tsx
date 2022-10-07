import React from 'react';
import {
  Card, Typography, Grid, Button,
} from '@arco-design/web-react';
import { Link } from 'react-router-dom';
import { useGetSubsQuery } from './subscribeConfigSlice';

export default function GroupManager() {
  const { data: subs } = useGetSubsQuery();
  return (
    <>
      <Typography.Title heading={4} style={{ margin: '15px' }}>群管理</Typography.Title>
      <div>
        { subs && (
          <Grid.Row gutter={20}>
            { Object.keys(subs).map(
              (groupNumber: string) => (
                <Grid.Col span={6} key={groupNumber}>
                  <Card
                    title={subs[groupNumber].name}
                    actions={[
                      <Link to={`/home/groups/${groupNumber}`}><Button>详情</Button></Link>,
                      <Button type="primary">添加</Button>,
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
    </>
  );
}
