interface QQGroup {
  id: string,
  name: string,
}

export interface LoginStatus {
  login: boolean
  type: string
  name: string
  id: string
  // groups: Array<QQGroup>
  token: string
}

export type LoginContextType = {
  login: LoginStatus
  save: (status: LoginStatus) => void
}

export interface SubscribeConfig {
  platformName: string
  target?: string
  targetName: string
  cats: Array<number>
  tags: Array<string>
}

export interface GlobalConf {
  platformConf: AllPlatformConf,
  loaded: boolean
}

export interface AllPlatformConf {
  [idx: string]: PlatformConfig;
}

export interface CategoryConfig {
  [idx: number]: string
}

export interface PlatformConfig {
  name: string
  categories: CategoryConfig
  enabledTag: boolean,
  platformName: string,
  hasTarget: boolean
}

export interface TokenResp {
  status: number,
  token: string,
  type: string,
  id: string
  name: string
}

export interface SubscribeGroupDetail {
  name: string,
  subscribes: Array<SubscribeConfig>
}

export interface SubscribeResp {
  [idx: string]: SubscribeGroupDetail
}

export interface TargetNameResp {
  targetName: string
}

export interface CreateSubscribeReq {
  platformName: string,
  targetName: string,
  target: string,
  categories: Array<string>,
  tags: Array<string>
}
