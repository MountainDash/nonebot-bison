import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { RootState } from '../../app/store';
import { GlobalConf } from '../../utils/type';
import { globalConfUrl } from '../../utils/urls';

const initialState = {
  loaded: false,
  platformConf: {},
  siteConf: {},
} as GlobalConf;

export const loadGlobalConf = createAsyncThunk(
  'globalConf/load',
  async () => {
    const res = await fetch(globalConfUrl);
    return (await res.json()) as GlobalConf;
  },
);

export const globalConfSlice = createSlice({
  name: 'globalConf',
  initialState,
  reducers: {},
  extraReducers(builder) {
    builder
      .addCase(loadGlobalConf.fulfilled, (state, payload) => {
        state.platformConf = payload.payload.platformConf;
        state.siteConf = payload.payload.siteConf;
        state.loaded = true;
      });
  },
});

export default globalConfSlice.reducer;

export const selectGlobalConfLoaded = (state: RootState) => state.globalConf.loaded;
export const selectPlatformConf = (state: RootState) => state.globalConf.platformConf;
export const selectSiteConf = (state: RootState) => state.globalConf.siteConf;
