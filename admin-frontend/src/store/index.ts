import {configureStore} from "@reduxjs/toolkit";
import loginSlice from "./loginSlice";
import globalConfSlice from "./globalConfSlice";
import groupConfigSlice from './groupConfigSlice';

const store = configureStore({
  reducer: {
    login: loginSlice,
    globalConf: globalConfSlice,
    groupConfig: groupConfigSlice,
  }
})

export default store;

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export type Store = typeof store;
