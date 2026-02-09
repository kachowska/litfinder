"use client";

import { useState, useEffect } from "react";

// --- Types ---
interface Article {
  id: string;
  title: string;
  authors: { name: string }[];
  year: number;
  journal_name?: string;
  cited_by_count: number;
  doi?: string;
  abstract?: string;
  relevance_score?: number;
}

// --- Components ---

function GlowOrb({ className }: { className: string }) {
  return (
    <div className={`absolute rounded-full blur-3xl opacity-20 animate-pulse ${className}`} />
  );
}

function Header() {
  return (
    <header className="fixed top-0 w-full z-50">
      <div className="mx-4 mt-4">
        <div className="max-w-6xl mx-auto px-6 py-3 bg-white/5 backdrop-blur-2xl border border-white/10 rounded-2xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-400 to-cyan-400 flex items-center justify-center shadow-lg shadow-emerald-500/25">
                <span className="text-lg">📚</span>
              </div>
              <span className="text-lg font-bold text-white">LitFinder</span>
            </div>

            <a
              href="https://t.me/litfinder_bot"
              target="_blank"
              className="px-4 py-2 bg-white text-slate-900 rounded-xl font-medium text-sm hover:bg-white/90 transition shadow-lg"
            >
              Открыть в Telegram
            </a>
          </div>
        </div>
      </div>
    </header>
  );
}

function SearchBox({ onSearch, loading }: { onSearch: (q: string) => void; loading: boolean }) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !loading) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div className="relative">
        {/* Glow effect */}
        <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 via-cyan-500 to-blue-500 rounded-2xl opacity-50 blur-xl group-hover:opacity-75 transition" />

        {/* Input container */}
        <div className="relative flex items-center bg-slate-900/80 backdrop-blur-xl border border-white/20 rounded-2xl overflow-hidden shadow-2xl">
          <div className="pl-5 text-slate-400">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Введите тему исследования..."
            className="flex-1 px-4 py-5 bg-transparent text-white text-lg outline-none placeholder:text-slate-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading}
            className="m-2 px-6 py-3 bg-gradient-to-r from-emerald-500 to-cyan-500 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-emerald-500/25 transition-all disabled:opacity-50"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              "Найти"
            )}
          </button>
        </div>
      </div>
    </form>
  );
}

function StatCard({ icon, value, label }: { icon: string; value: string; label: string }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-white/5 backdrop-blur border border-white/10 rounded-xl">
      <span className="text-2xl">{icon}</span>
      <div>
        <div className="text-white font-bold">{value}</div>
        <div className="text-slate-400 text-xs">{label}</div>
      </div>
    </div>
  );
}

