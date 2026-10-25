import type { Extrait } from "@/lib/api";

type Props = {
  extraits: Extrait[];
  prefixe: string; // identifiant unique de l'échange, pour les ancres des extraits
  actif: number | null; // extrait mis en évidence après un clic sur une citation
};

export default function ListeExtraits({ extraits, prefixe, actif }: Props) {
  return (
    <ol className="extraits">
      {extraits.map((e) => (
        <li key={e.numero} id={`${prefixe}-extrait-${e.numero}`}
          className={["extrait", e.cite ? "cite" : "", actif === e.numero ? "actif" : ""].join(" ")}>
          <div className="extrait-entete">
            <span className="numero">{e.numero}</span>
            <span className="extrait-titre">
              {e.document}
              {e.section && <span className="section"> › {e.section}</span>}
            </span>
            {e.score !== null && <span className="score" title="Score de la recherche">{e.score.toFixed(3)}</span>}
          </div>
          <div className="extrait-fichier">
            {e.fichier}
            {e.cite && <span className="etiquette">cité</span>}
          </div>
          <p className="extrait-texte">{e.texte}</p>
        </li>
      ))}
    </ol>
  );
}
