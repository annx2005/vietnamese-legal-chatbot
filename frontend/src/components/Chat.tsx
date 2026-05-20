import { FormEvent, useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Database,
  FileSearch,
  Link2,
  Loader2,
  Quote,
  Scale,
  Search,
  ShieldCheck,
} from "lucide-react";
import { api } from "../api";
import { QueryResponse, Citation } from "../types";
import { EmptyState } from "./Common";

export function Chat() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      setResponse(await api.query({ query, top_k: 5, filters: {} }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không gọi được RAG service");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="workspace chat-workspace">
      <header className="page-hero chat-hero">
        <div className="hero-copy">
          <p className="eyebrow">Public legal assistant</p>
          <h1>Hỏi đáp pháp luật có dẫn nguồn</h1>
          <p>
            Trợ lý AI truy xuất câu trả lời từ kho văn bản pháp luật đã nạp, hiển thị mức
            tin cậy và nguồn tham chiếu để bạn kiểm chứng nhanh hơn.
          </p>
          <div className="hero-badges" aria-label="Trust indicators">
            <span className="trust-badge">
              <ShieldCheck size={15} /> Có dẫn nguồn
            </span>
            <span className="trust-badge">
              <Database size={15} /> Dựa trên dữ liệu nội bộ
            </span>
            <span className="trust-badge warning">
              <Scale size={15} /> Không thay thế tư vấn pháp lý
            </span>
          </div>
        </div>
        <div className="hero-card" aria-hidden="true">
          <div className="hero-card-icon">
            <BookOpen size={26} />
          </div>
          <strong>Legal AI</strong>
          <span>RAG-backed answers with transparent citations</span>
        </div>
      </header>

      <form className="query-panel prompt-composer" onSubmit={submit}>
        <div className="composer-header">
          <div>
            <span className="section-kicker">Đặt câu hỏi</span>
            <h2>Nhập tình huống pháp lý cần tra cứu</h2>
          </div>
          <span className="composer-hint">Top 5 nguồn phù hợp nhất</span>
        </div>
        <label className="sr-only" htmlFor="legal-query">
          Câu hỏi pháp luật
        </label>
        <textarea
          id="legal-query"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ví dụ: Tôi muốn hỏi về quyền lợi khi nghỉ việc thì cần xem quy định nào?"
          rows={5}
        />
        <div className="composer-footer">
          <p className="form-helper">
            Câu trả lời được tạo từ corpus hiện có và nên được kiểm chứng với nguồn gốc.
          </p>
          <button className="primary" disabled={loading || !query.trim()}>
            {loading ? <Loader2 className="spin" size={18} /> : <Search size={18} />}
            Gửi câu hỏi
          </button>
        </div>
      </form>

      {error && (
        <div className="notice danger alert-card" role="alert">
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {response && (
        <div className="answer-layout">
          <article
            className={
              response.status === "low_confidence" ? "answer answer-card warning" : "answer answer-card"
            }
          >
            <div className="answer-status-row">
              <span className={response.status === "low_confidence" ? "status-pill warn" : "status-pill ok"}>
                {response.status === "low_confidence" ? (
                  <AlertTriangle size={15} />
                ) : (
                  <CheckCircle2 size={15} />
                )}
                {response.status === "low_confidence" ? "Chưa đủ căn cứ" : "Đã trả lời"}
              </span>
              <span className="confidence-pill">{Math.round(response.confidence * 100)}% tin cậy</span>
            </div>
            <div className="answer-content">
              <p>{response.answer}</p>
            </div>
            <div className="legal-disclaimer">
              <Scale size={16} />
              <small>{response.disclaimer}</small>
            </div>
          </article>

          <section className="sources" aria-labelledby="sources-title">
            <div className="sources-header">
              <span className="source-icon" aria-hidden="true">
                <FileSearch size={18} />
              </span>
              <div>
                <span className="section-kicker">Nguồn kiểm chứng</span>
                <h2 id="sources-title">Nguồn tham chiếu</h2>
              </div>
            </div>
            {response.citations.length === 0 ? (
              <EmptyState text="Chưa có nguồn phù hợp trong corpus." />
            ) : (
              response.citations.map((citation, index) => (
                <CitationRow citation={citation} index={index + 1} key={`${citation.title}-${index}`} />
              ))
            )}
          </section>
        </div>
      )}
    </section>
  );
}

function CitationRow({ citation, index }: { citation: Citation; index: number }) {
  return (
    <article className="citation source-card">
      <div className="source-card-header">
        <span className="source-index">#{index}</span>
        <div>
          <strong>{citation.title}</strong>
          <span className="source-meta">
            {citation.article || "Không rõ điều khoản"} · {Math.round(citation.score * 100)}% phù hợp
          </span>
        </div>
      </div>
      <div className="source-snippet">
        <Quote size={17} />
        <p>{citation.snippet}</p>
      </div>
      {citation.source_url && (
        <a className="source-link" href={citation.source_url}>
          <Link2 size={14} />
          {citation.source_url}
        </a>
      )}
    </article>
  );
}
