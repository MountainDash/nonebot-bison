import {configureStore} from "@reduxjs/toolkit";
import loginSlice from "./loginSlice";
import globalConfSlice from "./globalConfSlice";

const store = configureStore({
  reducer: {
    login: loginSlice,
    globalConf: globalConfSlice,
  }
})

export default store;

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
