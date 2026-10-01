from es_client import INDEX, get_client

es = get_client()
resp = es.search(
    index=INDEX,
    size=0,
    aggs={ "offres_par_mois": {
      "date_histogram": { 
        "field": "date_publication",
        "calendar_interval": "month", "format": "yyyy-MM" },
      "aggs": { "par_contrat": { "terms": { "field": "contrat", "size": 5 } }}
      }
    },
)

buckets = resp["aggregations"]["offres_par_mois"]["buckets"]

mois = []
nb_offres = []
for bucket in buckets:
    mois.append(bucket["key_as_string"])
    nb_offres.append(bucket["doc_count"])

print(mois)       # ['2026-04', '2026-05', ...]
print(nb_offres) 

print(f"Response type: {type(resp)}")
print(f"The body type: \n {type(resp.body)}")



