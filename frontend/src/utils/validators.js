// Light client-side checks. The server is the real validator.
const LOGIN_ID_PATTERN = /^[a-z0-9_]{4,32}$/;
const DISPLAY_NAME_PATTERN = /^[0-9A-Za-zㄱ-ㆎ가-힣 ._-]{1,30}$/;

export function checkLoginId(value) {
  if (!LOGIN_ID_PATTERN.test(value)) {
    return '아이디는 영문 소문자·숫자·밑줄(_) 4~32자로 입력해 주세요.';
  }
  return '';
}

export function checkDisplayName(value) {
  if (!DISPLAY_NAME_PATTERN.test(value)) {
    return '이름은 한글·영문·숫자·공백·마침표·하이픈·밑줄 1~30자로 입력해 주세요.';
  }
  return '';
}

export function checkNewPassword(value) {
  if (value.length < 10 || value.length > 128) {
    return '비밀번호는 10~128자로 입력해 주세요.';
  }
  const kinds = [/[A-Z]/, /[a-z]/, /[0-9]/, /[^A-Za-z0-9]/].filter((rule) =>
    rule.test(value),
  ).length;
  if (kinds < 2) {
    return '영문 대문자·소문자·숫자·특수문자 중 2종류 이상을 섞어 주세요.';
  }
  return '';
}

export function checkRecordFields(fields) {
  const values = [fields.did, fields.stuck, fields.next_step];
  if (values.every((value) => value.trim() === '')) {
    return '세 칸 중 한 칸 이상 입력해 주세요.';
  }
  return '';
}
