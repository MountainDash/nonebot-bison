import { RootState, store } from '../../app/store';
import { baseUrl } from '../../utils/urls';

export default async function getTargetName(platformName: string, target: string) {
  const url = `${baseUrl}target_name?platformName=${platformName}&target=${target}`;
  const state = store.getState() as RootState;
  const authToken = state.auth.token;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });
  const resObj = await res.json();
  return resObj.targetName as string;
}
