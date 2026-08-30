export type Route = '/login' | '/register' | '/profile' | '/pool' | '/generate' | '/archive' | '/account'
export type PoolType = 'experience' | 'project' | 'skill' | 'education'
export type PoolSource = 'pdf' | 'github' | 'manual'
export type TypeFilter = 'all' | PoolType

export type User = {
  id: string
  email: string
  kvkk_consent_at: string
}

export type LLMCredential = {
  provider: string
  model: string
  key_hint: string
  updated_at: string
}

export type KVKKNotice = {
  version: string
  title: string
  explicit_consent_text: string
  sections: Array<{ title: string; body: string }>
}

export type Profile = {
  id: string
  full_name: string
  contact: { email?: string; phone?: string; location?: string } | null
  education: Array<{ school?: string; degree?: string }>
  personal_info: { summary?: string } | null
}

export type ProfileForm = {
  fullName: string
  email: string
  phone: string
  location: string
  school: string
  degree: string
  summary: string
}

export type PoolItem = {
  id: string
  user_id: string
  source: PoolSource
  type: PoolType
  title: string | null
  raw_content: string
  tags: string[]
  technologies: string[]
  language: 'tr' | 'en' | 'mixed'
  verified_by_user: boolean
  created_at: string
  embedding_dimensions: number
}

export type PoolForm = {
  type: PoolType
  title: string
  rawContent: string
  tags: string
  technologies: string
}

export type PDFImportResponse = {
  imported_count: number
  items: PoolItem[]
  profile: Profile | null
}

export type JobInputMode = 'text' | 'url'
export type PipelineStepName = 'job_parser' | 'selector' | 'cvtailor' | 'evaluator' | 'typst_renderer'

export type PipelineStep = {
  name: PipelineStepName
  status: 'pending' | 'running' | 'completed' | 'failed'
}

export type BeforeAfterDiff = {
  source_pool_item_id: string
  title: string | null
  before: string
  after: string
  diff: string
}

export type CVGenerationStatus = {
  pipeline_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  current_step: PipelineStepName | null
  steps: PipelineStep[]
  job_id: string | null
  generated_cv_id: string | null
  selected_pool_item_ids: string[]
  output_language: 'tr' | 'en' | 'mixed' | null
  job_summary: string | null
  ats_score: number | null
  missing_keywords: string[]
  ats_recommendations: string[]
  before_after_diff: BeforeAfterDiff[]
  tailoring_fell_back: boolean
  error: string | null
}

export type Job = {
  id: string
  source_url: string | null
  raw_text: string
  parsed_requirements_json: { summary?: string } | null
  created_at: string
}

export type GeneratedCV = {
  id: string
  job_id: string
  output_language: 'tr' | 'en' | 'mixed'
  pdf_path: string | null
  ats_score: number | null
  created_at: string | null
}

export type GithubCallback = { status: 'connected'; username: string } | { status: 'error'; reason: string | null }
