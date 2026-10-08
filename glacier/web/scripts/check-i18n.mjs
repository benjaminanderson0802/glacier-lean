import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'

const base = fileURLToPath(new URL('../', import.meta.url))
const dictionaryDir = join(base, 'src/i18n')
const dictionaryFiles = readdirSync(dictionaryDir).filter(name => /^[a-z]{2}\.ts$/.test(name)).sort()
const findings = []

function readDictionary(fileName) {
  const path = join(dictionaryDir, fileName)
  const source = readFileSync(path, 'utf8')
  const sourceFile = ts.createSourceFile(path, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)
  const exported = sourceFile.statements.find(statement =>
    ts.isVariableStatement(statement) && statement.modifiers?.some(modifier => modifier.kind === ts.SyntaxKind.ExportKeyword))
  const declaration = exported?.declarationList.declarations[0]
  if (!declaration || !ts.isObjectLiteralExpression(declaration.initializer)) {
    findings.push(`${fileName}: expected an exported dictionary object`)
    return {}
  }

  const values = {}
  for (const property of declaration.initializer.properties) {
    if (!ts.isPropertyAssignment(property) || !ts.isStringLiteral(property.name) || !ts.isStringLiteral(property.initializer)) {
      findings.push(`${fileName}: dictionary entries must use string keys and values`)
      continue
    }
    const key = property.name.text
    if (Object.hasOwn(values, key)) findings.push(`${fileName}: duplicate key ${key}`)
    values[key] = property.initializer.text
  }
  return values
}

const dictionaries = Object.fromEntries(dictionaryFiles.map(file => [file, readDictionary(file)]))
const english = dictionaries['en.ts']
if (!english) {
  findings.push('en.ts: English dictionary is required')
} else {
  const placeholders = value => [...value.matchAll(/\{(\w+)\}/g)].map(match => match[1]).sort()
  for (const [file, dictionary] of Object.entries(dictionaries)) {
    if (file === 'en.ts') continue
    for (const key of Object.keys(english)) {
      if (!Object.hasOwn(dictionary, key)) findings.push(`${file}: missing key ${key}`)
      else if (JSON.stringify(placeholders(dictionary[key])) !== JSON.stringify(placeholders(english[key]))) {
        findings.push(`${file}: placeholder mismatch for ${key} (English: ${placeholders(english[key]).join(', ') || 'none'}; translation: ${placeholders(dictionary[key]).join(', ') || 'none'})`)
      }
    }
    for (const key of Object.keys(dictionary)) {
      if (!Object.hasOwn(english, key)) findings.push(`${file}: extra key ${key}`)
    }
  }
}

if (findings.length) {
  console.error(`i18n parity: ${findings.length} finding(s)\n${findings.join('\n')}`)
  process.exitCode = 1
} else {
  console.log(`i18n parity: ${dictionaryFiles.length} dictionaries, ${Object.keys(english).length} keys; keys and placeholders match`)
}
