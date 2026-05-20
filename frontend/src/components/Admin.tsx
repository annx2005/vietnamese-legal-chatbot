import { FormEvent, useEffect, useState } from "react";
import { BarChart3, FileText, RefreshCw, Upload } from "lucide-react";
import { api } from "../api";
import { DocumentRecord, IngestionJob } from "../types";
import { Metric, PanelTitle, StatusBadge, EmptyState } from "./Common";

export function Admin() {
  const [tab, setTab] = useState("dashboard");

  return (
    <section className="workspace">
      <header className="page-header">
        <div>
          <p className="eyebrow">Admin web</p>
          <h1>Quản trị dữ liệu và chất lượng chatbot</h1>
        </div>
      </header>
      <div className="tabs">
        <button
          className={tab === "dashboard" ? "tab active" : "tab"}
          onClick={() => setTab("dashboard")}
        >
          <BarChart3 size={16} /> Dashboard
        </button>
        <button
          className={tab === "documents" ? "tab active" : "tab"}
          onClick={() => setTab("documents")}
        >
          <FileText size={16} /> Documents
        </button>
        <button className={tab === "jobs" ? "tab active" : "tab"} onClick={() => setTab("jobs")}>
          <RefreshCw size={16} /> Jobs
        </button>
      </div>
      {tab === "dashboard" && <Dashboard />}
      {tab === "documents" && <Documents />}
      {tab === "jobs" && <Jobs />}
    </section>
  );
}

function Dashboard() {
  const [stats, setStats] = useState({
    documents: 0,
    chunks: 0,
    failed: 0,
    processing: 0,
    logs: 0,
    low: 0,
    reviewed: 0
  });

  useEffect(() => {
    Promise.allSettled([api.ingestStats(), api.ragStats()]).then(([ingest, rag]) => {
      setStats({
        documents: ingest.status === "fulfilled" ? ingest.value.documents_total : 0,
        chunks: ingest.status === "fulfilled" ? ingest.value.chunks_total : 0,
        failed: ingest.status === "fulfilled" ? ingest.value.jobs_failed : 0,
        processing: ingest.status === "fulfilled" ? ingest.value.jobs_processing : 0,
        logs: rag.status === "fulfilled" ? rag.value.chat_logs_total : 0,
        low: rag.status === "fulfilled" ? rag.value.low_confidence_total : 0,
        reviewed: rag.status === "fulfilled" ? rag.value.reviewed_total : 0
      });
    });
  }, []);

  return (
    <div className="metrics-grid">
      <Metric label="Tài liệu" value={stats.documents} />
      <Metric label="Chunks" value={stats.chunks} />
      <Metric label="Job lỗi" value={stats.failed} tone={stats.failed ? "bad" : "ok"} />
      <Metric label="Đang xử lý" value={stats.processing} />
      <Metric label="Câu hỏi" value={stats.logs} />
      <Metric label="Low confidence" value={stats.low} tone={stats.low ? "warn" : "ok"} />
    </div>
  );
}

function Documents() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [domain, setDomain] = useState("");
  const [status, setStatus] = useState("");

  async function refresh() {
    const result = await api.documents();
    setDocuments(result.documents);
  }

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  async function uploadAndIngest(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      setStatus("Vui lòng chọn file PDF.");
      return;
    }
    setStatus("Đang gửi tài liệu...");
    try {
      const uploaded = await api.upload(file);
      await api.ingest({
        file_url: uploaded.fileUrl,
        document_id: uploaded.documentId,
        document_type: "PDF",
        metadata: { title: file.name, domain: domain.trim() || "general" }
      });
      setStatus("Đã tạo job ingest.");
      await refresh();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Không ingest được tài liệu");
    }
  }

  return (
    <div className="admin-grid">
      <form className="tool-panel" onSubmit={uploadAndIngest}>
        <h2>Nạp tài liệu</h2>
        <label>
          PDF upload
          <input
            accept="application/pdf"
            type="file"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
        </label>
        <label>
          Lĩnh vực
          <input
            placeholder="Ví dụ: hình sự, thuế, doanh nghiệp..."
            value={domain}
            onChange={(event) => setDomain(event.target.value)}
          />
        </label>
        <button className="primary">
          <Upload size={18} /> Ingest
        </button>
        {status && <div className="notice">{status}</div>}
      </form>
      <div className="table-panel">
        <PanelTitle title="Documents" />
        {documents.length === 0 ? (
          <EmptyState text="Chưa có tài liệu được ingest." />
        ) : (
          <DocumentTable documents={documents} onRefresh={refresh} />
        )}
      </div>
    </div>
  );
}