function ArticleCard({
  article,
  isSelected,
  onToggle
}: {
  article: Article;
  isSelected: boolean;
  onToggle: () => void;
}) {
  const authors = article.authors?.slice(0, 2).map(a => a.name).join(", ");
  const hasMore = (article.authors?.length || 0) > 2;

  const openArticle = (e: React.MouseEvent) => {
    e.stopPropagation();
    const doi = article.doi?.replace("https://doi.org/", "");
    if (doi) {
      window.open(`https://doi.org/${doi}`, "_blank");
    } else if (article.id) {
      window.open(`https://openalex.org/works/${article.id}`, "_blank");
    }
  };

  return (
    <div
      onClick={onToggle}
      className={`group relative p-5 rounded-2xl cursor-pointer transition-all duration-300 ${isSelected
        ? "bg-emerald-500/10 border-2 border-emerald-500/50 shadow-lg shadow-emerald-500/10"
        : "bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20"
        }`}
    >
      {/* Selection indicator */}
      <div className={`absolute top-4 right-4 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${isSelected ? "bg-emerald-500 border-emerald-500" : "border-slate-500 group-hover:border-slate-400"
        }`}>
        {isSelected && (
          <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>

      {/* Content */}
      <h3 className="text-white font-medium text-lg leading-snug pr-10 mb-3 line-clamp-2">
        {article.title}
      </h3>

      <p className="text-slate-400 text-sm mb-4">
        {authors}{hasMore ? " и др." : ""}
      </p>

      <div className="flex flex-wrap gap-2 mb-3">
        <span className="px-3 py-1 bg-slate-800 rounded-lg text-xs text-slate-300">
          📅 {article.year || "—"}
        </span>
        <span className="px-3 py-1 bg-slate-800 rounded-lg text-xs text-slate-300">
          📊 {article.cited_by_count || 0} цит.
        </span>
        {article.relevance_score && (
          <span className="px-3 py-1 bg-emerald-500/20 rounded-lg text-xs text-emerald-400">
            ✨ {(article.relevance_score * 100).toFixed(0)}%
          </span>
        )}
      </div>

      <button
        onClick={openArticle}
        className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition flex items-center gap-2"
      >
        🔗 Открыть статью
      </button>
    </div>
  );
}

function BibliographyPanel({
  articles,
  onClose
}: {
  articles: Article[];
  onClose: () => void;
}) {
  const [bibliography, setBibliography] = useState<string[]>([]);
  const [bibtex, setBibtex] = useState("");
  const [format, setFormat] = useState<"gost" | "bibtex">("gost");
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchBibliography = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/v1/bibliography", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ articles }),
        });
        const data = await res.json();
        setBibliography(data.formatted_list || []);
        setBibtex(data.bibtex || "");
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    fetchBibliography();
  }, [articles]);

  const copyToClipboard = () => {
    const text = format === "gost" ? bibliography.join("\n\n") : bibtex;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-slate-900 border border-white/10 rounded-3xl overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div>
            <h2 className="text-xl font-bold text-white">Список литературы</h2>
            <p className="text-slate-400 text-sm">{articles.length} источников</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-xl transition"
          >
            <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Format toggle */}
        <div className="flex gap-2 p-4 bg-white/5">
          {[
            { id: "gost" as const, label: "ГОСТ Р 7.0.100" },
            { id: "bibtex" as const, label: "BibTeX" },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFormat(f.id)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition ${format === f.id
                ? "bg-emerald-500 text-white"
                : "bg-white/10 text-slate-400 hover:text-white"
                }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6 max-h-80 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-8 h-8 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="space-y-4 font-mono text-sm text-slate-300">
              {format === "gost" ? (
                bibliography.map((item, i) => (
                  <p key={i} className="leading-relaxed">{item}</p>
                ))
              ) : (
                <pre className="whitespace-pre-wrap">{bibtex}</pre>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 p-6 border-t border-white/10 bg-white/5">
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-2 px-5 py-2.5 bg-white/10 hover:bg-white/20 text-white rounded-xl transition"
          >
            {copied ? "✓ Скопировано!" : "📋 Копировать"}
          </button>
          <button
            onClick={onClose}
            className="px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-cyan-500 text-white font-medium rounded-xl hover:shadow-lg hover:shadow-emerald-500/25 transition"
          >
            Готово
          </button>
        </div>
      </div>
    </div>
  );
}

// --- Main Page ---

export default function Home() {
  const [results, setResults] = useState<Article[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showBibliography, setShowBibliography] = useState(false);

  const handleSearch = async (searchQuery: string) => {
    setQuery(searchQuery);
    setLoading(true);
    setResults([]);
    setSelected(new Set());
    setOffset(0);

    try {
      const res = await fetch("http://localhost:8000/api/v1/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery, limit: 12, offset: 0 }),
      });
      const data = await res.json();
      setResults(data.results || []);
      setTotal(data.total || 0);
      setOffset(12);
    } catch (error) {
      console.error("Search error:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadMore = async () => {
    if (loadingMore || results.length >= total) return;
    setLoadingMore(true);

    try {
      const res = await fetch("http://localhost:8000/api/v1/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, limit: 12, offset }),
      });
      const data = await res.json();
      setResults([...results, ...(data.results || [])]);
      setOffset(offset + 12);
    } catch (error) {
      console.error("Load more error:", error);
    } finally {
      setLoadingMore(false);
    }
  };

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selected);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelected(newSelected);
  };

  const selectedArticles = results.filter(r => selected.has(r.id));

  return (
    <div className="min-h-screen bg-slate-950 text-white overflow-hidden">
      {/* Background effects */}
      <div className="fixed inset-0 pointer-events-none">
        <GlowOrb className="w-96 h-96 bg-emerald-500 -top-48 -left-48" />
        <GlowOrb className="w-96 h-96 bg-cyan-500 top-1/2 -right-48" />
        <GlowOrb className="w-96 h-96 bg-blue-500 -bottom-48 left-1/3" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(0,0,0,0.8)_100%)]" />
      </div>

      <Header />

      <main className="relative pt-32 pb-20 px-4">
        <div className="max-w-6xl mx-auto">
          {/* Hero */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-full text-emerald-400 text-sm mb-8">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              250+ млн научных работ (OpenAlex)
            </div>

            <h1 className="text-5xl md:text-7xl font-black mb-6 tracking-tight">
              <span className="bg-gradient-to-r from-white via-emerald-100 to-cyan-100 bg-clip-text text-transparent">
                Поиск статей
              </span>
              <br />
              <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                с умом
              </span>
            </h1>

            <p className="text-xl text-slate-400 mb-12 max-w-xl mx-auto">
              Находите релевантные научные публикации за секунды.
              Оформляйте список литературы по ГОСТ автоматически.
            </p>

            {/* Search */}
            <div className="flex justify-center mb-8">
              <SearchBox onSearch={handleSearch} loading={loading} />
            </div>

            {/* Quick stats */}
            {results.length === 0 && !loading && (
              <div className="flex flex-wrap justify-center gap-4 mt-12">
                <StatCard icon="📚" value="250M+" label="работ в OpenAlex" />
                <StatCard icon="🎓" value="ГОСТ" label="оформление" />
                <StatCard icon="⚡" value="< 1с" label="время поиска" />
              </div>
            )}
          </div>

          {/* Results */}
          {(results.length > 0 || loading) && (
            <div>
              {/* Results header */}
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-bold">
                    {loading ? "Поиск..." : `Найдено: ${total.toLocaleString()}`}
                  </h2>
                  {query && !loading && (
                    <p className="text-slate-400">по запросу «{query}»</p>
                  )}
                </div>

                {selected.size > 0 && (
                  <button
                    onClick={() => setShowBibliography(true)}
                    className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-emerald-500 to-cyan-500 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-emerald-500/25 transition-all"
                  >
                    📝 Оформить ({selected.size})
                  </button>
                )}
              </div>

              {/* Loading skeleton */}
              {loading && (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[...Array(6)].map((_, i) => (
                    <div key={i} className="h-44 bg-white/5 rounded-2xl animate-pulse" />
                  ))}
                </div>
              )}

              {/* Results grid */}
              {!loading && results.length > 0 && (
                <>
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {results.map((article) => (
                      <ArticleCard
                        key={article.id}
                        article={article}
                        isSelected={selected.has(article.id)}
                        onToggle={() => toggleSelect(article.id)}
                      />
                    ))}
                  </div>

                  {results.length < total && (
                    <div className="flex justify-center mt-8">
                      <button
                        onClick={loadMore}
                        disabled={loadingMore}
                        className="px-8 py-4 bg-white/10 hover:bg-white/20 border border-white/20 rounded-2xl text-white font-medium transition-all flex items-center gap-3"
                      >
                        {loadingMore ? (
                          <>
                            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            Загрузка...
                          </>
                        ) : (
                          <>
                            ⬇️ Загрузить ещё
                            <span className="text-slate-400">({results.length} из {total.toLocaleString()})</span>
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </main>

      {/* Bibliography modal */}
      {showBibliography && (
        <BibliographyPanel
          articles={selectedArticles}
          onClose={() => setShowBibliography(false)}
        />
      )}
    </div>
  );
}
