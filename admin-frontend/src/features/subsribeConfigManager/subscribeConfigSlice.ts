import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { RootState } from '../../app/store';
import { StatusResp, SubscribeResp, SubscribeConfig } from '../../utils/type';
import { subsribeUrl } from '../../utils/urls';
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