function DocumentTable({
  documents,
  onRefresh
}: {
  documents: DocumentRecord[];
  onRefresh: () => void;
}) {
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const itemsPerPage = 10;

  useEffect(() => {
    setPage(1);
  }, [searchQuery]);

  const filtered = documents.filter(
    (doc) =>
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.domain.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const totalPages = Math.max(1, Math.ceil(filtered.length / itemsPerPage));
  const displayed = filtered.slice((page - 1) * itemsPerPage, page * itemsPerPage);

  async function toggle(documentId: string, currentlyEnabled: boolean) {
    try {
      if (currentlyEnabled) {
        await api.disableDocument(documentId);
      } else {
        await api.enableDocument(documentId);
      }
      await onRefresh();
    } catch (err) {
      console.error("Failed to toggle document status", err);
    }
  }

  return (
    <div>
      <div style={{ marginBottom: "16px", display: "flex", gap: "12px", alignItems: "center" }}>
        <input
          type="text"
          placeholder="Tìm kiếm tài liệu (tên, lĩnh vực)..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{ maxWidth: "320px", padding: "10px 14px" }}
        />
        <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
          {filtered.length} kết quả
        </span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Title</th>
            <th>Domain</th>
            <th>Status</th>
            <th>Chunks</th>
            <th style={{ textAlign: "center" }}>Enabled</th>
          </tr>
        </thead>
        <tbody>
          {displayed.map((document) => (
            <tr key={document.document_id}>
              <td>{document.title}</td>
              <td>{document.domain}</td>
              <td>
                <StatusBadge status={document.ingestion_status} />
              </td>
              <td>{document.chunks_count}</td>
              <td style={{ textAlign: "center" }}>
                <input
                  type="checkbox"
                  checked={document.enabled}
                  onChange={() => toggle(document.document_id, document.enabled)}
                  style={{ cursor: "pointer", width: "16px", height: "16px" }}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {totalPages > 1 && (
        <div style={{ display: "flex", gap: "12px", marginTop: "20px", justifyContent: "flex-end", alignItems: "center" }}>
          <button 
            className="ghost" 
            disabled={page === 1} 
            onClick={() => setPage(p => p - 1)}
            style={{ padding: "6px 12px", borderRadius: "6px" }}
          >
            Trước
          </button>
          <span style={{ fontSize: "14px", fontWeight: 500, color: "var(--text-secondary)" }}>
            Trang {page} / {totalPages}
          </span>
          <button 
            className="ghost" 
            disabled={page === totalPages} 
            onClick={() => setPage(p => p + 1)}
            style={{ padding: "6px 12px", borderRadius: "6px" }}
          >
            Sau
          </button>
        </div>
      )}
    </div>
  );
}

function Jobs() {
  const [jobs, setJobs] = useState<IngestionJob[]>([]);

  async function refresh() {
    const result = await api.jobs();
    setJobs(result.jobs);
  }

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  async function retry(taskId: string) {
    await api.retry(taskId);
    await refresh();
  }

  return (
    <div className="table-panel">
      <PanelTitle title="Ingestion Jobs" />
      {jobs.length === 0 ? (
        <EmptyState text="Chưa có job ingest." />
      ) : (
        <table>
          <thead>
            <tr>
              <th>Job</th>
              <th>Document</th>
              <th>Status</th>
              <th>Chunks</th>
              <th>Message</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.task_id}>
                <td>{job.task_id}</td>
                <td>{job.document_id}</td>
                <td>
                  <StatusBadge status={job.status} />
                </td>
                <td>{job.chunks_indexed}</td>
                <td>{job.error || job.message}</td>
                <td>
                  <button className="ghost" onClick={() => retry(job.task_id)}>
                    <RefreshCw size={16} /> Retry
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

