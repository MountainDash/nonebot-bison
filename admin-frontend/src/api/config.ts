import axios from "axios";
import { GlobalConf } from "../utils/type";

const baseUrl = '/hk_reporter/api/'

export async function getGlobalConf(): Promise<GlobalConf> {
  const res = await axios.get<GlobalConf>(`${baseUrl}global_conf`);
  return res.data;
}
