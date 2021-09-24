import { createContext } from "react";
import { LoginContextType, GlobalConf } from "./type";

export const loginContextDefault: LoginContextType = {
  login: {
    login: false,
    type: '',
    name: '',
    id: '123',
    // groups: [],
    token: ''
  },
  save: () => {}
};

export const LoginContext = createContext(loginContextDefault);
export const GlobalConfContext = createContext<GlobalConf>({platformConf: []});
