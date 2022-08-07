import React from 'react';
import { useGetSubsQuery } from './subscribeConfigSlice';

export default function SubscribeManager() {
  const { data: subs } = useGetSubsQuery();

  return (
    <>
      <div>{ subs && JSON.stringify(subs) }</div>
      <div>1</div>
    </>
  );
}
