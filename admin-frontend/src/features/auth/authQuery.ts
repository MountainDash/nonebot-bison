import {
  BaseQueryFn, FetchArgs, fetchBaseQuery, FetchBaseQueryError,
} from '@reduxjs/toolkit/dist/query';
import { RootState } from '../../app/store';
import { baseUrl } from '../../utils/urls';
import { setLogout } from './authSlice';

const baseQuery = fetchBaseQuery({
  baseUrl,
  prepareHeaders: (headers, { getState }) => {
    const { token } = (getState() as RootState).auth;

    if (token) {
      headers.set('authorization', `Bearer ${token}`);
    }

    return headers;
  },
});

export const baseQueryWithAuth: BaseQueryFn<
string | FetchArgs,
unknown,
FetchBaseQueryError
> = async (args, api, extraOptions) => {
  const result = await baseQuery(args, api, extraOptions);
  if (result.error && result.error.status === 401) {
    api.dispatch(setLogout());
  }
  return result;
};

export default baseQueryWithAuth;
