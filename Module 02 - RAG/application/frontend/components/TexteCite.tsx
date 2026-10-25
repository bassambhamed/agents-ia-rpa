import { Fragment, type ReactNode } from "react";

type Props = {
  texte: string;
  onCitation: (numero: number) => void;
};

// Met en forme la réponse du modèle : paragraphes, listes à puces, **gras**,
// et citations [n] transformées en boutons qui affichent l'extrait cité.
export default function TexteCite({ texte, onCitation }: Props) {
  const blocs = texte.trim().split(/\n{2,}/);
  return (
    <div className="texte-reponse">
      {blocs.map((bloc, i) => {
        const lignes = bloc.split("\n").filter((ligne) => ligne.trim());
        const puce = /^\s*(?:[-*•]|\d+[.)])\s+/;
        if (lignes.length > 0 && lignes.every((ligne) => puce.test(ligne))) {
          return (
            <ul key={i}>
              {lignes.map((ligne, j) => (
                <li key={j}>{enLigne(ligne.replace(puce, ""), onCitation)}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={i}>
            {lignes.map((ligne, j) => (
              <Fragment key={j}>
                {j > 0 && <br />}
                {enLigne(ligne, onCitation)}
              </Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}

function enLigne(texte: string, onCitation: (numero: number) => void): ReactNode[] {
  const morceaux = texte.split(/(\*\*[^*]+\*\*|\[\d+(?:\s*,\s*\d+)*\])/g);
  return morceaux.map((morceau, i) => {
    if (/^\*\*[^*]+\*\*$/.test(morceau)) {
      return <strong key={i}>{morceau.slice(2, -2)}</strong>;
    }
    const citation = morceau.match(/^\[(\d+(?:\s*,\s*\d+)*)\]$/);
    if (citation) {
      return (
        <Fragment key={i}>
          {citation[1].split(",").map((n) => {
            const numero = Number(n.trim());
            return (
              <button key={numero} type="button" className="citation" title={`Voir l'extrait ${numero}`}
                onClick={() => onCitation(numero)}>
                {numero}
              </button>
            );
          })}
        </Fragment>
      );
    }
    return <Fragment key={i}>{morceau}</Fragment>;
  });
}
