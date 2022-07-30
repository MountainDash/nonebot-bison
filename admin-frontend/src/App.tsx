import React, { useEffect } from 'react';
import { Route, Routes } from 'react-router-dom';
import './App.css';
import { useAppDispatch, useAppSelector } from './app/hooks';
import Auth from './features/auth/Auth';
import { loadGlobalConf, selectGlobalConfLoaded } from './features/globalConf/globalConfSlice';
import Home from './pages/Home';
import Unauthed from './pages/Unauthed';

function App() {
  const dispatch = useAppDispatch();
  const globalConfLoaded = useAppSelector(selectGlobalConfLoaded);

  useEffect(() => {
    if (!globalConfLoaded) {
      dispatch(loadGlobalConf());
    }
  }, [globalConfLoaded]);

  return (
    <>
      { globalConfLoaded
      && (
      <Routes>
        <Route path="/auth/:code" element={<Auth />} />
        <Route path="/unauthed" element={<Unauthed />} />
        <Route path="/home" element={<Home />} />
      </Routes>
      )}
    </>
  );
}

export default App;
