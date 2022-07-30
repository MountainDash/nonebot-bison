import React, { useEffect } from 'react';
import { Navigate, useParams } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import { login, selectIsFailed, selectIsLogin } from './authSlice';

export default function Auth() {
  const isLogin = useAppSelector(selectIsLogin);
  const dispatch = useAppDispatch();
  const { code } = useParams();
  const isFailed = useAppSelector(selectIsFailed);

  useEffect(() => {
    if (!isLogin && code) {
      dispatch(login(code));
    }
  }, [isLogin, code]);
  return (
      { isLogin
        ? <Navigate to="/home" />
        : isFailed
          ? <Navigate to="/unauthed" />
          : <div> login </div>}
  );
}
