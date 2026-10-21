import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { defineConfig } from 'vite'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// 개발 서버에서만: 검수 페이지(docs/review/review.html)를 http://localhost:5173/review.html 로 연다.
// 파일을 더블클릭해도 .html 기본 프로그램이 브라우저가 아닌 PC가 있어서 만들었다. 빌드(배포)에는 들어가지 않는다.
const here = path.dirname(fileURLToPath(import.meta.url))
// 앞은 docker compose 에서 연결한 경로, 뒤는 저장소 안의 경로
const REVIEW_PAGES = {
  '/review.html': ['/review/review.html', path.resolve(here, '../docs/review/review.html')],
  '/label-review.html': ['/review/label-review.html', path.resolve(here, '../docs/review/label-review.html')],
}
const reviewPage = {
  name: 'avly-review-page',
  configureServer(server) {
    Object.entries(REVIEW_PAGES).forEach(([route, candidates]) => {
      server.middlewares.use(route, (req, res, next) => {
        const file = candidates.find((p) => fs.existsSync(p) && fs.statSync(p).isFile())
        if (!file) return next()
        res.setHeader('Content-Type', 'text/html; charset=utf-8')
        res.end(fs.readFileSync(file))
      })
    })
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    reviewPage,
    babel({ presets: [reactCompilerPreset()] })
  ],
})
