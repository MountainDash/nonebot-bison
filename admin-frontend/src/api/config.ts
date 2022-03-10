import axios from "axios";
import {
  GlobalConf,
  TokenResp,
  SubscribeResp,
  TargetNameResp,
  SubscribeConfig,
} from "../utils/type";
import { baseUrl } from "./utils";

export async function getGlobalConf(): Promise<GlobalConf> {
  const res = await axios.get<GlobalConf>(`${baseUrl}global_conf`);
  return res.data;
}

export async function auth(token: string): Promise<TokenResp> {
  const res = await axios.get<TokenResp>(`${baseUrl}auth`, {
    params: { token },
  });
  return res.data;
}

export async function getSubscribe(): Promise<SubscribeResp> {
  const res = await axios.get(`${baseUrl}subs`);
  return res.data;
}

export async function getTargetName(
  platformName: string,
  target: string
): Promise<TargetNameResp> {
  const res = await axios.get(`${baseUrl}target_name`, {
    params: { platformName, target },
  });
  return res.data;
}

export async function addSubscribe(groupNumber: string, req: SubscribeConfig) {
  const res = await axios.post(`${baseUrl}subs`, req, {
    params: { groupNumber },
  });
  return res.data;
}

export async function delSubscribe(
  groupNumber: string,
  platformName: string,
  target: string
) {
  const res = await axios.delete(`${baseUrl}subs`, {
    params: { groupNumber, platformName, target },
  });
  return res.data;
}

export async function updateSubscribe(
  groupNumber: string,
  req: SubscribeConfig
) {
  return axios
    .patch(`${baseUrl}subs`, req, { params: { groupNumber } })
    .then((res) => res.data);
}
