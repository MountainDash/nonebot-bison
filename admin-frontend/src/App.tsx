import 'antd/dist/antd.css';
import React, {useEffect} from 'react';
import {useDispatch, useSelector} from 'react-redux';
import {BrowserRouter as Router, Route, Switch} from 'react-router-dom';
import './App.css';
import {Admin} from './pages/admin';
import {Auth} from './pages/auth';
import {getGlobalConf} from './store/globalConfSlice';
import {useAppSelector} from './store/hooks';
import {loadLoginState, loginSelector} from './store/loginSlice';


function LoginSwitch() {
  const login = useSelector(loginSelector)
  if (login.login) {
    return <Admin />;
  } else {
    return (
      <div>
        not login
      </div>
    )
  }
}

function App() {
  const dispatch = useDispatch()
  const globalConf = useAppSelector(state => state.globalConf)
  useEffect(() => {
    dispatch(getGlobalConf());
    dispatch(loadLoginState())
  }, [dispatch]);
  return <>
      { globalConf.loaded &&
        <Router basename="/bison">
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
    </>;
}

export default App;
