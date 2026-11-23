import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

// A new screen starts at the top (e.g. after saving a long form, the
// "저장했습니다" notice must be in view).
export default function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}
