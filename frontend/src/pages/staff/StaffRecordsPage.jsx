import StaffHero from '../../components/StaffHero.jsx';
import Tabs, { TabPanel } from '../../components/Tabs.jsx';
import { useTabParam } from '../../hooks/useTabParam.js';
import AuditTab from './AuditTab.jsx';
import RecordsTab from './RecordsTab.jsx';

const TABS = [
  { id: 'records', label: '기록·메모' },
  { id: 'audit', label: '감사 로그' },
];
const TAB_IDS = TABS.map((tab) => tab.id);

export default function StaffRecordsPage() {
  const [active, setActive] = useTabParam(TAB_IDS);

  return (
    <>
      <StaffHero title="기록 관리·감사 로그" />
      <Tabs label="기록 관리 메뉴" tabs={TABS} active={active} onChange={setActive} />
      <TabPanel id={active}>
        {active === 'records' && <RecordsTab />}
        {active === 'audit' && <AuditTab />}
      </TabPanel>
    </>
  );
}
