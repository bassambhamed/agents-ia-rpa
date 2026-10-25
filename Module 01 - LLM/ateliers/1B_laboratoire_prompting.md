# Atelier 1.B — Laboratoire de prompting

**Durée : 50 min**

Dans ce laboratoire, chaque technique du module 1.3 est appliquée puis **mesurée** sur des cas du projet fil rouge. L'objectif n'est pas d'obtenir le meilleur score, mais de comprendre ce que chaque technique apporte et ce qu'elle coûte.

## Mode d'emploi

1. Ouvrez un notebook vierge **dans le dossier `ateliers/`** (ou une console Python lancée depuis ce dossier).
2. Copiez les blocs de code au fur et à mesure, exécutez-les, puis notez vos résultats dans les tableaux.
3. Les blocs marqués ✏️ sont à modifier : c'est là que vous expérimentez.

```python
import outils_llm as llm

MODELE = llm.choisir_modele()   # ou forcez : "groq:openai/gpt-oss-120b", "nvidia:nvidia/nemotron-3.5-lightning-30b-a3b"…
print("Modèle utilisé :", MODELE)
```

---

## Exercice 1 — Itération guidée : détecter l'urgence

**Tâche.** Attribuer à une demande client un niveau d'urgence : `haute`, `normale` ou `basse`.
**Mesure.** Exactitude sur les 20 premières demandes du jeu de test.

### Le banc de test

```python
from typing import Literal
from pydantic import BaseModel

class Urgence(BaseModel):
    urgence: Literal["haute", "normale", "basse"]

CAS_URGENCE = llm.charger_demandes("test").head(20)

def banc_urgence(systeme, avec_schema=False):
    """Classe les 20 demandes et affiche l'exactitude."""
    def un_cas(ligne):
        demande = llm.formater_demande(ligne)
        if avec_schema:
            r = llm.demander(demande, systeme=systeme, modele=MODELE, schema=Urgence)
            return r.objet.urgence if r.objet else None
        r = llm.demander(demande, systeme=systeme, modele=MODELE)
        return r.texte.strip().lower()

    predictions = llm.en_lot(un_cas, [ligne for _, ligne in CAS_URGENCE.iterrows()])
    print(f"Exactitude : {llm.exactitude(CAS_URGENCE.urgence, predictions):.0%}")
    return predictions
```

### V0 — Zero-shot minimal

```python
V0 = "Quelle est l'urgence de cette demande ?"
p0 = banc_urgence(V0)
p0[:5]   # regardez à quoi ressemblent les réponses
```

### V1 — Format de sortie précisé

```python
V1 = "Indique l'urgence de cette demande. Réponds uniquement par un mot : haute, normale ou basse."
p1 = banc_urgence(V1)
```

### V2 — Rôle et contexte : les règles de Fictiva

```python
REGLES = llm.lire("regles_tri.md")

V2 = f"""Tu es chargé du tri des emails du service client de Fictiva SA, distributeur B2B de matériel informatique.
Les règles de tri de l'entreprise :

{REGLES}

Indique l'urgence de la demande selon ces règles. Réponds uniquement par un mot : haute, normale ou basse."""
p2 = banc_urgence(V2)
```

### V3 — Exemples (few-shot)

```python
exemples = llm.charger_demandes("exemples")
EXEMPLES = "\n\n".join(
    f"{llm.formater_demande(ligne)}\nUrgence : {ligne['urgence']}" for _, ligne in exemples.iterrows()
)

V3 = V2 + f"\n\nExemples de demandes déjà classées :\n\n{EXEMPLES}"
p3 = banc_urgence(V3)
```

### V4 — Balises et schéma imposé

```python
V4 = f"""Tu es chargé du tri des emails du service client de Fictiva SA, distributeur B2B de matériel informatique.
Attribue à la demande un niveau d'urgence en appliquant strictement les règles ci-dessous.

<regles>
{REGLES}
</regles>

<exemples>
{EXEMPLES}
</exemples>

Vérifie d'abord un par un les critères d'urgence haute, puis ceux d'urgence basse ; sinon, l'urgence est normale."""
p4 = banc_urgence(V4, avec_schema=True)
```

