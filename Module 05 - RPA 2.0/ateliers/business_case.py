"""
business_case.py : éligibilité, priorisation et business case d'un processus (atelier 5.B).

- score_eligibilite : grille pondérée de six critères, notés de 1 (défavorable) à 5 (favorable) ;
- matrice_priorisation : valeur attendue face à l'effort d'automatisation, en quatre quadrants ;
- business_case : gains et coûts annuels (y compris les coûts cachés : tokens, supervision
  humaine, maintenance et évaluation), retour sur investissement et délai de retour ;
- sensibilite : effet d'une hypothèse sur le bénéfice net ;
- risque_ai_act : pré-diagnostic indicatif du niveau de risque au sens de l'AI Act.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import pandas as pd

DOSSIER = Path(__file__).resolve().parent

# critère : (poids, question posée, repères de notation)
CRITERES = {
    "volume": (0.20, "Combien de cas par mois ?", "1 : moins de 50 ; 3 : environ 500 ; 5 : plus de 5 000"),
    "repetitivite": (0.15, "Les cas se ressemblent-ils ?", "1 : chaque cas est unique ; 5 : quelques variantes connues"),
    "structuration": (0.15, "Les données d'entrée sont-elles structurées ?",
                      "1 : textes libres, scans ; 5 : formulaires, bases de données (la RPA 2.0 traite le non-structuré, à un coût)"),
    "regles": (0.15, "Les règles de décision sont-elles explicites et stables ?", "1 : jugement d'expert ; 5 : règles écrites"),
    "valeur": (0.20, "Quel gain attendu ?", "temps, délai de réponse, qualité, conformité, satisfaction"),
    "risque": (0.15, "Une erreur est-elle grave ?", "1 : atteinte aux personnes ou aux droits ; 5 : conséquences faibles et réversibles"),
}


def score_eligibilite(notes: dict[str, float]) -> float:
    """Score pondéré de 1 à 5 ; au-dessus de 3,5, le processus est un bon candidat."""
    manquants = set(CRITERES) - set(notes)
    if manquants:
        raise ValueError(f"Notes manquantes : {', '.join(sorted(manquants))}")
    return round(sum(poids * notes[c] for c, (poids, _, _) in CRITERES.items()), 2)


def charger_processus() -> list[dict]:
    return json.loads((DOSSIER / "donnees" / "processus_exemples.json").read_text(encoding="utf-8"))


def portefeuille(processus: list[dict]) -> pd.DataFrame:
    lignes = [{"id": p["id"], "processus": p["nom"], "domaine": p["domaine"], "eligibilite": score_eligibilite(p["notes"]),
               "effort": p["effort"], "risque": p["notes"]["risque"], "typologie": p["typologie"]} for p in processus]
    t = pd.DataFrame(lignes).set_index("id")
    t["quadrant"] = [quadrant(e, f) for e, f in zip(t.eligibilite, t.effort)]
    return t.sort_values("eligibilite", ascending=False)


def quadrant(eligibilite: float, effort: float) -> str:
    valeur_haute, effort_faible = eligibilite >= 3.5, effort <= 3
    if valeur_haute and effort_faible:
        return "gain rapide"
    if valeur_haute:
        return "projet stratégique"
    return "à reconsidérer" if effort_faible else "à écarter"


def matrice_priorisation(table: pd.DataFrame, titre: str = "Matrice de priorisation"):
    """Nuage de points : effort en abscisse, éligibilité en ordonnée, quatre quadrants."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.axhline(3.5, color="#d7dee6"), ax.axvline(3, color="#d7dee6")
    for x, y, texte in [(1.6, 4.85, "Gains rapides"), (4.4, 4.85, "Projets stratégiques"),
                        (1.6, 1.15, "À reconsidérer"), (4.4, 1.15, "À écarter")]:
        ax.text(x, y, texte, ha="center", color="#5b6770", fontsize=10, style="italic")
    couleurs = ["#c0392b" if r <= 2 else "#123a63" for r in table.risque]
    ax.scatter(table.effort, table.eligibilite, s=160, c=couleurs, alpha=0.85)
    for ident, ligne in table.iterrows():
        ax.annotate(f"{ident} {ligne.processus}", (ligne.effort, ligne.eligibilite), xytext=(8, 4),
                    textcoords="offset points", fontsize=8.5)
    ax.set(xlim=(0.5, 5.5), ylim=(1, 5), xlabel="Effort d'automatisation (1 faible, 5 élevé)",
           ylabel="Éligibilité pondérée (1 à 5)", title=titre)
    ax.text(0.6, 1.05, "en rouge : risque élevé en cas d'erreur", color="#c0392b", fontsize=8)
    fig.tight_layout()
    return fig


@dataclass
class Hypotheses:
    """Hypothèses annuelles d'un business case ; les montants sont en CHF.

    Trois populations de cas : traités de bout en bout sans humain (avec un contrôle
    qualité par échantillonnage), validés par un humain (relecture d'une proposition),
    et exceptions traitées entièrement à la main."""

    cas_par_mois: float = 6000
    minutes_manuelles_par_cas: float = 6.0
    cout_horaire_chf: float = 75.0  # salaire chargé de l'équipe concernée
    taux_automatisation: float = 0.50  # cas clos sans intervention humaine
    taux_validation: float = 0.35  # cas validés par un humain ; le reste est traité à la main
    minutes_validation_par_cas: float = 2.0
    part_controle_qualite: float = 0.05  # cas automatiques relus par échantillonnage
    taux_erreur_residuel: float = 0.005  # erreurs non détectées parmi les cas automatiques
    cout_par_erreur_chf: float = 150.0  # correction, geste commercial, temps perdu
    tokens_par_cas: float = 3500
    prix_usd_par_million_tokens: float = 0.30  # tarif payant moyen (entrée et sortie)
    chf_par_usd: float = 0.80
    construction_chf: float = 80000  # conception, intégration, tests, conduite du changement
    exploitation_annuelle_chf: float = 25000  # hébergement, supervision technique, licences
    evaluation_maintenance_annuelle_chf: float = 30000  # golden set, prompts, mises à jour des modèles


