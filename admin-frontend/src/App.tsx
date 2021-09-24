import React, { useContext, useEffect, useState } from 'react';
import { HashRouter as Router, Route, Switch } from 'react-router-dom';
import './App.css';
import { LoginContext, loginContextDefault, GlobalConfContext } from './utils/context';
import { LoginStatus, GlobalConf } from './utils/type';
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
  const [globalConf, setGlobalConf] = useState<GlobalConf>({platformConf: []});
  // const globalConfContext = useContext(GlobalConfContext);
  const save = (login: LoginStatus) => setLogin(_ => login);
  useEffect(() => {
    const fetchGlobalConf = async () => {
      const res = await getGlobalConf();
      setGlobalConf(_ => res);
    };
    fetchGlobalConf();
  }, []);
  return (
    <LoginContext.Provider value={{login: loginStatus, save}}>
      <GlobalConfContext.Provider value={globalConf}>
        <Router>
          <Switch>
            <Route path="/auth/:code">
              <Auth />   
            </Route>
            <Route path="/admin/">
              <LoginSwitch /> 
            </Route>
          </Switch>
        </Router>
      </GlobalConfContext.Provider>
    </LoginContext.Provider>
  );
}

export default App;
