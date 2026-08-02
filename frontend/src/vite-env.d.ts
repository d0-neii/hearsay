/// <reference types="vite/client" />
/// <reference types="vite-plugin-svgr/client" />

interface ImportMetaEnv {
  /**
   * 백엔드 API 주소. 배포 환경에서만 설정한다.
   * 비어 있으면 '/api'로 요청해 vite dev server의 proxy를 탄다.
   * 예) https://hearsay-api.example.com
   */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
