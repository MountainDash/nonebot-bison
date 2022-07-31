import { createApi } from '@reduxjs/toolkit/query/react';
import { StatusResp, SubscribeConfig, SubscribeResp } from '../../utils/type';
import { baseQueryWithAuth } from '../auth/authQuery';

export const subscribeApi = createApi({
  reducerPath: 'subscribe',
  baseQuery: baseQueryWithAuth,
  tagTypes: ['Subscribe'],
  endpoints: (builder) => ({
    getSubs: builder.query<SubscribeResp, void>({
      query: () => '/subs',
      providesTags: ['Subscribe'],
    }),
    newSub: builder.mutation<StatusResp, SubscribeConfig>({
      query: (config) => ({
        method: 'POST',
        url: '/subs',
        body: config,
      }),
      invalidatesTags: ['Subscribe'],
    }),
    updateSub: builder.mutation<StatusResp, SubscribeResp>({
      query: (config) => ({
        method: 'PATCH',
        url: '/subs',
        body: config,
      }),
      invalidatesTags: ['Subscribe'],
    }),
  }),
});

export const { useGetSubsQuery } = subscribeApi;
