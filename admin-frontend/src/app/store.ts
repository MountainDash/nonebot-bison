import { configureStore, ThunkAction, Action } from '@reduxjs/toolkit';
import authReducer from '../features/auth/authSlice';
import globalConfReducer from '../features/globalConf/globalConfSlice';
import { subscribeApi } from '../features/subsribeConfigManager/subscribeConfigSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    globalConf: globalConfReducer,
    [subscribeApi.reducerPath]: subscribeApi.reducer,
  },
  middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(subscribeApi.middleware),
});

export type AppDispatch = typeof store.dispatch;
export type RootState = ReturnType<typeof store.getState>;
export type AppThunk<ReturnType = void> = ThunkAction<
ReturnType,
RootState,
unknown,
Action<string>
>;