### ✏️ À vous

Écrivez une **V5** qui corrige les erreurs restantes : relisez les demandes mal classées (`CAS_URGENCE[[...]]`) et ajoutez une précision **générale**, valable pour toute demande future.

### Résultats

| Version | Ce qui change | Exactitude | Observations |
|---|---|---|---|
| V0 | Question seule | | |
| V1 | + format de sortie | | |
| V2 | + rôle et règles de Fictiva | | |
| V3 | + exemples | | |
| V4 | + balises, méthode, schéma | | |
| V5 | votre version | | |

**Questions**
1. Pourquoi V0 obtient-elle un score si bas ? Distinguez le problème de **format** et le problème de **critères**.
2. Quelle étape apporte le plus ? Pourquoi ?
3. V4 est-elle meilleure que V3 sur ce modèle ? Sur un autre ? Qu'en concluez-vous ?

---

## Exercice 2 — Raisonnement : calculer un remboursement

**Tâche.** Appliquer la politique de retours (`donnees/politique_retours.md`) à dix cas : délais, statut Premium, défaut, consommables, frais plafonnés, validation au-delà de 5 000 CHF.
**Mesure.** Nombre de montants exacts sur 10, tokens consommés, coût estimé et latence.

On compare un petit modèle **sans raisonnement**, aidé ou non par les techniques du module 1.3, à un **modèle de raisonnement**. Adaptez les deux noms à vos accès. Le petit modèle n'a pas de tarif public dans `llm.TARIFS` : son coût s'affiche à 0, comparez plutôt les tokens.

```python
import pandas as pd

MODELE_SIMPLE = "nvidia:nvidia/nemotron-3.5-bolt-e4b"   # petit modèle, sans raisonnement
MODELE_RAISONNEMENT = "groq:openai/gpt-oss-20b"         # modèle de raisonnement
from pydantic import BaseModel, Field

POLITIQUE = llm.lire("politique_retours.md")
CAS = llm.charger_json("cas_remboursement.json")

SYSTEME_REMBOURSEMENT = f"""Tu appliques la politique de retours de Fictiva SA.

<politique>
{POLITIQUE}
</politique>

Pour le cas soumis, calcule le montant remboursable en CHF et indique si une validation par un responsable est requise."""

class Montant(BaseModel):
    montant_chf: float
    validation_requise: bool

class MontantRaisonne(BaseModel):
    raisonnement: str = Field(description="Les étapes du calcul et les articles appliqués")
    montant_chf: float
    validation_requise: bool

def banc_remboursement(schema, modele, repetitions=1):
    """Exactitude, coût et latence sur les 10 cas ; vote majoritaire si repetitions > 1."""
    def un_cas(cas):
        reponses = [
            llm.demander(f"<cas>\n{cas['description']}\n</cas>", systeme=SYSTEME_REMBOURSEMENT,
                         modele=modele, schema=schema)
            for _ in range(repetitions)
        ]
        montants = [round(r.objet.montant_chf, 2) for r in reponses if r.objet]
        vote = max(set(montants), key=montants.count) if montants else None
        return {
            "cas": cas["id"],
            "attendu": cas["montant_attendu_chf"],
            "obtenu": vote,
            "juste": vote is not None and abs(vote - cas["montant_attendu_chf"]) < 0.01,
            "tokens": sum(r.tokens_entree + r.tokens_sortie for r in reponses),
            "cout_usd": sum(r.cout_usd or 0 for r in reponses),
            "latence_s": round(sum(r.latence_s for r in reponses), 1),
        }

    resultats = pd.DataFrame(llm.en_lot(un_cas, CAS))
    print(f"{resultats.juste.sum()}/10 justes, {resultats.tokens.sum()} tokens, coût total {resultats.cout_usd.sum():.4f} $")
    return resultats
```

