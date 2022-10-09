import { AppThunk } from '../../app/store';
import { baseUrl } from '../../utils/urls';

// eslint-disable-next-line
export const getTargetName =
  (platformName: string, target: string): AppThunk<Promise<string>> => async (_, getState) => {
    const url = `${baseUrl}target_name?platformName=${platformName}&target=${target}`;
    const state = getState();
    const authToken = state.auth.token;
    const res = await fetch(url, {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
    const resObj = await res.json();
    return resObj.targetName as string;
  };

export default getTargetName;
