export interface TokenResp {
  status: number;
  token: string;
  type: string;
  id: number;
  name: string;
}
export interface GlobalConf {
  platformConf: AllPlatformConf;
  loaded: boolean;
}

export interface AllPlatformConf {
  [idx: string]: PlatformConfig;
}

export interface CategoryConfig {
  [idx: number]: string;
}

export interface PlatformConfig {
  name: string;
  categories: CategoryConfig;
  enabledTag: boolean;
  platformName: string;
  hasTarget: boolean;
}

export interface SubscribeConfig {
  platformName: string;
  target: string;
  targetName: string;
  cats: Array<number>;
  tags: Array<string>;
}

export interface SubscribeGroupDetail {
  name: string;
  subscribes: Array<SubscribeConfig>;
}

export interface SubscribeResp {
  [idx: string]: SubscribeGroupDetail;
}

export interface StatusResp {
  status: number;
  msg: string;
}
