import { AnyAction, CaseReducer, createAsyncThunk, createSlice, PayloadAction, ThunkAction } from "@reduxjs/toolkit";
import jwt_decode from 'jwt-decode';
import { LoginStatus, TokenResp } from "src/utils/type";
import { auth } from "src/api/config";
import {RootState} from ".";

const initialState: LoginStatus = {
  login: false,
  type: '',
  name: '',
  id: '123',
  // groups: [],
  token: '',
  failed: false
}

interface storedInfo {
  type: string
  name: string
  id: string
}

const loginAction: CaseReducer<LoginStatus, PayloadAction<TokenResp>> = (_, action) => {
  return {
    login: true,
    failed: false,
    type: action.payload.type,
    name: action.payload.name,
    id: action.payload.id,
    token: action.payload.token
  }
}

export const login = createAsyncThunk(
  "auth/login",
  async (code: string) => {
    let res = await auth(code);
    if (res.status !== 200) {
      throw Error("Login Error")
    } else {
      localStorage.setItem('loginInfo', JSON.stringify({
        'type': res.type,
        'name': res.name,
        id: res.id,
      }))
      localStorage.setItem('token', res.token)
    }
    return res
  },
  {
    condition: (_: string, { getState }) => {
      const { login } = getState() as { login: LoginStatus }
      return !login.login;
    }
  }
)


export const loginSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    doLogin: loginAction
  },
  extraReducers: (builder) => {
    builder.addCase(login.fulfilled, loginAction);
    builder.addCase(login.rejected, (stat) => {
      stat.failed = true
    })
  }
})

export const { doLogin } = loginSlice.actions

export const loadLoginState = (): ThunkAction<void, RootState, unknown, AnyAction> =>
  (dispatch, getState) => {
    if (getState().login.login) {
      return
    }
    const infoJson = localStorage.getItem('loginInfo')
    const jwtToken = localStorage.getItem('token');
    if (infoJson && jwtToken) {
      const decodedJwt = jwt_decode(jwtToken) as { exp: number };
      if (decodedJwt.exp < Date.now() / 1000) {
        return
      }
      const info = JSON.parse(infoJson) as storedInfo
      const payload: TokenResp = {
        ...info,
        status: 200,
        token: jwtToken,
      }
      dispatch(doLogin(payload))
    }
  }

export const loginSelector = (state: RootState) => state.login

export default loginSlice.reducer