Lancez les quatre variantes :

```python
direct = banc_remboursement(Montant, MODELE_SIMPLE)                             # A. réponse directe
raisonne = banc_remboursement(MontantRaisonne, MODELE_SIMPLE)                   # B. chain-of-thought
vote = banc_remboursement(MontantRaisonne, MODELE_SIMPLE, repetitions=3)        # C. self-consistency (3 tirages)
modele_raisonnement = banc_remboursement(Montant, MODELE_RAISONNEMENT)          # D. modèle de raisonnement
```

```python
raisonne   # lisez les cas faux : quel article a été mal appliqué ?
```

| Variante | Justes / 10 | Tokens | Coût estimé | Latence | Observations |
|---|---|---|---|---|---|
| A. Directe | | | | | |
| B. Chain-of-thought | | | | | |
| C. Self-consistency | | | | | |
| D. Modèle de raisonnement | | | | | |

**Questions**
1. Le champ `raisonnement` est placé **avant** `montant_chf` dans le schéma. Pourquoi cet ordre compte-t-il ?
2. Le petit modèle aidé par le chain-of-thought (B, C) rattrape-t-il le modèle de raisonnement (D) ? À quel coût ?
3. Relancez B avec `MODELE_RAISONNEMENT` : le chain-of-thought explicite apporte-t-il encore quelque chose à un modèle qui raisonne déjà ?
4. La self-consistency vaut-elle son coût ici ?

---

## Exercice 3 — Décomposition : traiter une demande en trois prompts

**Tâche.** Traiter la demande ci-dessous de bout en bout : vérifier les droits du client, calculer le montant, rédiger la réponse.

```python
from typing import Literal

DEMANDE = """<demande>
De : Olivier Roux (Roux Avocats), client Premium CL-10012
Objet : Retour imprimante

Bonjour,
Nous avons reçu le 9 septembre l'imprimante LX-500 (facture FAC-2026-1166 : 400 CHF, plus 25 CHF de livraison).
Elle fonctionne parfaitement mais ne correspond pas à nos besoins. Nous souhaitons la retourner et être remboursés.
Olivier Roux
</demande>"""

AUJOURD_HUI = "Nous sommes le 24 octobre 2026."   # le modèle ne connaît pas la date du jour
```

**Résultat attendu** : client Premium, 45 jours après la livraison, donc dans le délai de 60 jours (art. 1.2) ; retour sans défaut : 400 − 40 = **360 CHF**, frais de livraison non remboursés (art. 3) ; remboursement sous 14 jours après réception (art. 6).

### Version en un seul prompt

```python
r = llm.demander(
    f"{AUJOURD_HUI}\n\n{DEMANDE}\n\nTraite cette demande selon la politique et rédige la réponse au client.",
    systeme=f"Tu es agent du service client de Fictiva SA.\n<politique>\n{POLITIQUE}\n</politique>",
    modele=MODELE,
)
print(r.texte)
```

### Version décomposée

```python
class Faits(BaseModel):
    statut_client: Literal["premium", "standard", "inconnu"]
    jours_depuis_livraison: int | None
    article_defectueux: bool | None
    prix_articles_chf: float | None
    frais_livraison_chf: float | None
    article_personnalise_ou_consommable: bool | None

class Decision(BaseModel):
    articles_appliques: list[str] = Field(description="Ex. ['1.2', '3']")
    montant_chf: float
    validation_requise: bool
    explication: str

# 1. Extraire les faits
faits = llm.demander(f"{AUJOURD_HUI}\n\n{DEMANDE}", modele=MODELE, schema=Faits,
                     systeme="Extrais les faits utiles au traitement d'un retour. N'invente rien : null si absent.").objet
print(faits)

# 2. Appliquer la politique aux faits, et seulement aux faits
decision = llm.demander(f"<faits>\n{faits.model_dump_json(indent=2)}\n</faits>", modele=MODELE, schema=Decision,
                        systeme=SYSTEME_REMBOURSEMENT).objet
print(decision)

# 3. Rédiger la réponse
reponse = llm.demander(
    f"{DEMANDE}\n\n<decision>\n{decision.model_dump_json(indent=2)}\n</decision>",
    systeme="Tu rédiges les réponses du service client de Fictiva SA : ton cordial et professionnel, "
            "vouvoiement, 8 lignes au plus. Appuie-toi uniquement sur la décision fournie.",
    modele=MODELE,
)
print(reponse.texte)
```

