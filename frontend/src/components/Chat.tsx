import { FormEvent, useState } from "react";
import { Loader2, Search } from "lucide-react";
import { api } from "../api";
import { QueryResponse, Citation } from "../types";
import { EmptyState } from "./Common";

export function Chat() {
  const [query, setQuery] = useState("Tôi muốn hỏi về quyền lợi khi nghỉ việc thì cần xem quy định nào?");
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
      <header className="page-header">
        <div>
          <p className="eyebrow">Public chat</p>
          <h1>Hỏi đáp pháp luật có dẫn nguồn</h1>
        </div>
      </header>

      <form className="query-panel" onSubmit={submit}>
        <textarea value={query} onChange={(event) => setQuery(event.target.value)} rows={4} />
        <button className="primary" disabled={loading || !query.trim()}>
          {loading ? <Loader2 className="spin" size={18} /> : <Search size={18} />}
          Gửi câu hỏi
        </button>
      </form>

      {error && <div className="notice danger">{error}</div>}
      {response && (
        <div className="answer-layout">
          <article className={response.status === "low_confidence" ? "answer warning" : "answer"}>
            <div className="answer-meta">
              <span>{response.status === "low_confidence" ? "Chưa đủ căn cứ" : "Đã trả lời"}</span>
              <strong>{Math.round(response.confidence * 100)}%</strong>
            </div>
            <p>{response.answer}</p>
            <small>{response.disclaimer}</small>
          </article>
          <section className="sources">
            <h2>Nguồn tham chiếu</h2>
            {response.citations.length === 0 ? (
              <EmptyState text="Chưa có nguồn phù hợp trong corpus." />
            ) : (
              response.citations.map((citation, index) => (
                <CitationRow citation={citation} key={`${citation.title}-${index}`} />
              ))
            )}
          </section>
        </div>
      )}
    </section>
  );
}

function CitationRow({ citation }: { citation: Citation }) {
  return (
    <article className="citation">
      <div>
        <strong>{citation.title}</strong>
        <span>
          {citation.article || "Không rõ điều khoản"} · {Math.round(citation.score * 100)}%
        </span>
      </div>
      <p>{citation.snippet}</p>
      {citation.source_url && <a href={citation.source_url}>{citation.source_url}</a>}
    </article>
  );
}
