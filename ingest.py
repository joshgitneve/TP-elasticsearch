"""Partie 3a — Crée l'index `offres` avec un mapping explicite puis ingère le NDJSON en bulk.

Usage : python ingest.py [--fichier data/offres.ndjson] [--reset]
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterator
from pathlib import Path

from elasticsearch import helpers

from es_client import INDEX, get_client

SETTINGS = {"number_of_shards": 1, "number_of_replicas": 0}

MAPPINGS = {
            "dynamic": "strict",
            "properties": {
                        "id": {"type": "keyword"},
                        "entreprise": {"type": "keyword"},
                        "ville": {"type": "keyword"},
                        "contrat": {"type": "keyword"},
                        "teletravail": {"type": "keyword"},
                        "titre": {"type": "text",
                            "analyzer": "french",
                            "fields":{
                                "brut": { "type": "keyword"}
                                }
                            },
                        "description": {"type": "text",
                            "analyzer": "french"},
                        "competences": {"type": "keyword",
                                "fields":{
                                    "texte": { "type": "text",
                                            "analyzer": "french"}
                                }
                            },
                        "localisation": {"type": "geo_point"},
                        "experience_annees": {"type": "integer"},
                        "salaire_min": {"type": "integer"},
                        "salaire_max": {"type": "integer"},
                        "date_publication": {"type": "date"}
    }
}

def lire_actions(fichier: Path) -> Iterator[dict]:
    """générateur qui lit le fichier ligne à ligne et produit
    {"_index": INDEX, "_id": <id de l'offre>, "_source": <document>}."""
    with open(fichier, encoding='utf-8') as f:
        # enumerate numérote les lignes pour pouvoir les citer dans les messages d'erreur
        for numero, ligne in enumerate(f, start=1):
            ligne = ligne.strip()
            if not ligne:
                continue

            # Ligne qui n'est pas du JSON (fichier tronqué, ligne coupée...) : on ajoute le n° de ligne
            try:
                doc = json.loads(ligne)
            except json.JSONDecodeError as e:
                raise ValueError(f"{fichier}, ligne {numero} : JSON invalide ({e.msg})") from e

            # JSON valide mais pas un objet (ex. une liste [1, 2]) : doc["id"] n'aurait pas de sens
            if not isinstance(doc, dict):
                raise ValueError(f"{fichier}, ligne {numero} : objet JSON attendu, reçu {type(doc).__name__}")

            # Objet sans "id" : impossible de construire le _id (les autres champs sont vérifiés par le mapping strict)
            if "id" not in doc:
                raise ValueError(f"{fichier}, ligne {numero} : champ \"id\" manquant")

            yield {"_index": INDEX, "_id": doc["id"], "_source": doc}



def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fichier", type=Path, default=Path("data/offres.ndjson"))
    parser.add_argument("--reset", action="store_true", help="supprime l'index s'il existe")
    args = parser.parse_args()

    # Fichier absent: on s'arrête avant de toucher au cluster (sinon --reset aurait déjà vidé l'index)
    if not args.fichier.is_file():
        parser.error(f"fichier introuvable : {args.fichier}")

    es = get_client()
    print("Cluster :", es.info()["version"]["number"])
    # TODO 3 : si --reset, supprimer l'index (sans erreur s'il n'existe pas)
    if args.reset:
        if es.indices.exists(index=INDEX):
            es.indices.delete(index=INDEX)

    # TODO 4 : créer l'index s'il n'existe pas, avec SETTINGS et MAPPINGS
    if not es.indices.exists(index=INDEX):
        es.indices.create(index=INDEX, settings=SETTINGS, mappings=MAPPINGS)

    # TODO 5 : ingérer avec helpers.bulk (chunk_size=1000, raise_on_error=False), afficher les erreurs
    actions = lire_actions(args.fichier)
    executed_actions, errors = helpers.bulk(client=es, actions=actions, chunk_size=1000, raise_on_error=False)
    print(f"{executed_actions} actions éxecutés")
    print(f"{len(errors)} erreurs")
    for error in errors[:5]:
        print(error)

    # TODO 6 : rafraîchir l'index puis afficher le nombre de documents (es.count)
    es.indices.refresh(index=INDEX)
    count = es.count(index=INDEX)
    print(f'Index "{INDEX}" contient {count["count"]} documents')


if __name__ == "__main__":
    main()

