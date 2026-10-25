// Client de l'API FastAPI (schémas : backend/app/schemas.py).
// Les chemins /api/* sont relayés vers le backend par next.config.ts.

export type Extrait = {
  numero: number;
  fichier: string;
  document: string;
  section: string;
  texte: string;
  score: number | null;
  cite: boolean;
};

export type Reponse = {
  question: string;
  reponse: string;
  trouve: boolean;
  extraits: Extrait[];
  sources: string[];
  modele: string;
  latence_s: number;
  cout_usd: number | null;
};

export type ResultatRecherche = {
  question: string;
  extraits: Extrait[];
};

export type DocumentInfo = {
  fichier: string;
  titre: string;
  extraits: number;
};

export type Sante = {
  statut: string;
  modele: string;
  documents: number;
  extraits_indexes: number;
  reranking: boolean;
  langsmith: boolean;
};

async function appeler<T>(chemin: string, options: RequestInit = {}): Promise<T> {
  let reponse: Response;
  try {
    reponse = await fetch(`/api${chemin}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
    });
  } catch {
    throw new Error("Serveur injoignable.");
  }
  if (!reponse.ok) {
    let detail = `Erreur ${reponse.status}`;
    try {
      const corps = await reponse.json();
      if (typeof corps.detail === "string") detail = corps.detail;
    } catch {
      if (reponse.status >= 500) detail += " : le backend FastAPI est-il démarré ?";
    }
    throw new Error(detail);
  }
  return (await reponse.json()) as T;
}

export const api = {
  sante: () => appeler<Sante>("/sante"),
  documents: () => appeler<DocumentInfo[]>("/documents"),
  exemples: () => appeler<string[]>("/exemples"),
  question: (question: string) =>
    appeler<Reponse>("/question", { method: "POST", body: JSON.stringify({ question }) }),
  recherche: (question: string, k = 4) =>
    appeler<ResultatRecherche>("/recherche", { method: "POST", body: JSON.stringify({ question, k }) }),
};
