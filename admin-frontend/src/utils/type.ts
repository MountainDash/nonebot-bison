export interface LoginStatus {
  login: boolean
  type: String
  name: String
}

export type LoginContextType = {
  login: LoginStatus
  save: (status: LoginStatus) => void
}

export interface SubscribeConfig {
  platform: String
  target?: String
  catetories: Array<number>
  tags: Array<String>
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
