import {CaseReducer, createAsyncThunk, createSlice, PayloadAction} from "@reduxjs/toolkit";
import {getGlobalConf as getGlobalConfApi} from "src/api/config";
import {GlobalConf} from "src/utils/type";
import {RootState} from ".";


const initialState: GlobalConf = {
  platformConf: {},
  loaded: false
}

const setGlobalConf: CaseReducer<GlobalConf, PayloadAction<GlobalConf>> = (_, action) => {
  return {...action.payload, loaded: true}
}

export const getGlobalConf = createAsyncThunk(
  "globalConf/set",
  getGlobalConfApi,
  {
    condition: (_, { getState }) => !(getState() as RootState).globalConf.loaded
  }
);

export const globalConfSlice = createSlice({
  name: "globalConf",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(getGlobalConf.fulfilled, setGlobalConf)
  }
})

export const platformConfSelector = (state: RootState) => state.globalConf.platformConf

export default globalConfSlice.reducer
