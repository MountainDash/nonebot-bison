import packageJson from '@/../package.json'

const apiBase = packageJson.config.apiUrl

export function api(strings: TemplateStringsArray, ...values: unknown[]): string {
  let result = ''
  strings.forEach((str, i) => {
    result += str + (values[i] || '')
  })
  return `${apiBase}${result}`
}

export async function fetchApi<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const res = await fetch(input, init)
  if (!res.ok) {
    throw new Error(res.statusText)
  }
  return res.json()
}
