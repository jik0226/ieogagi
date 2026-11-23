import js from '@eslint/js';
import globals from 'globals';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import security from 'eslint-plugin-security';

export default [
  { ignores: ['dist/'] },
  js.configs.recommended,
  react.configs.flat.recommended,
  react.configs.flat['jsx-runtime'],
  reactHooks.configs.flat.recommended,
  security.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    settings: { react: { version: 'detect' } },
    rules: {
      // Security rules that the contest static analysis also looks for.
      'react/no-danger': 'error',
      'react/jsx-no-target-blank': 'error',
      'react/jsx-no-script-url': 'error',
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',
      'no-script-url': 'error',
      'no-console': 'error',
      'no-alert': 'error',
      'no-debugger': 'error',
      'no-warning-comments': ['error', { terms: ['todo', 'fixme', 'xxx', 'hack'], location: 'start' }],
      'react/iframe-missing-sandbox': 'error',
      'react/no-invalid-html-attribute': 'error',
      // The session lives only in an HttpOnly cookie; nothing goes to browser storage.
      'no-restricted-globals': [
        'error',
        { name: 'localStorage', message: '중요정보를 브라우저 저장소에 두지 않습니다 (세션은 HttpOnly 쿠키).' },
        { name: 'sessionStorage', message: '중요정보를 브라우저 저장소에 두지 않습니다 (세션은 HttpOnly 쿠키).' },
        { name: 'indexedDB', message: '중요정보를 브라우저 저장소에 두지 않습니다 (세션은 HttpOnly 쿠키).' },
      ],
      'no-restricted-properties': [
        'error',
        { object: 'Math', property: 'random', message: '보안 용도의 난수는 crypto.getRandomValues()를 씁니다.' },
        { object: 'document', property: 'cookie', message: '쿠키는 서버가 HttpOnly로만 다룹니다.' },
        { object: 'document', property: 'write', message: 'DOM에 HTML 문자열을 쓰지 않습니다 (XSS).' },
        { object: 'document', property: 'writeln', message: 'DOM에 HTML 문자열을 쓰지 않습니다 (XSS).' },
        { object: 'window', property: 'localStorage', message: '중요정보를 브라우저 저장소에 두지 않습니다.' },
        { object: 'window', property: 'sessionStorage', message: '중요정보를 브라우저 저장소에 두지 않습니다.' },
      ],
      'no-restricted-syntax': [
        'error',
        {
          selector: 'AssignmentExpression[left.property.name=/^(innerHTML|outerHTML)$/]',
          message: 'innerHTML/outerHTML 대입 대신 React 렌더링(텍스트로 출력)을 씁니다 (XSS).',
        },
        {
          selector: "CallExpression[callee.property.name='insertAdjacentHTML']",
          message: 'insertAdjacentHTML 대신 React 렌더링을 씁니다 (XSS).',
        },
        {
          selector: 'CallExpression[callee.name=/^(setTimeout|setInterval)$/][arguments.0.type=/^(Literal|TemplateLiteral)$/]',
          message: '타이머에 문자열 코드를 넘기지 않습니다 (코드 삽입).',
        },
        // Built-in no-empty ignores a catch block that holds only a comment; the contest
        // analyzer (diagnosis 04.02) does not, so an empty body is rejected here.
        {
          selector: 'CatchClause[body.body.length=0]',
          message: '빈 catch 블록 금지 (오류 상황 대응 부재): 사용자에게 고정 문구로 알리거나 대체 동작을 둡니다.',
        },
        {
          selector: "CallExpression[callee.property.name='catch'] > :function[body.type='BlockStatement'][body.body.length=0]",
          message: '빈 .catch 처리기 금지 (오류 상황 대응 부재): 오류를 삼키지 않습니다.',
        },
      ],
      // The project is plain JavaScript, so prop-types are not declared.
      'react/prop-types': 'off',
    },
  },
  {
    files: ['vite.config.js', 'eslint.config.js'],
    languageOptions: { globals: globals.node },
  },
];
