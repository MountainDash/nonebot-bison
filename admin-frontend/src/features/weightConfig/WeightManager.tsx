import React from 'react';
// import { WeightConfig } from '../../utils/type';
// import { useGetWeightQuery, useUpdateWeightMutation } from './weightConfigSlice';
//
// export default function WeightManager() {
//   const { data: weight } = useGetWeightQuery();
//   const [updateWeight] = useUpdateWeightMutation();
//
//   const doUpdate = () => {
//     const weightConfig: WeightConfig = {
//       default: 20,
//       time_config: [
//         {
//           start_time: '01:00',
//           end_time: '02:00',
//           weight: 50,
//         },
//       ],
//     };
//     updateWeight({ weight: weightConfig, platform_name: 'weibo', target: '' });
//   };
//   return (
//     <>
//       <div>{weight && JSON.stringify(weight)}</div>
//       <button type="button" onClick={doUpdate}> 123</button>
//     </>
//   );
// }

export default function WeightConfig() {
  return <div>下个版本再写</div>;
}
