import { createApi } from '@reduxjs/toolkit/query/react';
import {
  StatusResp, Cookie, NewCookieParam, DelCookieParam,
} from '../../utils/type';
import { baseQueryWithAuth } from '../auth/authQuery';

export const cookieApi = createApi({
  reducerPath: 'cookie',
  baseQuery: baseQueryWithAuth,
  tagTypes: ['Cookie'],
  endpoints: (builder) => ({
    getCookies: builder.query<Cookie, void>({
      query: () => '/cookie',
      providesTags: ['Cookie'],
    }),
    newCookie: builder.mutation<StatusResp, NewCookieParam>({
      query: ({ siteName, content }) => ({
        method: 'POST',
        url: `/cookie?site_name=${siteName}&content=${content}`,
      }),
      invalidatesTags: ['Cookie'],
    }),
    deleteCookie: builder.mutation<StatusResp, DelCookieParam>({
      query: ({ siteName, cookieId }) => ({
        method: 'DELETE',
        url: `/cookie/${cookieId}?site_name=${siteName}`,
      }),
      invalidatesTags: ['Cookie'],
    }),
  }),
});

export const {
  useGetCookiesQuery, useNewCookieMutation, useDeleteCookieMutation,
} = cookieApi;
