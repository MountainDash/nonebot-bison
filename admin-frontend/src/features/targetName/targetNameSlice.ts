import { createApi } from '@reduxjs/toolkit/query/react';
import baseQueryWithAuth from '../auth/authQuery';

export const targetNameApi = createApi({
  reducerPath: 'targetName',
  baseQuery: baseQueryWithAuth,
  endpoints: (builder) => ({
    getTargetName: builder.query<{targetName: string}, {target: string; platformName: string}>({
      query: () => '/target_name',
    }),
  }),
});

export const { useGetTargetNameQuery } = targetNameApi;
