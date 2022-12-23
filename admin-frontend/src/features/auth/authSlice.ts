import {
  CaseReducer, createAsyncThunk, createSlice, PayloadAction,
} from '@reduxjs/toolkit';
import { RootState } from '../../app/store';
import { TokenResp } from '../../utils/type';
import { authUrl } from '../../utils/urls';

export interface AuthStatus {
  login: boolean;
  token: string;
  failed: boolean;
  userType: string;
  id: number;
}

const initialState = {
  login: false,
  failed: false,
  token: '',
  userType: '',
  id: 0,
} as AuthStatus;

export const login = createAsyncThunk(
  'auth/login',
  async (code: string) => {
    const res = await fetch(`${authUrl}?token=${code}`);
    return (await res.json()) as TokenResp;
  },
);

const setLoginReducer: CaseReducer<AuthStatus, PayloadAction<TokenResp>> = (state, action) => {
  state.login = true;
  state.id = action.payload.id;
  state.userType = action.payload.type;
  state.token = action.payload.token;
};

export const setLoginFailedReducer: CaseReducer<AuthStatus> = (state) => {
  state.login = false;
  state.failed = true;
};

export const setLogoutReducer: CaseReducer<AuthStatus> = (state) => {
  state.login = false;
};

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setLogin: setLoginReducer,
    setLogout: setLogoutReducer,
  },
  extraReducers(builder) {
    builder
      .addCase(login.pending, (state) => {
        state.failed = false;
      })
      .addCase(login.fulfilled, setLoginReducer)
      .addCase(login.rejected, setLogoutReducer);
  },
});

export const { setLogin, setLogout } = authSlice.actions;

export const selectIsLogin = (state: RootState) => state.auth.login;
export const selectIsFailed = (state: RootState) => state.auth.failed;

export default authSlice.reducer;
