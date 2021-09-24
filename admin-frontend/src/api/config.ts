import axios from "axios";
import { GlobalConf, TokenResp } from "../utils/type";
import { baseUrl } from './utils';

export async function getGlobalConf(): Promise<GlobalConf> {
  const res = await axios.get<GlobalConf>(`${baseUrl}global_conf`);
  return res.data;
}

export async function auth(token: string): Promise<TokenResp> {
  const res = await axios.get<TokenResp>(`${baseUrl}auth`, {params: {token}});
  return res.data;
}
