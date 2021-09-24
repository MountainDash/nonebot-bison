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
  platform: string
  target?: string
  catetories: Array<number>
  tags: Array<string>
}

export interface GlobalConf {
  platformConf: Array<PlatformConfig>
}

export interface PlatformConfig {
  name: string
  catetories: Map<number, string>,
  enableTag: boolean,
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
