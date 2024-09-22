import React, { useState } from 'react';
import {
  Button,
  Card, Descriptions, Grid, List, Popover, Typography,
} from '@arco-design/web-react';
import { selectSiteConf } from '../globalConf/globalConfSlice';
import { useAppSelector } from '../../app/hooks';
import { Cookie, SiteConfig } from '../../utils/type';
import { useGetCookiesQuery } from './cookieConfigSlice';
import CookieModal from './CookieModal';

interface CookieSite {
    site: SiteConfig;
    cookies: Cookie[];
}

export default function CookieManager() {
  const siteConf = useAppSelector(selectSiteConf);
  const { data: cookieDict } = useGetCookiesQuery();
  const cookiesList = cookieDict ? Object.values(cookieDict) : [];
  const cookieSite = Object.values(siteConf).filter((site) => site.enable_cookie);
  const cookieSiteList: CookieSite[] = cookieSite.map((site) => ({
    site,
    cookies: cookiesList.filter((cookie) => cookie.site_name === site.name),
  }));
  const [showModal, setShowModal] = useState(false);
  const [siteName, setSiteName] = useState('');

  const handleAddCookie = (newSiteName: string) => () => {
    console.log(newSiteName);
    setSiteName(newSiteName);
    setShowModal(true);
  };
  return (
    <>
      <Typography.Title heading={4} style={{ margin: '15px' }}>Cookie 管理</Typography.Title>

      <Grid.Row gutter={20}>
        {cookieSiteList && cookieSiteList.map(({ cookies, site }) => (
          <Grid.Col xs={24} sm={12} md={8} lg={6} key={site.name} style={{ margin: '1em 0' }}>
            <Card
              title={site.name}
              extra={(
                <Button
                  type="primary"
                  onClick={handleAddCookie(site.name)}
                >
                  添加
                </Button>
                            )}
            >

              {cookies.map((cookie) => (
                <List>

                  <Popover
                    key={cookie.id}
                    title={cookie.friendly_name}
                    content={(
                      <Descriptions
                        column={1}
                        title="Cookie 详情"
                        data={Object.entries(cookie).map((entry) => ({
                          label: entry[0].toString(),
                          value: entry[1].toString(),
                        }))}
                      />
                                        )}
                  >
                    <List.Item key={cookie.id}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        {cookie.friendly_name}
                        <Button type="primary" status="danger">删除</Button>
                      </div>
                    </List.Item>
                  </Popover>
                </List>
              ))}
            </Card>
          </Grid.Col>
        ))}
      </Grid.Row>
      <CookieModal visible={showModal} setVisible={setShowModal} siteName={siteName} />
    </>
  );
}
