import axios from "axios";
// import { useContext } from 'react';
// import { LoginContext } from "../utils/context";

export const baseUrl = '/hk_reporter/api/'

// const loginStatus = useContext(LoginContext);
axios.interceptors.request.use(function (config) {
  if (config.url && config.url.startsWith(baseUrl) && config.url !== `${baseUrl}auth` 
     && config.url !== `${baseUrl}global_conf`) {
    const token = sessionStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    } else {
      throw new axios.Cancel('User not login');
    }
  }
  return config;
}, function (error) {
  return Promise.reject(error);
})
