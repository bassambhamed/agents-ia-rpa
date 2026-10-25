import type { DocumentInfo, Sante } from "@/lib/api";

type Props = {
  sante: Sante | null;
  erreurSante: string | null;
  documents: DocumentInfo[];
  exemples: string[];
  occupe: boolean;
  onExemple: (question: string) => void;
};

export default function BarreLaterale({ sante, erreurSante, documents, exemples, occupe, onExemple }: Props) {
  return (
    <aside className="barre">
      <section className="panneau">
        <h2>Service</h2>
        {erreurSante ? (
          <p className="etat hors-ligne">
            <span className="pastille" /> Backend injoignable
            <span className="aide">{erreurSante}</span>
          </p>
        ) : sante ? (
          <>
            <p className="etat en-ligne">
              <span className="pastille" /> En ligne
            </p>
            <dl className="mesures">
              <dt>Modèle</dt>
              <dd className="code">{sante.modele}</dd>
              <dt>Index</dt>
              <dd>
                {sante.documents} documents, {sante.extraits_indexes} extraits
              </dd>
              <dt>Reranking</dt>
              <dd>{sante.reranking ? "activé" : "désactivé"}</dd>
              <dt>LangSmith</dt>
              <dd>{sante.langsmith ? "traces envoyées" : "non configuré"}</dd>
            </dl>
          </>
        ) : (
          <p className="etat">Connexion…</p>
        )}
      </section>

      {exemples.length > 0 && (
        <section className="panneau">
          <h2>Exemples (golden set)</h2>
          <ul className="exemples">
            {exemples.map((q) => (
              <li key={q}>
                <button type="button" disabled={occupe} onClick={() => onExemple(q)}>
                  {q}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {documents.length > 0 && (
        <section className="panneau">
          <h2>Documentation publique</h2>
          <ul className="documents">
            {documents.map((d) => (
              <li key={d.fichier}>
                <span className="doc-titre">{d.titre}</span>
                <span className="doc-meta">
                  {d.fichier} · {d.extraits} extraits
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="avertissement">Fictiva SA est une entreprise fictive : toutes les données sont synthétiques.</p>
    </aside>
  );
}
