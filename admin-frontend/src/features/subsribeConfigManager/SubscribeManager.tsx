import React from 'react';
import { useGetSubsQuery, useDeleteSubMutation } from './subscribeConfigSlice';

export default function SubscribeManager() {
  const { data: subs } = useGetSubsQuery();
  const [patchSub] = useDeleteSubMutation();

  const createNewSub = () => {
    patchSub({ target: '2773976700', platformName: 'weibo', groupNumber: 868610060 }).unwrap();
  };
  return (
    <>
      <div>{ subs && JSON.stringify(subs) }</div>
      <div>1</div>
      <button onClick={() => createNewSub()} type="button">new</button>
    </>
  );
}
