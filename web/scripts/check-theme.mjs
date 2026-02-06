import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'

const root = path.resolve('src')
const ignorePaths = new Set([
  path.resolve('src/styles/tokens.css'),
])
const ignoreDirs = new Set([
  path.resolve('src/assets'),
])

const patterns = [
  {
    name: 'tailwind-default-palette',
    regex: /\b(?:bg|text|border|from|to|via|ring|outline|stroke|fill|shadow)-(?:gray|slate|zinc|neutral|stone|red|blue|green|orange|purple|indigo|emerald|amber|cyan|teal|lime|rose|pink|sky)-\d{2,3}(?:\/\d{1,3})?\b/g,
  },
  {
    name: 'tailwind-basic-colors',
    regex: /\b(?:bg|text|border|ring|outline|stroke|fill|shadow)-(?:white|black)(?:\/\d{1,3})?\b/g,
  },
  {
    name: 'hex-colors',
    regex: /#[0-9a-fA-F]{3,8}\b/g,
  },
]

function isIgnored(filePath) {
  if (ignorePaths.has(filePath)) return true
  for (const dir of ignoreDirs) {
    if (filePath.startsWith(dir + path.sep)) return true
  }
  return false
}

async function walk(dir, files = []) {
  const entries = await readdir(dir, { withFileTypes: true })
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      if (ignoreDirs.has(fullPath)) continue
      await walk(fullPath, files)
    } else if (entry.isFile()) {
      if (isIgnored(fullPath)) continue
      if (!fullPath.match(/\.(ts|tsx|css)$/)) continue
      files.push(fullPath)
    }
  }
  return files
}

function findViolations(filePath, content) {
  const violations = []
  const lines = content.split(/\r?\n/)
  lines.forEach((line, index) => {
    for (const pattern of patterns) {
      pattern.regex.lastIndex = 0
      let match
      while ((match = pattern.regex.exec(line)) !== null) {
        violations.push({
          filePath,
          line: index + 1,
          match: match[0],
          rule: pattern.name,
        })
      }
    }
  })
  return violations
}

async function main() {
  const files = await walk(root)
  const violations = []

  for (const filePath of files) {
    const content = await readFile(filePath, 'utf8')
    violations.push(...findViolations(filePath, content))
  }

  if (violations.length > 0) {
    console.error('Theme lint failed. Use design tokens instead of raw colors.')
    for (const v of violations) {
      console.error(`${v.filePath}:${v.line}  ${v.match}  (${v.rule})`)
    }
    process.exit(1)
  }

  console.log('Theme lint passed.')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
