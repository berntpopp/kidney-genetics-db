export interface JsonApiResponse<T> {
  data: T
  meta?: JsonApiMeta
  links?: JsonApiLinks
}

export interface JsonApiListResponse<T> {
  data: T[]
  meta?: JsonApiMeta
  links?: JsonApiLinks
}

export interface JsonApiMeta {
  total?: number
  page?: number
  per_page?: number
  total_pages?: number
  [key: string]: unknown
}

export interface JsonApiLinks {
  self?: string
  first?: string
  last?: string
  prev?: string | null
  next?: string | null
}

export interface JsonApiError {
  status: number
  title: string
  detail?: string
  source?: { pointer?: string; parameter?: string }
}

export interface ApiErrorResponse {
  errors: JsonApiError[]
}
