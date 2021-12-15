import React, {useEffect} from "react";
import {useDispatch, useSelector} from "react-redux";
import {useParams} from "react-router";
import {Redirect} from 'react-router-dom';
import {login, loginSelector} from 'src/store/loginSlice';

interface AuthParam  {
  code: string
}
export function Auth() {
  const { code } = useParams<AuthParam>(); 
  const dispatch = useDispatch();
  const loginState = useSelector(loginSelector)
  useEffect(() => {
    const loginFun = async () => {
      dispatch(login(code));
    }
    loginFun();
  }, [code, dispatch])
  return <>
    { loginState.login ?
      <Redirect to={{pathname: '/admin'}} /> :
      loginState.failed ?
      <div>登录失败，请重新获取连接</div> :
      <div>Logining...</div>
    }
</>;
}
