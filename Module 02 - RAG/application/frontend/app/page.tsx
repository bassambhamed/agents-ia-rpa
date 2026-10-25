"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import BarreLaterale from "@/components/BarreLaterale";
import ListeExtraits from "@/components/ListeExtraits";
import TexteCite from "@/components/TexteCite";
import { api, type DocumentInfo, type Reponse, type ResultatRecherche, type Sante } from "@/lib/api";

type Mode = "reponse" | "recherche";

type Echange = {
  id: number;
  question: string;
  mode: Mode;
  statut: "en_cours" | "ok" | "erreur";
  reponse?: Reponse;
  recherche?: ResultatRecherche;
  erreur?: string;
};

export default function Page() {
  const [sante, setSante] = useState<Sante | null>(null);
  const [erreurSante, setErreurSante] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [exemples, setExemples] = useState<string[]>([]);
  const [echanges, setEchanges] = useState<Echange[]>([]);
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<Mode>("reponse");
  const [extraitsOuverts, setExtraitsOuverts] = useState<Record<number, boolean>>({});
  const [extraitActif, setExtraitActif] = useState<Record<number, number>>({});
  const compteur = useRef(0);
  const fin = useRef<HTMLDivElement>(null);
  const occupe = echanges.some((e) => e.statut === "en_cours");

  // État du service, documents et exemples. Le backend construit son index au
  // démarrage : tant qu'il ne répond pas, on réessaie toutes les 5 secondes.
  useEffect(() => {
    let annule = false;
    let minuterie: ReturnType<typeof setTimeout> | undefined;
    async function verifier() {
      try {
        const etat = await api.sante();
        if (annule) return;
        setSante(etat);
        setErreurSante(null);
        const [docs, questions] = await Promise.all([api.documents(), api.exemples()]);
        if (!annule) {
          setDocuments(docs);
          setExemples(questions);
        }
      } catch (erreur) {
        if (annule) return;
        setErreurSante((erreur as Error).message);
        minuterie = setTimeout(verifier, 5000);
      }
    }
    verifier();
    return () => {
      annule = true;
      clearTimeout(minuterie);
    };
  }, []);

  useEffect(() => {
    fin.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [echanges]);

  async function envoyer(texte: string) {
    const q = texte.trim();
    if (q.length < 3 || occupe) return;
    const id = ++compteur.current;
    const modeEnvoye = mode;
    setEchanges((liste) => [...liste, { id, question: q, mode: modeEnvoye, statut: "en_cours" }]);
    setQuestion("");
    try {
      const resultat =
        modeEnvoye === "reponse" ? { reponse: await api.question(q) } : { recherche: await api.recherche(q, 4) };
      setEchanges((liste) => liste.map((e) => (e.id === id ? { ...e, ...resultat, statut: "ok" } : e)));
    } catch (erreur) {
      const message = (erreur as Error).message;
      setEchanges((liste) => liste.map((e) => (e.id === id ? { ...e, statut: "erreur", erreur: message } : e)));
    }
  }

  function soumettre(evenement: FormEvent) {
    evenement.preventDefault();
    envoyer(question);
  }

  function toucheClavier(evenement: KeyboardEvent<HTMLTextAreaElement>) {
    if (evenement.key === "Enter" && !evenement.shiftKey) {
      evenement.preventDefault();
      envoyer(question);
    }
  }

  // Clic sur une citation [n] : ouvre la liste des extraits et met l'extrait n en évidence.
  function montrerExtrait(id: number, numero: number) {
    setExtraitsOuverts((o) => ({ ...o, [id]: true }));
    setExtraitActif((a) => ({ ...a, [id]: numero }));
    setTimeout(() => {
      document.getElementById(`e${id}-extrait-${numero}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
  }

  return (
    <div className="page">
      <header className="entete">
        <div>
          <p className="surtitre">Fictiva SA · Module 02 — RAG</p>
          <h1>Assistant documentaire</h1>
        </div>
        <p className="sous-titre">Réponses tirées de la documentation publique, avec citations des sources.</p>
      </header>

      <div className="corps">
        <BarreLaterale sante={sante} erreurSante={erreurSante} documents={documents} exemples={exemples}
          occupe={occupe} onExemple={envoyer} />

        <main className="conversation">
          {echanges.length === 0 && (
            <div className="accueil">
              <h2>Posez une question à la documentation</h2>
              <p>
                Conditions générales de vente, livraison, retours, maintenance, portail client, NAS NS4… L&apos;assistant
                recherche les extraits pertinents, puis le modèle rédige une réponse qui cite chaque extrait utilisé.
              </p>
              <p>
                Le mode <strong>Extraits seulement</strong> montre ce que trouve la recherche, sans appeler le modèle.
              </p>
            </div>
          )}

          {echanges.map((e) => (
            <article key={e.id} className="echange">
              <div className="question">
                <span className="role">{e.mode === "reponse" ? "Question" : "Recherche"}</span>
                <p>{e.question}</p>
              </div>

              {e.statut === "en_cours" && (
                <div className="carte chargement">
                  <span className="points" aria-hidden />
                  {e.mode === "reponse" ? "Recherche des extraits et rédaction de la réponse…" : "Recherche des extraits…"}
                </div>
              )}

              {e.statut === "erreur" && <div className="carte erreur">{e.erreur}</div>}

              {e.reponse && (
                <div className={`carte reponse${e.reponse.trouve ? "" : " non-trouve"}`}>
                  {!e.reponse.trouve && <p className="bandeau">Information absente de la documentation publique</p>}
                  <TexteCite texte={e.reponse.reponse} onCitation={(n) => montrerExtrait(e.id, n)} />
                  <div className="meta">
                    <span className="code">{e.reponse.modele}</span>
                    <span>{e.reponse.latence_s.toFixed(1)} s</span>
                    {e.reponse.cout_usd !== null && <span>coût estimé {formaterCout(e.reponse.cout_usd)}</span>}
                    {e.reponse.sources.length > 0 && <span>Sources : {e.reponse.sources.join(", ")}</span>}
                  </div>
                  <details className="details-extraits" open={extraitsOuverts[e.id] ?? false}
                    onToggle={(ev) => {
                      const ouvert = ev.currentTarget.open;
                      setExtraitsOuverts((o) => ({ ...o, [e.id]: ouvert }));
                    }}>
                    <summary>
                      Extraits transmis au modèle ({e.reponse.extraits.length}) · cités :{" "}
                      {e.reponse.extraits.filter((x) => x.cite).map((x) => x.numero).join(", ") || "aucun"}
                    </summary>
                    <ListeExtraits extraits={e.reponse.extraits} prefixe={`e${e.id}`} actif={extraitActif[e.id] ?? null} />
                  </details>
                </div>
              )}

              {e.recherche && (
                <div className="carte">
                  <p className="titre-carte">Extraits retrouvés, sans appel au modèle</p>
                  <ListeExtraits extraits={e.recherche.extraits} prefixe={`e${e.id}`} actif={null} />
                </div>
              )}
            </article>
          ))}
          <div ref={fin} />

          <form className="saisie" onSubmit={soumettre}>
            <div className="modes" role="radiogroup" aria-label="Mode">
              <button type="button" role="radio" aria-checked={mode === "reponse"}
                className={mode === "reponse" ? "choisi" : ""} onClick={() => setMode("reponse")}>
                Réponse du modèle
              </button>
              <button type="button" role="radio" aria-checked={mode === "recherche"}
                className={mode === "recherche" ? "choisi" : ""} onClick={() => setMode("recherche")}>
                Extraits seulement
              </button>
            </div>
            <div className="ligne-saisie">
              <textarea value={question} onChange={(ev) => setQuestion(ev.target.value)} onKeyDown={toucheClavier}
                placeholder="Votre question (Entrée pour envoyer, Maj + Entrée pour aller à la ligne)" rows={2}
                maxLength={1000} aria-label="Question" />
              <button type="submit" className="envoyer" disabled={occupe || question.trim().length < 3}>
                Envoyer
              </button>
            </div>
          </form>
        </main>
      </div>
    </div>
  );
}

function formaterCout(cout: number): string {
  return cout === 0 ? "0 $" : `${cout.toFixed(5)} $`;
}
