import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { defineConfig } from 'vite'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// 개발 서버에서만: 검수 페이지(docs/review/review.html)를 http://localhost:5173/review.html 로 연다.
// 파일을 더블클릭해도 .html 기본 프로그램이 브라우저가 아닌 PC가 있어서 만들었다. 빌드(배포)에는 들어가지 않는다.
const here = path.dirname(fileURLToPath(import.meta.url))
const REVIEW_PAGE = ['/review/review.html', path.resolve(here, '../docs/review/review.html')] // 앞은 docker compose 에서 연결한 경로
const reviewPage = {
  name: 'avly-review-page',
  configureServer(server) {
    server.middlewares.use('/review.html', (req, res, next) => {
      const file = REVIEW_PAGE.find((p) => fs.existsSync(p))
      if (!file) return next()
      res.setHeader('Content-Type', 'text/html; charset=utf-8')
      res.end(fs.readFileSync(file))
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