def business_case(h: Hypotheses) -> dict:
    """Bilan annuel : gains de temps, coûts directs et cachés, retour sur investissement."""
    if h.taux_automatisation + h.taux_validation > 1:
        raise ValueError("taux_automatisation + taux_validation ne peut pas dépasser 1")
    cas_an = h.cas_par_mois * 12
    heures_avant = cas_an * h.minutes_manuelles_par_cas / 60
    minutes_apres = cas_an * (h.taux_automatisation * h.part_controle_qualite * h.minutes_validation_par_cas
                              + h.taux_validation * h.minutes_validation_par_cas
                              + (1 - h.taux_automatisation - h.taux_validation) * h.minutes_manuelles_par_cas)
    heures_apres = minutes_apres / 60
    gain = (heures_avant - heures_apres) * h.cout_horaire_chf
    cout_llm = cas_an * h.tokens_par_cas / 1e6 * h.prix_usd_par_million_tokens * h.chf_par_usd
    cout_erreurs = cas_an * h.taux_automatisation * h.taux_erreur_residuel * h.cout_par_erreur_chf
    recurrent = cout_llm + cout_erreurs + h.exploitation_annuelle_chf + h.evaluation_maintenance_annuelle_chf
    net_recurrent = gain - recurrent
    return {
        "heures_avant": round(heures_avant),
        "heures_apres": round(heures_apres),
        "gain_annuel_chf": round(gain),
        "cout_llm_annuel_chf": round(cout_llm),
        "cout_erreurs_annuel_chf": round(cout_erreurs),
        "couts_recurrents_annuels_chf": round(recurrent),
        "benefice_net_annuel_chf": round(net_recurrent),
        "benefice_premiere_annee_chf": round(net_recurrent - h.construction_chf),
        "roi_premiere_annee": round((net_recurrent - h.construction_chf) / (h.construction_chf + recurrent), 2),
        "delai_retour_mois": round(12 * h.construction_chf / net_recurrent, 1) if net_recurrent > 0 else None,
        "cout_par_cas_avant_chf": round(h.minutes_manuelles_par_cas / 60 * h.cout_horaire_chf, 2),
        "cout_par_cas_apres_chf": round((heures_apres * h.cout_horaire_chf + recurrent + h.construction_chf / 3) / cas_an, 2),
    }


def sensibilite(h: Hypotheses, variable: str, valeurs: list[float]) -> pd.DataFrame:
    """Bénéfice net et délai de retour quand une hypothèse varie, les autres restant fixes."""
    return pd.DataFrame([{variable: v, **business_case(replace(h, **{variable: v}))} for v in valeurs]).set_index(variable)[
        ["gain_annuel_chf", "couts_recurrents_annuels_chf", "benefice_net_annuel_chf", "delai_retour_mois"]]


DOMAINES_HAUT_RISQUE = {
    "biometrie": "identification biométrique, reconnaissance des émotions",
    "infrastructures_critiques": "sécurité des infrastructures critiques (énergie, eau, transport)",
    "education": "accès à l'éducation, évaluation des élèves",
    "emploi": "recrutement, sélection, promotion, licenciement, évaluation des travailleurs",
    "services_essentiels": "accès aux services essentiels : crédit, assurance vie et maladie, prestations sociales",
    "repressif_justice_migration": "répression, justice, migration, asile, contrôle aux frontières",
}


def risque_ai_act(pratique_interdite: bool = False, domaines: tuple[str, ...] = (),
                  interagit_avec_des_personnes: bool = False, genere_du_contenu: bool = False) -> dict:
    """Pré-diagnostic indicatif (AI Act, règlement (UE) 2024/1689 modifié par le règlement 2026/1744).
    Il ne remplace pas une analyse juridique : il oriente la discussion avec le juriste et le DPO."""
    if pratique_interdite:
        niveau, obligations = "inacceptable", ["pratique interdite depuis le 2 février 2025 : ne pas déployer"]
    elif domaines:
        niveau = "haut risque (annexe III)"
        obligations = ["gestion des risques, qualité des données, documentation technique, journalisation",
                       "supervision humaine effective, exactitude et robustesse",
                       "applicable à partir du 2 décembre 2027 (règlement 2026/1744)"]
    elif interagit_avec_des_personnes or genere_du_contenu:
        niveau = "risque limité : obligations de transparence (art. 50)"
        obligations = ["informer les personnes qu'elles échangent avec un système d'IA",
                       "signaler les contenus générés ou manipulés par l'IA"]
    else:
        niveau, obligations = "risque minimal", ["pas d'obligation spécifique ; codes de conduite volontaires"]
    obligations.append("pour tous : maîtrise de l'IA des équipes (art. 4), en vigueur depuis le 2 février 2025")
    obligations.append("en Suisse : nLPD (transparence, droits des personnes, analyse d'impact si risque élevé)")
    return {"niveau": niveau, "obligations": obligations,
            "domaines": [DOMAINES_HAUT_RISQUE.get(d, d) for d in domaines]}


def hypotheses_dict(h: Hypotheses) -> dict:
    return asdict(h)
