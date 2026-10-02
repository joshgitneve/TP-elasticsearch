"""Mini-défi — moteur de recherche d'offres en ligne de commande.

Attendu :
  python search.py "développeur python"
  python search.py "données spark" --ville Lyon --contrat CDI --salaire-min 45000
  python search.py "kubernetes" --autour "43.6108,3.8767"--rayon 50km --teletravail partiel
"""

from __future__ import annotations

import argparse

from es_client import INDEX, get_client

def _coordinates_checker(texte: str) -> tuple[float, float]:
    morceaux = texte.split(",")
    if len(morceaux) != 2:
        raise argparse.ArgumentTypeError("format attendu: lat,lon")

    try:
        lat = float(morceaux[0])
        lon = float(morceaux[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("lat et lon doivent être des nombres") from exc

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise argparse.ArgumentTypeError("lat entre -90 et 90, lon entre -180 et 180")

    return lat, lon


def construire_requete(args: argparse.Namespace) -> dict:
    """TODO : requête bool
    - must   : multi_match sur titre (x3), competences.texte (x2), description, tolérant aux fautes
    - filter : ville, contrat, teletravail (term), salaire_max >= --salaire-min (range),
               distance autour d'un point (geo_distance) si --autour est fourni
    """
    requete =  {
        "bool": {
            "must": {
                "multi_match": {
                    "query": args.texte,
                    "fields": ["titre^3", "competences.texte^2", "description"],
                    "fuzziness": "AUTO"
                }
            }, 
            "filter": []
        }
    }

    if args.ville:
        requete["bool"]["filter"].append({"terms": {"ville": [args.ville]}})
    if args.contrat:
        requete["bool"]["filter"].append({"term": {"contrat": args.contrat}})
    if args.teletravail:
        requete["bool"]["filter"].append({"term": {"teletravail": args.teletravail}})
    if args.salaire_min is not None:
        requete["bool"]["filter"].append({"range": {"salaire_max": {"gte": args.salaire_min}}})
    if args.autour:
        requete["bool"]["filter"].append({"geo_distance": {"distance": args.rayon, "localisation": { "lat": lat, "lon": lon } }})
    return requete


# POST offres/_search
# {
#   "query": { # on peut rajouter "explain": true ici avant "query" -> _explanation détaille (dans les résultats) le calcul de chaque score
#     "bool": {
#       "must": {
#         "multi_match": {
#           "query": "données",
#           "fields": [
#             "titre",
#             "description"
#           ]
#         }
#       },
#       "filter": [
#         {"term": {"contrat": "CDI"}},
#         {"terms": {"ville": ["Montpellier","Toulouse"]}},
#         {"range": {"salaire_max": {"gte": 50000}}}
#       ],
#       "must_not": {
#         "term": {
#           "teletravail": "aucun"
#         }
#       },
#       "should": {
#         "term": {
#           "competences": "Elasticsearch"
#         }
#       }
#     }
#   }
# }


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
        )
    p.add_argument("texte")
    p.add_argument("--ville")
    p.add_argument(
        "--contrat", choices=["CDI", "CDD", "Alternance", "Freelance", "Stage"]
    )
    p.add_argument("--teletravail", choices=["aucun", "partiel", "total"])
    p.add_argument("--salaire-min", type=int)
    p.add_argument("--autour", help="lat,lon")
    p.add_argument("--rayon", default="30km")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--taille", type=int, default=10)
    args = p.parse_args()

    es = get_client()

    # TODO : appeler es.search avec la requête, la pagination (from_, size), un highlight sur
    # description et trois facettes (aggs terms) : ville, contrat, compétences.
    response = es.search(
        index=INDEX, 
        query=construire_requete(args),
        from_=(args.page - 1) * args.taille,
        size=args.taille,
        highlight={"fields": {"description": {}}},
        aggs={
             "villes": {"terms": {"field": "ville", "size": 12}},
             "contrats": {"terms": {"field": "contrat"}},
             "competences": {"terms": {"field": "competences"}},
        })

# Afficher : total, puis pour chaque résultat score, titre, entreprise, ville, contrat, salaire,
    # l'extrait surligné, et enfin les facettes.
    total = response["hits"]["total"]["value"]
    print(f"{total} offres trouvées (page {args.page})\n")
    for hit in response["hits"]["hits"]:
        offre = hit["_source"]
        salaire = "non communiqué"
        if "salaire_min" in offre:
            salaire = f"{offre['salaire_min']} - {offre['salaire_max']} €"
        print(f"[{hit['_score']:.2f}] {offre['titre']} - {offre['entreprise']} "
              f"({offre['ville']}, {offre['contrat']}) - {salaire}")
        for extrait in hit.get("highlight", {}).get("description", []): # description is a list inside a dict named "highlight"
            print("    ...", extrait)

    for name in ("villes", "contrats", "competences"):
        print(f"\nFacette {name} 😊")
        for groupe in response["aggregations"][name]["buckets"]:
            print(f"  {groupe['key']} : {groupe['doc_count']}")


if __name__ == "__main__":
    main()
