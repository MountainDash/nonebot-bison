import React, { useEffect } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import './App.css';
import { useAppDispatch, useAppSelector } from './app/hooks';
import Auth from './features/auth/Auth';
import { loadGlobalConf, selectGlobalConfLoaded } from './features/globalConf/globalConfSlice';
import GroupManager from './features/subsribeConfigManager/GroupManager';
import SubscribeManager from './features/subsribeConfigManager/SubscribeManager';
import WeightConfig from './features/weightConfig/WeightManager';
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

  const router = createBrowserRouter([
    {
      path: '/auth/:code',
      element: <Auth />,
    },
    {
      path: '/unauthed',
      element: <Unauthed />,
    },
    {
      path: '/home/',
      element: <Home />,
      // loader: homeLoader,
      children: [
        {
          path: 'groups',
          element: <GroupManager />,
        },
        {
          path: 'groups/:groupNumber',
          element: <SubscribeManager />,
        },
        {
          path: 'weight',
          element: <WeightConfig />,
        },
      ],
    },
  ], { basename: '/bison' });

  return (
    globalConfLoaded
      ? (
        <RouterProvider router={router} />
      ) : <div>loading</div>
  );
}

export default App;
