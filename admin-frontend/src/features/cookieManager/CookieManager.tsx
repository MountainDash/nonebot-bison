import React, { useState } from 'react';
import {
  Button,
  Card, Descriptions, Grid, List, Popconfirm, Popover, Typography,
} from '@arco-design/web-react';
import { Link } from 'react-router-dom';
import { IconDelete, IconEdit } from '@arco-design/web-react/icon';
import { selectSiteConf } from '../globalConf/globalConfSlice';
import { useAppSelector } from '../../app/hooks';
import { Cookie, SiteConfig } from '../../utils/type';
import { useGetCookiesQuery, useDeleteCookieMutation } from './cookieConfigSlice';
import CookieModal from './CookieModal';
import './CookieManager.css';

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
  const [deleteCookie] = useDeleteCookieMutation();

  const handleAddCookie = (newSiteName: string) => () => {
    console.log(newSiteName);
    setSiteName(newSiteName);
    setShowModal(true);
  };
  const handleDelCookie = (cookieId: string) => () => {
    console.log(cookieId);
    deleteCookie({
      cookieId,
    });
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

                  <List.Item key={cookie.id}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>

                      <Popover
                        key={cookie.id}
                        title={cookie.friendly_name}
                        content={(
                          <Descriptions
                            column={1}
                            title="Cookie 详情"
                            data={Object.entries(cookie).map((entry) => ({
                              label: entry[0].toString(),
                              value: typeof (entry[1]) === 'object' ? JSON.stringify(entry[1]) : entry[1].toString(),
                            }))}
                          />
                        )}
                      >
                        {cookie.friendly_name}

                      </Popover>

                      <div style={{ display: 'flex' }}>

                        <Link to={`/home/cookie/${cookie.id}`}>
                          <span className="list-actions-icon">
                            <IconEdit />
                          </span>
                        </Link>
                        <Popconfirm
                          title={`确定删除 Cookie ${cookie.friendly_name} ？`}
                          onOk={handleDelCookie(cookie.id.toString())}
                        >
                          <span className="list-actions-icon">
                            <IconDelete />
                          </span>
                        </Popconfirm>
                      </div>

                    </div>
                  </List.Item>
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
