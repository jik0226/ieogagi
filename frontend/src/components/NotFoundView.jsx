import { Link } from 'react-router-dom';

export default function NotFoundView() {
  return (
    <section className="state-screen">
      <h1 className="state-screen__title">페이지를 찾을 수 없습니다</h1>
      <p className="state-screen__text">주소를 다시 확인해 주세요.</p>
      <Link className="btn" to="/">
        처음으로
      </Link>
    </section>
  );
}
