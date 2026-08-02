const API = "http://127.0.0.1:9998/api/v1";

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
  tavily_secret_saved: boolean;
  gmail_client_id_saved: boolean;
  gmail_client_secret_saved: boolean;
  outlook_client_id_saved: boolean;
  outlook_client_secret_saved: boolean;
};

export type MailAccount = {
  account_id: string;
  adapter: "imap163" | "gmail" | "outlook";
  email: string;
  enabled: boolean;
  credential_saved: boolean;
  created_at: string;
  updated_at: string;
};

export type OAuthConnection = {
  account_id: string;
  provider: "gmail" | "outlook";
  email: string;
  status: string;
  scopes: string[];
  token_saved: boolean;
  token_expires_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type Reminder = {
  reminder_id: string;
  application_id: string;
  company: string;
  role: string;
  title: string;
  due_at: string;
  status: "scheduled" | "dismissed";
  created_at: string;
  updated_at: string;
};

export type NotificationItem = {
  notification_id: string;
  reminder_id: string;
  application_id: string;
  company: string;
  role: string;
  title: string;
  due_at: string;
  kind: "upcoming" | "urgent" | "overdue";
  status: "unread" | "read";
  created_at: string;
  read_at: string | null;
};

export type PrefillSession = {
  session_id: string;
  application_id: string;
  company: string;
  role: string;
  target_origin: string;
  field_values: Record<string, string>;
  diff: Array<{
    field_key: string;
    label: string;
    current_value: string;
    next_value: string;
  }>;
  status: "draft" | "blocked_captcha" | "handed_off";
  captcha_required: boolean;
  final_submit_allowed: false;
  created_at: string;
  updated_at: string;
};

export type MailSample = {
  sample_id: string;
  subject: string;
  sender: string;
  sent_at: string | null;
  size: number;
  uploaded_at: string;
};

export type Attachment = {
  attachment_id: string;
  application_id: string | null;
  filename: string;
  content_type: string;
  size: number | null;
  allowed: boolean;
  status: "pending" | "stored" | "rejected" | "failed";
  rejection_reason: string | null;
  download_url: string | null;
  created_at: string;
  updated_at: string;
};

export type ResumeVersion = {
  version_id: string;
  resume_id: string;
  version: number;
  label: string;
  filename: string;
  content_type: string;
  size: number;
  content_hash: string;
  application_ids: string[];
  download_url: string;
  created_at: string;
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

export type JDItem = {
  item_id: string;
  category: "responsibility" | "required" | "preferred" | "benefit" | "process" | "other";
  statement: string;
  evidence_quote: string;
  locator: string;
};

export type JDVersion = {
  jd_version_id: string;
  application_id: string;
  version: number;
  source_type: "manual" | "url";
  source_url: string | null;
  source_title: string | null;
  raw_text: string;
  content_hash: string;
  structure: { items: JDItem[]; unknowns: string[] } | null;
  created_at: string;
  updated_at: string;
};

export type CompanyResearch = {
  research_id: string;
  application_id: string;
  version: number;
  created_at: string;
  content: {
    sources: Array<{ url: string; title: string; fetched_at: string }>;
    claims: Array<{
      claim_id: string;
      topic: string;
      statement: string;
      source_url: string;
      evidence_quote: string;
      locator: string;
    }>;
    unknowns: string[];
  };
};

export type EvidenceMap = {
  map_id: string;
  application_id: string;
  jd_version_id: string;
  resume_version_id: string;
  version: number;
  created_at: string;
  content: {
    mappings: Array<{
      jd_item_id: string;
      status: "matched" | "partial" | "missing" | "unknown";
      rationale: string;
      resume_evidence: Array<{ quote: string; locator: string }>;
    }>;
  };
};

export type Gap = {
  jd_item_id: string;
  status: "partial" | "missing" | "unknown";
  statement: string;
  finding: string;
  review_question: string;
};

export type Review = {
  review_id: string;
  application_id: string;
  artifact_type: "jd" | "research" | "evidence_map";
  artifact_id: string;
  item_id: string;
  decision: "confirmed" | "needs_revision" | "rejected";
  note: string | null;
  created_at: string;
};

export type AgentLimits = {
  max_steps: number;
  max_model_calls: number;
  max_tool_calls: number;
  max_write_approvals: number;
  max_elapsed_seconds: number;
};

export type AgentFact = {
  statement: string;
  source_id: string;
  locator: string;
};

export type AgentToolCall = {
  tool_call_id: string;
  sequence: number;
  tool_name: string;
  risk_level: "read" | "write_approval";
  status: string;
  reason: string;
  arguments: Record<string, unknown>;
  result_refs: string[];
  result_summary_safe: string | null;
  error_code: string | null;
  created_at: string;
  finished_at: string | null;
};

export type AgentApproval = {
  approval_id: string;
  tool_call_id: string;
  status: "pending" | "approved" | "rejected" | "expired";
  request_summary: string;
  application_version: number;
  decision_note: string | null;
  requested_at: string;
  decided_at: string | null;
};

export type AgentRun = {
  run_id: string;
  application_id: string;
  request_text: string;
  model_name: string;
  status: string;
  current_step: string | null;
  limits: AgentLimits;
  usage: {
    steps: number;
    model_calls: number;
    tool_calls: number;
    write_approvals: number;
    elapsed_ms: number;
  };
  final_output: {
    action: "final";
    summary: string;
    facts: AgentFact[];
    unknowns: string[];
    next_questions: string[];
  } | null;
  error_code: string | null;
  error_message_safe: string | null;
  tool_calls: AgentToolCall[];
  approvals: AgentApproval[];
  created_at: string;
  finished_at: string | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.code ?? `请求失败 (${response.status})`);
  }
  return response.json() as Promise<T>;
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
  mailAccounts: () => request<MailAccount[]>("/mail-accounts"),
  oauthConnections: () => request<OAuthConnection[]>("/oauth-connections"),
  startOAuth: (provider: "gmail" | "outlook", accountId: string, email: string) =>
    request<{ authorization_url: string; connection: OAuthConnection }>(
      `/oauth/${provider}/start`,
      {
        method: "POST",
        body: JSON.stringify({ account_id: accountId, email }),
      },
    ),
  disconnectOAuth: (accountId: string) =>
    request<OAuthConnection>(
      `/oauth-connections/${encodeURIComponent(accountId)}/disconnect`,
      { method: "POST" },
    ),
  reminders: () => request<Reminder[]>("/reminders"),
  createReminder: (applicationId: string, title: string, dueAt: string) =>
    request<Reminder>("/reminders", {
      method: "POST",
      body: JSON.stringify({
        application_id: applicationId,
        title,
        due_at: dueAt,
        idempotency_key: crypto.randomUUID(),
      }),
    }),
  dismissReminder: (id: string) =>
    request<Reminder>(`/reminders/${encodeURIComponent(id)}/dismiss`, {
      method: "POST",
    }),
  reminderIcsUrl: () => `${API}/reminders.ics`,
  notifications: () => request<NotificationItem[]>("/notifications"),
  scanNotifications: () =>
    request<NotificationItem[]>("/notifications/scan", { method: "POST" }),
  readNotification: (id: string) =>
    request<NotificationItem>(`/notifications/${encodeURIComponent(id)}/read`, {
      method: "POST",
    }),
  createPrefillSession: (
    applicationId: string,
    targetUrl: string,
    profile: Record<string, string>,
  ) =>
    request<PrefillSession>("/prefill-sessions", {
      method: "POST",
      body: JSON.stringify({
        application_id: applicationId,
        target_url: targetUrl,
        profile,
        idempotency_key: crypto.randomUUID(),
      }),
    }),
  mailSamples: () => request<MailSample[]>("/mail-samples"),
  attachments: (applicationId?: string) =>
    request<Attachment[]>(
      `/attachments${applicationId ? `?application_id=${encodeURIComponent(applicationId)}` : ""}`,
    ),
  approveAttachment: (id: string) =>
    request<Attachment>(`/attachments/${encodeURIComponent(id)}/approve`, {
      method: "POST",
    }),
  jdVersions: (id: string) => request<JDVersion[]>(`/applications/${id}/jd-versions`),
  createJD: (id: string, value: { raw_text?: string; source_url?: string }) =>
    request<JDVersion>(`/applications/${id}/jd-versions`, {
      method: "POST",
      body: JSON.stringify({ ...value, idempotency_key: crypto.randomUUID() }),
    }),
  structureJD: (id: string) =>
    request<{ job_id: string; jd: JDVersion }>(`/jd-versions/${id}/structure-jobs`, {
      method: "POST",
      body: JSON.stringify({
        idempotency_key: crypto.randomUUID(),
        data_leaving_confirmed: true,
      }),
    }),
  companyResearch: (id: string) =>
    request<CompanyResearch[]>(`/applications/${id}/company-research`),
  generateCompanyResearch: (id: string) =>
    request<{ job_id: string; research: CompanyResearch }>(
      `/applications/${id}/company-research-jobs`,
      {
        method: "POST",
        body: JSON.stringify({
          idempotency_key: crypto.randomUUID(),
          data_leaving_confirmed: true,
        }),
      },
    ),
  evidenceMaps: (id: string) => request<EvidenceMap[]>(`/applications/${id}/evidence-maps`),
  generateEvidenceMap: (id: string, jdVersionId: string, resumeVersionId: string) =>
    request<{ job_id: string; evidence_map: EvidenceMap }>(
      `/applications/${id}/evidence-map-jobs`,
      {
        method: "POST",
        body: JSON.stringify({
          jd_version_id: jdVersionId,
          resume_version_id: resumeVersionId,
          idempotency_key: crypto.randomUUID(),
          data_leaving_confirmed: true,
        }),
      },
    ),
  gaps: (mapId: string) =>
    request<{ map_id: string; gaps: Gap[] }>(`/evidence-maps/${mapId}/gaps`),
  reviews: (id: string) => request<Review[]>(`/applications/${id}/reviews`),
  createReview: (
    id: string,
    body: Omit<Review, "review_id" | "application_id" | "created_at">,
  ) =>
    request<Review>(`/applications/${id}/reviews`, {
      method: "POST",
      body: JSON.stringify({ ...body, idempotency_key: crypto.randomUUID() }),
    }),
  agentRuns: (id: string) => request<AgentRun[]>(`/applications/${id}/agent-runs`),
  agentRun: (runId: string) => request<AgentRun>(`/agent-runs/${runId}`),
  createAgentRun: (
    id: string,
    requestText: string,
    limits: AgentLimits,
  ) =>
    request<AgentRun>(`/applications/${id}/agent-runs`, {
      method: "POST",
      body: JSON.stringify({
        request_text: requestText,
        idempotency_key: crypto.randomUUID(),
        data_leaving_confirmed: true,
        limits,
      }),
    }),
  decideAgentApproval: (
    runId: string,
    approvalId: string,
    decision: "approved" | "rejected",
  ) =>
    request<AgentRun>(`/agent-runs/${runId}/approvals/${approvalId}`, {
      method: "POST",
      body: JSON.stringify({ decision, decision_note: null }),
    }),
  resumeAgentRun: (runId: string) =>
    request<AgentRun>(`/agent-runs/${runId}/resume`, { method: "POST" }),
  cancelAgentRun: (runId: string) =>
    request<AgentRun>(`/agent-runs/${runId}/cancel`, { method: "POST" }),
  resumes: () => request<ResumeVersion[]>("/resumes"),
  uploadResume: (
    file: File,
    label: string,
    resumeId?: string,
    applicationId?: string,
  ) => {
    const query = new URLSearchParams({ filename: file.name, label });
    if (resumeId) query.set("resume_id", resumeId);
    if (applicationId) query.set("application_id", applicationId);
    return request<ResumeVersion>(`/resumes?${query}`, {
      method: "POST",
      headers: { "Content-Type": file.type || "application/octet-stream" },
      body: file,
    });
  },
  linkResume: (versionId: string, applicationId: string) =>
    request<ResumeVersion>(
      `/resume-versions/${encodeURIComponent(versionId)}/applications/${encodeURIComponent(applicationId)}`,
      { method: "PUT" },
    ),
  contentUrl: (path: string) => new URL(path, API).toString(),
  importMailSample: (file: File, trackerPath: string) => {
    const query = new URLSearchParams({
      filename: file.name,
      tracker_path: trackerPath,
      idempotency_key: crypto.randomUUID(),
    });
    return request<MailSample & { stored: boolean; job_id: string; processed: number }>(
      `/mail-samples/import-jobs?${query}`,
      { method: "POST", headers: { "Content-Type": "message/rfc822" }, body: file },
    );
  },
  saveMailAccount: (id: string, body: Record<string, unknown>) =>
    request<MailAccount>(`/mail-accounts/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  setMailAccountEnabled: (id: string, enabled: boolean) =>
    request<MailAccount>(`/mail-accounts/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),
  testRegisteredMail: (id: string) =>
    request<{ status: string }>(`/mail-accounts/${encodeURIComponent(id)}/test`, {
      method: "POST",
    }),
  syncRegisteredMail: (id: string, body: Record<string, unknown>) =>
    request<{ job_id: string; processed: number }>(
      `/mail-accounts/${encodeURIComponent(id)}/sync-jobs`,
      {
        method: "POST",
        body: JSON.stringify({ ...body, idempotency_key: crypto.randomUUID() }),
      },
    ),
  testMail: (body: Record<string, unknown>) =>
    request<{ status: string }>("/mail-accounts/test", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  syncMail: (body: Record<string, unknown>) =>
    request<{ job_id: string; processed: number }>("/mail-sync-jobs", {
      method: "POST",
      body: JSON.stringify({ ...body, idempotency_key: crypto.randomUUID() }),
    }),
  syncExcel: (path: string, direction: "import" | "export") =>
    request<{ job_id: string }>("/excel-sync-jobs", {
      method: "POST",
      body: JSON.stringify({ path, direction, idempotency_key: crypto.randomUUID() }),
    }),
};
