import { AppThunk } from '../../app/store';
import { baseUrl } from '../../utils/urls';

// eslint-disable-next-line
export const validCookie =
  (siteName: string, content: string): AppThunk<Promise<string>> => async (_, getState) => {
    const url = `${baseUrl}cookie/validate?site_name=${siteName}&content=${content}`;
    const state = getState();
    const authToken = state.auth.token;
    const res = await fetch(url, {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
      method: 'POST',
    });
    const resObj = await res.json();
    return resObj.ok;
  };

export default validCookie;
