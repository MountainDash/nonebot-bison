import { createApi } from '@reduxjs/toolkit/query/react';
import baseQueryWithAuth from '../auth/authQuery';

export const weightApi = createApi({
  reducerPath: 'weight',
  baseQuery: baseQueryWithAuth,
  tagTypes: ['Weight'],
  endpoints: (builder) => ({
    getWeight: builder.query<any, void>({
      query: () => '/weight',
      providesTags: ['Weight'],
    }),
  }),
});

export const {
  useGetWeightQuery,
} = weightApi;
