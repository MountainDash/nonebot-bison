import React from 'react';
import { useGetWeightQuery } from './weightConfigSlice';

export default function WeightManager() {
  const { data: weight } = useGetWeightQuery();
  return (
    <div>{weight && JSON.stringify(weight)}</div>
  );
}
