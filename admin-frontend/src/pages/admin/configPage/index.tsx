import {Button, Collapse, Empty, Row} from 'antd';
import React, {ReactElement, useEffect, useState} from "react";
import {useDispatch, useSelector} from 'react-redux';
import {AddModal} from 'src/component/addSubsModal';
import {SubscribeCard} from 'src/component/subscribeCard';
import {groupConfigSelector, updateGroupSubs} from 'src/store/groupConfigSlice';

interface ConfigPageProp {
  tab: string
}
export function ConfigPage(prop: ConfigPageProp) {
  const [ showModal, setShowModal ] = useState<boolean>(false);
  const [ currentAddingGroupNumber, setCurrentAddingGroupNumber ] = useState('');
  const configData = useSelector(groupConfigSelector);
  const dispatcher = useDispatch();
  useEffect(() => {
    dispatcher(updateGroupSubs())
  }, [prop.tab, dispatcher]);
  const clickNew = (groupNumber: string) => (e: React.MouseEvent<HTMLButtonElement>) => {
    setShowModal(_ => true);
    setCurrentAddingGroupNumber(groupNumber);
    e.stopPropagation();
  }
  
  if (Object.keys(configData).length === 0) {
    return <Empty />
  } else {
    let groups: Array<ReactElement> = [];
    for (let key of Object.keys(configData)) {
      let value = configData[key];
      groups.push(
        <Collapse.Panel key={key} header={
          <span>{`${key} - ${value.name}`}<Button style={{float: "right"}} onClick={clickNew(key)}>添加</Button></span>
          }>
            <Row gutter={[{ xs: 8, sm: 16, md: 24, lg: 32},
              { xs: 8, sm: 16, md: 24, lg: 32}]} align="middle">
            {value.subscribes.map((subs, idx) => <SubscribeCard key={idx}
              groupNumber={key} config={subs} />)}
          </Row>
        </Collapse.Panel>
        )
    }
    return (
    <div>
      <Collapse>
        {groups}
      </Collapse>
      <AddModal groupNumber={currentAddingGroupNumber} showModal={showModal} 
        refresh={() => dispatcher(updateGroupSubs())}
        setShowModal={(s: boolean) => setShowModal(_ => s)} />
    </div>
    )
  }
}


