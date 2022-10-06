import {
  Action, combineReducers, configureStore, ThunkAction,
} from '@reduxjs/toolkit';
import {
  persistStore,
  persistReducer,
  FLUSH,
  REHYDRATE,
  PAUSE,
  PERSIST,
  PURGE,
  REGISTER,
} from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import authReducer from '../features/auth/authSlice';
import globalConfReducer from '../features/globalConf/globalConfSlice';
import { subscribeApi } from '../features/subsribeConfigManager/subscribeConfigSlice';
import { targetNameApi } from '../features/targetName/targetNameSlice';
import { weightApi } from '../features/weightConfig/weightConfigSlice';

const rootReducer = combineReducers({
  auth: authReducer,
  globalConf: globalConfReducer,
  [subscribeApi.reducerPath]: subscribeApi.reducer,
  [weightApi.reducerPath]: weightApi.reducer,
  [targetNameApi.reducerPath]: targetNameApi.reducer,
});

const persistConfig = {
  key: 'root',
  storage,
  whitelist: ['auth'],
};

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) => getDefaultMiddleware({
    serializableCheck: {
      ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER],
    },
  })
    .concat(subscribeApi.middleware)
    .concat(weightApi.middleware)
    .concat(targetNameApi.middleware),
});

export const persistor = persistStore(store);

export type AppDispatch = typeof store.dispatch;
export type RootState = ReturnType<typeof store.getState>;
export type AppThunk<ReturnType = void> = ThunkAction<
ReturnType,
RootState,
unknown,
Action<string>
>;
