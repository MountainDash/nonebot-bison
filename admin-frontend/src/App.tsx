import React, { useContext, useEffect, useState } from 'react';
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom';
import './App.css';
import { LoginContext, loginContextDefault, GlobalConfContext } from './utils/context';
import { LoginStatus, GlobalConf, AllPlatformConf } from './utils/type';
import { Admin } from './pages/admin';
import { getGlobalConf } from './api/config';
import { Auth } from './pages/auth';
import 'antd/dist/antd.css';


function LoginSwitch() {
  const {login, save} = useContext(LoginContext);
  if (login.login) {
    return <Admin />;
  } else {
    return (
      <div>
        not login
        <button onClick={() => save({
            login: true, type: 'admin', name: '', id: '123', token: ''
            })}>1</button>
      </div>
    )
  }
}

function App() {
  const [loginStatus, setLogin] = useState(loginContextDefault.login);
  const [globalConf, setGlobalConf] = useState<GlobalConf>({platformConf: {} as AllPlatformConf, loaded: false});
  // const globalConfContext = useContext(GlobalConfContext);
  const save = (login: LoginStatus) => setLogin(_ => login);
  useEffect(() => {
    const fetchGlobalConf = async () => {
      const res = await getGlobalConf();
      setGlobalConf(_ => {return {...res, loaded: true}});
    };
    fetchGlobalConf();
  }, []);
  return (
    <LoginContext.Provider value={{login: loginStatus, save}}>
      <GlobalConfContext.Provider value={globalConf}>
      { globalConf.loaded &&
        <Router basename="/hk_reporter">
          <Switch>
            <Route path="/auth/:code">
              <Auth />   
            </Route>
            <Route path="/admin/">
              <LoginSwitch /> 
            </Route>
          </Switch>
        </Router>
      }
      </GlobalConfContext.Provider>
    </LoginContext.Provider>
  );
}

export default App;
