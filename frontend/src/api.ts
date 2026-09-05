const API = "http://127.0.0.1:9998/api/v1";

export type UnresolvedMail = { email_id: string; subject: string; sender: string; facts: Record<string, string> };

export type JDReport = {
  job_id: string;
  jd: string;
  source_hash: string;
  model: string;
  prompt_version: string;
  analysis: {
    requirements: Array<{ text: string; quote: string; importance: string; origin: string; reason: string }>;
    unknowns: string[];
  };
};

export type Application = {
  application_id: string;
  company: string;
  role: string;
  values: Record<string, unknown>;
  version: number;
};

export type ApplicationDetail = Application & {
  timeline: Array<{ event_type: string; payload: Record<string, unknown>; created_at: string }>;
  provenance: Array<{
    field: string;
    value: unknown;
    source: string;
    evidence: string | null;
    created_at: string;
  }>;
  emails: Array<{
    subject: string;
    sender: string;
    sent_at: string | null;
    evidence: Record<string, unknown>;
  }>;
};

export type Job = {
  job_id: string;
  job_type: string;
  status: string;
  current_step: string | null;
  checkpoint: Record<string, unknown> | null;
  error_code: string | null;
  error_message_safe: string | null;
  retryable: boolean;
};

export type Settings = {
  account_id: string;
  email: string;
  tracker_path: string;
  markdown_path: string;
  model_base_url: string;
  model_name: string;
  scheduling_enabled: boolean;
  mail_secret_saved: boolean;
  model_secret_saved: boolean;
  brave_secret_saved: boolean;
};

export type SummarySource = {
  url: string;
  title: string;
  fetched_at: string;
};

export type Summary = {
  summary_id: string;
  application_id: string;
  version: number;
  created_at: string;
  content: {
    overview: string;
    jd_highlights: string[];
    process_clues: string[];
    written_test: string[];
    interview: string[];
    known_facts: string[];
    unknowns: string[];
    sources: SummarySource[];
  };
};

export type ResumeVersion = {
  version_id: string;
  resume_id: string;
  version: number;
  label: string;
  filename: string;
  content_type: string;
  size: number;
  application_ids: string[];
  download_url: string;
  created_at: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message ?? detail?.code ?? `请求失败 (${response.status})`);
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}

export const api = {
  applications: () => request<Application[]>("/applications"),
  application: (id: string) => request<ApplicationDetail>(`/applications/${id}`),
  createApplication: (company: string, role: string) =>
    request<Application>("/applications", {
      method: "POST",
      body: JSON.stringify({ company, role, idempotency_key: crypto.randomUUID() }),
    }),
  updateApplication: (
    id: string,
    changes: Record<string, unknown>,
    expected_version: number,
  ) =>
    request<Application>(`/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify({
        changes,
        expected_version,
        idempotency_key: crypto.randomUUID(),
      }),
    }),
  unresolvedMails: () => request<UnresolvedMail[]>("/unresolved-mails"),
  associateMail: (emailId: string, applicationId: string) => request(`/unresolved-mails/${emailId}/association`, {
    method: "POST", body: JSON.stringify({ application_id: applicationId }),
  }),
  jdAnalyses: (id: string) => request<JDReport[]>(`/applications/${id}/jd-analyses`),
  analyzeJD: (id: string, jd: string) => request<JDReport>(`/applications/${id}/jd-analyses`, {
    method: "POST", body: JSON.stringify({ jd, data_leaving_confirmed: true }),
  }),
  summaries: (id: string) => request<Summary[]>(`/applications/${id}/summaries`),
  generateSummary: (id: string) =>
    request<{ job_id: string; summary: Summary }>(`/applications/${id}/summary-jobs`, {
      method: "POST",
      body: JSON.stringify({
        idempotency_key: crypto.randomUUID(),
        data_leaving_confirmed: true,
      }),
    }),
  markdownUrl: (id: string) => `${API}/applications/${id}/markdown`,
  jobs: () => request<Job[]>("/jobs"),
  resumeJob: (id: string) =>
    request<{ job_id: string; processed: number }>(`/jobs/${id}/resume`, { method: "POST" }),
  settings: () => request<Settings>("/settings"),
  saveSettings: (body: Record<string, unknown>) =>
    request<Settings>("/settings", { method: "PUT", body: JSON.stringify(body) }),
  testMail: (body: Record<string, unknown>) =>
    request<{ status: string }>("/mail-accounts/test", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  syncMail: (body: Record<string, unknown>) =>
    request<{ job_id: string; processed: number; new_emails: number; created: number; updated: number; unchanged: number; unlinked: number; conflicts: number }>("/mail-sync-jobs", {
      method: "POST",
      body: JSON.stringify({ ...body, idempotency_key: crypto.randomUUID() }),
    }),
  syncExcel: (path: string, direction: "import" | "export") =>
    request<{ job_id: string; created?: number; updated?: number; deleted?: number; resume_mapped?: number }>("/excel-sync-jobs", {
      method: "POST",
      body: JSON.stringify({ path, direction, destructive_confirmed: direction === "import", idempotency_key: crypto.randomUUID() }),
    }),
  resumes: () => request<ResumeVersion[]>("/resumes"),
  uploadResume: (file: File, label: string, resumeId?: string) =>
    request<ResumeVersion>(`/resumes?filename=${encodeURIComponent(file.name)}&label=${encodeURIComponent(label)}${resumeId ? `&resume_id=${resumeId}` : ""}`, {
      method: "POST",
      headers: { "Content-Type": file.type || "application/octet-stream" },
      body: file,
    }),
  setApplicationResume: (applicationId: string, versionId: string) =>
    request<ResumeVersion>(`/applications/${applicationId}/resume/${versionId}`, { method: "PUT" }),
  deleteResume: (resumeId: string) =>
    request<void>(`/resumes/${resumeId}?confirmed=true`, { method: "DELETE" }),
  resumeDownloadUrl: (versionId: string) => `${API}/resume-versions/${versionId}/content`,
};
