import { FormEvent, useEffect, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock,
  Database,
  FileText,
  FolderOpen,
  Layers,
  MessageCircle,
  RefreshCw,
  Search,
  ShieldAlert,
  Upload,
  UploadCloud,
} from "lucide-react";
import { api } from "../api";
import { DocumentRecord, IngestionJob } from "../types";
import { Metric, PanelTitle, StatusBadge, EmptyState } from "./Common";

export function Admin() {
  const [tab, setTab] = useState("dashboard");

  return (
    <section className="workspace admin-workspace">
      <header className="page-hero admin-header">
        <div className="hero-copy">
          <p className="eyebrow">Admin web</p>
          <h1>Quản trị dữ liệu và chất lượng chatbot</h1>
          <p>
            Theo dõi corpus pháp luật, trạng thái ingest và tín hiệu chất lượng câu trả lời trong
            một bảng điều hành gọn, rõ, dễ kiểm soát.
          </p>
        </div>
        <div className="hero-card compact" aria-hidden="true">
          <div className="hero-card-icon">
            <BarChart3 size={24} />
          </div>
          <strong>Operations</strong>
          <span>Corpus health and ingestion control</span>
        </div>
      </header>

      <div className="tabs" role="tablist" aria-label="Admin sections">
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
      <Metric
        label="Tài liệu"
        value={stats.documents}
        helper="Tổng văn bản trong corpus"
        icon={<FolderOpen size={20} />}
      />
      <Metric label="Chunks" value={stats.chunks} helper="Đơn vị đã lập chỉ mục" icon={<Layers size={20} />} />
      <Metric
        label="Job lỗi"
        value={stats.failed}
        tone={stats.failed ? "bad" : "ok"}
        helper="Cần kiểm tra ingest"
        icon={stats.failed ? <AlertTriangle size={20} /> : <CheckCircle2 size={20} />}
      />
      <Metric
        label="Đang xử lý"
        value={stats.processing}
        helper="Job ingest chưa hoàn tất"
        icon={<Clock size={20} />}
      />
      <Metric label="Câu hỏi" value={stats.logs} helper="Lượt truy vấn RAG" icon={<MessageCircle size={20} />} />
      <Metric
        label="Low confidence"
        value={stats.low}
        tone={stats.low ? "warn" : "ok"}
        helper="Câu trả lời cần thận trọng"
        icon={<ShieldAlert size={20} />}
      />
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
      <form className="tool-panel upload-panel" onSubmit={uploadAndIngest}>
        <div className="panel-heading">
          <span className="panel-icon" aria-hidden="true">
            <UploadCloud size={20} />
          </span>
          <div>
            <span className="section-kicker">Ingestion</span>
            <h2>Nạp tài liệu</h2>
          </div>
        </div>

        <label className="upload-dropzone" htmlFor="pdf-upload">
          <UploadCloud size={28} />
          <strong>{file ? file.name : "Chọn tài liệu PDF"}</strong>
          <span>PDF only · hệ thống sẽ tạo job ingest sau khi upload</span>
          <input
            id="pdf-upload"
            accept="application/pdf"
            type="file"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
        </label>

        <label htmlFor="document-domain">
          Lĩnh vực
          <input
            id="document-domain"
            placeholder="Ví dụ: hình sự, thuế, doanh nghiệp..."
            value={domain}
            onChange={(event) => setDomain(event.target.value)}
          />
          <span className="form-helper">Để trống sẽ dùng nhóm mặc định: general.</span>
        </label>

        <button className="primary">
          <Upload size={18} /> Ingest
        </button>
        {status && (
          <div className="notice alert-card">
            <Database size={18} />
            <span>{status}</span>
          </div>
        )}
      </form>

      <div className="table-panel documents-panel">
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
    <div className="table-stack">
      <div className="table-toolbar">
        <label className="search-field" htmlFor="document-search">
          <Search size={17} />
          <input
            id="document-search"
            type="text"
            placeholder="Tìm kiếm tài liệu (tên, lĩnh vực)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </label>
        <span className="result-count">{filtered.length} kết quả</span>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Domain</th>
              <th>Status</th>
              <th>Chunks</th>
              <th className="center-cell">Enabled</th>
            </tr>
          </thead>
          <tbody>
            {displayed.map((document) => (
              <tr key={document.document_id}>
                <td>
                  <strong className="table-title">{document.title}</strong>
                </td>
                <td>{document.domain}</td>
                <td>
                  <StatusBadge status={document.ingestion_status} />
                </td>
                <td>{document.chunks_count}</td>
                <td className="center-cell">
                  <input
                    className="toggle-checkbox"
                    type="checkbox"
                    checked={document.enabled}
                    onChange={() => toggle(document.document_id, document.enabled)}
                    aria-label={`Toggle ${document.title}`}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination-bar">
          <button className="ghost compact" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
            Trước
          </button>
          <span>
            Trang {page} / {totalPages}
          </span>
          <button className="ghost compact" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>
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
    <div className="table-panel jobs-panel">
      <PanelTitle title="Ingestion Jobs" />
      {jobs.length === 0 ? (
        <EmptyState text="Chưa có job ingest." />
      ) : (
        <div className="table-scroll">
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
                  <td>
                    <code className="table-code">{job.task_id}</code>
                  </td>
                  <td>
                    <code className="table-code">{job.document_id}</code>
                  </td>
                  <td>
                    <StatusBadge status={job.status} />
                  </td>
                  <td>{job.chunks_indexed}</td>
                  <td className="job-message">{job.error || job.message}</td>
                  <td>
                    <button className="ghost compact" onClick={() => retry(job.task_id)}>
                      <RefreshCw size={16} /> Retry
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
