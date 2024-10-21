import { createApi } from '@reduxjs/toolkit/query/react';
import {
  StatusResp, Cookie, NewCookieParam,
  DelCookieParam, CookieTarget, NewCookieTargetParam, DelCookieTargetParam,
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
      query: ({ cookieId }) => ({
        method: 'DELETE',
        url: `/cookie/${cookieId}`,
      }),
      invalidatesTags: ['Cookie'],
    }),
  }),
});

export const {
  useGetCookiesQuery, useNewCookieMutation, useDeleteCookieMutation,
} = cookieApi;

export const cookieTargetApi = createApi({
  reducerPath: 'cookieTarget',
  baseQuery: baseQueryWithAuth,
  tagTypes: ['CookieTarget'],
  endpoints: (builder) => ({
    getCookieTargets: builder.query<CookieTarget[], { cookieId: number }>({
      query: ({ cookieId }) => `/cookie_target?cookie_id=${cookieId}`,
      providesTags: ['CookieTarget'],
    }),
    newCookieTarget: builder.mutation<StatusResp, NewCookieTargetParam>({
      query: ({ platformName, target, cookieId }) => ({
        method: 'POST',
        url: `/cookie_target?platform_name=${platformName}&target=${encodeURIComponent(target)}&cookie_id=${cookieId}`,
      }),
      invalidatesTags: ['CookieTarget'],
    }),
    deleteCookieTarget: builder.mutation<StatusResp, DelCookieTargetParam>({
      query: ({ platformName, target, cookieId }) => ({
        method: 'DELETE',
        url: `/cookie_target?platform_name=${platformName}&target=${encodeURIComponent(target)}&cookie_id=${cookieId}`,
      }),
      invalidatesTags: ['CookieTarget'],
    }),
  }),
});

export const {
  useGetCookieTargetsQuery, useNewCookieTargetMutation, useDeleteCookieTargetMutation,
} = cookieTargetApi;
