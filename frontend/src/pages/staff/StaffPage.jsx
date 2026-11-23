import { useCallback, useState } from 'react';
import StaffHero from '../../components/StaffHero.jsx';
import StaffTodo from '../../components/StaffTodo.jsx';
import Tabs, { TabPanel } from '../../components/Tabs.jsx';
import { useTabParam } from '../../hooks/useTabParam.js';
import AccountsTab from './AccountsTab.jsx';
import AssignmentsTab from './AssignmentsTab.jsx';
import ChildrenTab from './ChildrenTab.jsx';

const TABS = [
  { id: 'children', label: '아동' },
  { id: 'assignments', label: '배정' },
  { id: 'accounts', label: '계정' },
];
const TAB_IDS = TABS.map((tab) => tab.id);

export default function StaffPage() {
  const [active, setActive] = useTabParam(TAB_IDS);
  // Counts in StaffTodo follow the work: a tab calls refreshTodo after it
  // saves a change, and the counts are read again on every tab switch.
  const [changes, setChanges] = useState(0);
  const refreshTodo = useCallback(() => setChanges((current) => current + 1), []);

  return (
    <>
      <StaffHero title="아동·배정·계정 관리" />
      <StaffTodo refreshKey={`${active}:${changes}`} onOpen={setActive} />
      <Tabs label="관리 메뉴" tabs={TABS} active={active} onChange={setActive} />
      <TabPanel id={active}>
        {active === 'children' && <ChildrenTab onChanged={refreshTodo} />}
        {active === 'assignments' && <AssignmentsTab onChanged={refreshTodo} />}
        {active === 'accounts' && <AccountsTab onChanged={refreshTodo} />}
      </TabPanel>
    </>
  );
}