### Grille de comparaison

| Critère | Un seul prompt | Décomposé |
|---|---|---|
| Montant exact (360 CHF) | | |
| Articles cités correctement | | |
| Frais de livraison traités correctement | | |
| Délai de remboursement mentionné | | |
| Ton et longueur adaptés | | |
| Étape fautive identifiable en cas d'erreur | | |

**Questions**
1. Que se passe-t-il si vous retirez `AUJOURD_HUI` ?
2. Quel est l'intérêt de pouvoir tester chaque étape séparément ? Pensez à la mise en production (Jour 5).

---

## Exercice 4 — Fiabilité

### 4.a — Savoir dire « je ne sais pas »

Huit questions sur la politique de retours : quatre ont une réponse dans le texte, quatre n'en ont pas.

```python
QUESTIONS = llm.charger_json("questions_politique.json")

def banc_questions(systeme):
    reponses = llm.en_lot(
        lambda q: llm.demander(q["question"], systeme=systeme, modele=MODELE).texte,
        QUESTIONS,
    )
    for q, texte in zip(QUESTIONS, reponses):
        attendu = "répondable" if q["repondable"] else "INCONNU attendu"
        print(f"{q['id']} ({attendu}) : {q['question']}\n   → {texte.strip()[:200]}\n")
```

```python
# Sans permission d'ignorer
banc_questions(f"Tu réponds aux questions des clients de Fictiva SA.\n<politique>\n{POLITIQUE}\n</politique>")
```

```python
# ✏️ Avec permission d'ignorer : complétez la consigne
banc_questions(f"""Tu réponds aux questions des clients de Fictiva SA en t'appuyant uniquement sur la politique ci-dessous.
<politique>
{POLITIQUE}
</politique>
Si la politique ne permet pas de répondre, réponds exactement : INCONNU.
Sinon, réponds en une phrase et cite l'article utilisé.""")
```

| | Questions répondables justes (/4) | « INCONNU » sur les questions sans réponse (/4) |
|---|---|---|
| Sans permission | | |
| Avec permission | | |

Regardez la question Q5 (frais d'envoi du retour) : la politique parle des frais de livraison *initiaux*, pas des frais de retour. Le modèle fait-il la différence ?

### 4.b — Température et variabilité

Les modèles open-weight acceptent le paramètre `temperature` (certaines API propriétaires, comme Claude depuis octobre 2026, ne l'acceptent plus). Exécutez le même prompt cinq fois à deux températures et comptez les réponses distinctes.

```python
CONSIGNE = "Propose un objet d'email (8 mots au plus) pour répondre à un client dont la livraison a deux jours de retard."

for t in (0.0, 1.5):
    sorties = [llm.demander(CONSIGNE, modele=MODELE, temperature=t).texte.strip() for _ in range(5)]
    print(f"Température {t} : {len(set(sorties))} réponse(s) distincte(s)")
    for s in sorties:
        print("   ", s)
```

**Questions**
1. Une température nulle garantit-elle des réponses identiques ? Pourquoi pas toujours ?
2. Pour le tri des demandes, quelle variabilité est acceptable ? Comment l'obtenir sans régler la température ?

---

## Mon guide de bonnes pratiques

Notez vos cinq conclusions principales. Vous compléterez ce guide chaque jour.

1.
2.
3.
4.
5.
