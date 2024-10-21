export interface TokenResp {
  token: string;
  type: string;
  id: number;
  name: string;
}

export interface GlobalConf {
  platformConf: AllPlatformConf;
  siteConf: AllSiteConf;
  loaded: boolean;
}

export interface AllPlatformConf {
  [idx: string]: PlatformConfig;
}

export interface AllSiteConf {
  [idx: string]: SiteConfig;
}

export interface CategoryConfig {
  [idx: number]: string;
}

export interface PlatformConfig {
  name: string;
  categories: CategoryConfig;
  enabledTag: boolean;
  platformName: string;
  siteName: string;
  hasTarget: boolean;
}

export interface SiteConfig {
  name: string;
  enable_cookie: string;
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
  ok: boolean;
  msg: string;
}

export interface SubmitParam {
  groupNumber: number;
  sub: SubscribeConfig;
}

export interface TimeWeightConfig {
  start_time: string;
  end_time: string;
  weight: number;
}

export interface WeightConfig {
  default: number;
  time_config: TimeWeightConfig[];
}

export interface PlatformWeightConfigResp {
  target: string;
  target_name: string;
  platform_name: string;
  weight: WeightConfig;
}

export interface Target {
  platform_name: string;
  target_name: string;
  target: string;
}

export interface Cookie {
  id: number;
  site_name: string;
  content: string;
  cookie_name: string;
  last_usage: Date;
  status: string;
  cd_milliseconds: number;
  is_universal: boolean;
  is_anonymous: boolean;
  tags: { [key: string]: string };
}

export interface CookieTarget {
  target: Target;
  cookie_id: number;
}

export interface NewCookieParam {
  siteName: string;
  content: string;
}

export interface DelCookieParam {
  cookieId: string;
}

export interface NewCookieTargetParam {
  platformName: string;
  target: string;
  cookieId: number;
}

export interface DelCookieTargetParam {
  platformName: string;
  target: string;
  cookieId: number;
}
