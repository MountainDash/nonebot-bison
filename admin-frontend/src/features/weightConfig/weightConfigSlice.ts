import { createApi } from '@reduxjs/toolkit/query/react';
import { PlatformWeightConfigResp, StatusResp } from '../../utils/type';
import baseQueryWithAuth from '../auth/authQuery';

export const weightApi = createApi({
  reducerPath: 'weight',
  baseQuery: baseQueryWithAuth,
  tagTypes: ['Weight'],
  endpoints: (builder) => ({
    getWeight: builder.query<PlatformWeightConfigResp, void>({
      query: () => '/weight',
      providesTags: ['Weight'],
    }),
    updateWeight: builder.mutation<StatusResp,
      Pick<PlatformWeightConfigResp, 'platform_name' | 'target' | 'weight' >>({
        query: ({ platform_name: platformName, target, weight }) => ({
          method: 'PUT',
          url: `/weight?platform_name=${platformName}&target=${target}`,
          body: weight,
        }),
        invalidatesTags: ['Weight'],
      }),
  }),
});

export const {
  useGetWeightQuery, useUpdateWeightMutation,
} = weightApi;
