import axios from "axios";
// import { useContext } from 'react';
// import { LoginContext } from "../utils/context";

export const baseUrl = '/bison/api/'

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
});

axios.interceptors.response.use(function (response) {
  // const data = response.data;
  // const parseToMap = (item: any): any => {
  //   if (item instanceof Array) {
  //     return item.map(parseToMap);
  //   } else if (item instanceof Object) {
  //     let res = new Map();
  //     for (const key of Object.keys(item)) {
  //       res.set(key, parseToMap(item[key]));
  //     }
  //     return res;
  //   } else {
  //     return item;
  //   }
  // }
  // response.data = parseToMap(data);
  return response;
});
