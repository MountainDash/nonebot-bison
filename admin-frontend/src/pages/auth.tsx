import React, {useContext, useEffect, useState} from "react";
import { useParams } from "react-router";
import { auth } from '../api/config';
import { LoginContext } from '../utils/context';
import { Redirect } from 'react-router-dom'
interface AuthParam  {
  code: string
}
export function Auth() {
  const { code } = useParams<AuthParam>(); 
  const [ content, contentUpdate ] = useState(<div>Logining...</div>);
  const { save } = useContext(LoginContext);
  useEffect(() => {
    const loginFun = async () => {
      const resp = await auth(code);
      if (resp.status === 200) {
        save({login: true, type: resp.type, name: resp.name, id: resp.id, token: resp.token});
        contentUpdate(_ => <Redirect to={{pathname: '/admin'}} />);
        sessionStorage.setItem('token', resp.token);
      } else {
        contentUpdate(_ => <div>登录失败，请重新获取连接</div>);
      }
    }
    loginFun();
  }, [code, save])
  return content;
}
