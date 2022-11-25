import { createApi } from '@reduxjs/toolkit/query/react';
import {
  StatusResp, SubmitParam, SubscribeResp,
} from '../../utils/type';
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
    newSub: builder.mutation<StatusResp, SubmitParam>({
      query: ({ groupNumber, sub }) => ({
        method: 'POST',
        url: `/subs?groupNumber=${groupNumber}`,
        body: sub,
      }),
      invalidatesTags: ['Subscribe'],
    }),
    updateSub: builder.mutation<StatusResp, SubmitParam>({
      query: ({ groupNumber, sub }) => ({
        method: 'PATCH',
        url: `/subs?groupNumber=${groupNumber}`,
        body: sub,
      }),
      invalidatesTags: ['Subscribe'],
    }),
    deleteSub: builder.mutation<StatusResp,
      { groupNumber: number; target: string; platformName: string }>({
        query: ({ groupNumber, target, platformName }) => ({
          method: 'DELETE',
          url: `/subs?groupNumber=${groupNumber}&target=${encodeURIComponent(target)}&platformName=${platformName}`,
        }),
        invalidatesTags: ['Subscribe'],
      }),
  }),
});

export const {
  useGetSubsQuery, useNewSubMutation, useDeleteSubMutation, useUpdateSubMutation,
} = subscribeApi;
