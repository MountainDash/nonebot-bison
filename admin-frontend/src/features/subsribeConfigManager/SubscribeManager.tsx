import React from 'react';
import { SubscribeResp } from '../../utils/type';
import { useGetSubsQuery } from './subscribeConfigSlice';

export function SubscribeManager() {
  const {
    data: subs,
    isLoading,
    isFetching,
    isSuccess,
  } = useGetSubsQuery();
  return (
    <>
    </>
  );
}
