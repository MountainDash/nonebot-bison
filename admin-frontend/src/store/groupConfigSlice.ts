import {
  CaseReducer,
  createAsyncThunk,
  createSlice,
  PayloadAction,
} from "@reduxjs/toolkit";
import { SubscribeResp } from "src/utils/type";
import { getSubscribe } from "src/api/config";
import { RootState } from ".";
const initialState: SubscribeResp = {};

const setSubs: CaseReducer<SubscribeResp, PayloadAction<SubscribeResp>> = (
  _,
  action
) => {
  return action.payload;
};

export const updateGroupSubs = createAsyncThunk(
  "groupConfig/update",
  getSubscribe
);

export const groupConfigSlice = createSlice({
  name: "groupConfig",
  initialState,
  reducers: {
    setSubs,
  },
  extraReducers: (reducer) => {
    reducer.addCase(updateGroupSubs.fulfilled, setSubs);
  },
});

export const groupConfigSelector = (state: RootState) => state.groupConfig;
export default groupConfigSlice.reducer;
