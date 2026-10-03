Questions : pourquoi ne pas utiliser le compte elastic pour Logstash ? 
R: Pour que les permissions des differents roles soient configurables chacun; un role pour rentrer des logs, un autre pour les analyser.
Que se passerait-il si le pipeline web tentait d'écrire dans logs-generic-default ? 
R: Ne peut pas. Les permissions donnent acces à logs-web.* est pas logs-generic-*. 
Pourquoi le mot de passe est-il transmis par variable d'environnement plutôt qu'écrit dans les fichiers .conf ?
R: Pour que chacun guard ses codes d'accès secret.

Partie 0:
Questions : quels champs Logstash a-t-il ajoutés à votre phrase ? 
R: @version, @timestamp.

Que contient @timestamp : l'heure de quoi ?
R: l'heure de l'écriture du log.
À quoi sert l'option --path.data /tmp/essai (indice : un autre Logstash pourrait utiliser le même dossier de données) ?
R: Il signifie où stocker les logs transformés.  

Partie 1.2
Questions : les documents sont-ils indexés ? 
R: Non, Dev Tools montre 5000 documents encore à version 2, comme avant. 

Quelle erreur Elasticsearch renvoie-t-il, avec quel code HTTP et quel type
d'exception ? 
R: Elasticsearch renvoit un "strict_dynamic_mapping_exception" avec un code erreur 400 parce que notre mapping est "set to strict", 
 -> dynamic introduction of [@timestamp] within [_doc] is not allowed"
Quels noms de champs sont cités ? @timestamp
Faites le lien avec "dynamic": "strict" (TP d'introduction, ex. 1.4). -> Notre mapping ne permets pas l'introduction d'un champs qui n'existe pas parce que l'on a mit le setting "dynamic": "strict".

Partie 1.3:
Questions : le nombre de documents a-t-il changé ? 
R: Non
Et le _version de OFF-00002 ? 
R: Oui
Pourquoi ?
R: Parce que le pipeline écrase les anciens versions vue que l'on fournit _id pour chaque document. 
Pourquoi a-t-on préféré supprimer ces champs plutôt que d'assouplir le mapping de l'index ? 
Parce que l'on veut pas perdre la protection de notre schema/mapping et on n'a pas besoin des nouveaux champs.

Pourquoi l'index offres doit-il exister avant le premier démarrage de Logstash (indice : manage_template => false et mapping dynamique) ? 
R: Parce que l'on veut pas le mapping dynamique et notre mapping stricte est lié à l'index. 

1.4
Questions : combien de fois le fichier a-t-il été lu ? 
R: Il est lu à chaque démarrage .

Que se passerait-il avec la sincedb par défaut au lieu de /dev/null ? 
R: Rien serait lu de nouveau car le défaut est de lire seulement des nouveau lignes rajoutés.

Et si document_id n'était pas renseigné ?
5000 documents seraient rajoutés à chaque démarrage.

2.1

Questions : combien de pipelines sont chargés, avec combien de workers chacun ? 
On voit deux: web, offres, 10 workers chacun.
Que valent in, filtered et out pour offres, et que représentent-ils depuis le dernier démarrage ? 
Ils valent 5000 chacun. Ils represent le flux et donc compte des documents depuis la derniere démarrage.

Quel plugin du pipeline consomme le plus de temps (duration_in_millis) ?
Assez difficile à lire quand meme pour un humain. 
Total duration est de 5115ms.
Mutate prend 625ms.
elasticsearch prend 4345ms
file(input) 83ms (queue_push_duration_in_millis - attente)

Donc output(elasticsearch) prend le plus de temps, ~85% du temps.

2.2
Questions : le document OFF-99999 est-il dans l'index ? 
non.
Où se trouve-t-il ? 
Dans le DLQ.
Quelle raison de refus est enregistrée dans [@metadata][dead_letter_queue] ? 
Un grep qui fonctionne correctement (grep -i "warn\|error\|index") nous donne le log dans le DLQ:
{"status" => 400, "error" => {"type" => "strict_dynamic_mapping_exception", "reason" => "[1:54] mapping set to strict, 
dynamic introduction of [prime] within [_doc] is not allowed"}} - Visiblement le mapping dyanamique strice bloque encore 
l'introduction d'un nouveau clé. 
Comparez avec raise_on_error=False dans ingest.py : qu'apporte la DLQ en plus ? 
La DLQ nous apporte un raison claire pour l'erreur et en plus il nous dit quel document précis cause le probleme.
Décrivez en trois étapes comment vous corrigeriez et réinjecteriez ce document.
Diagnostiquer : lire l'événement dans la DLQ pour savoir pourquoi il a été refusé. 
Corriger : soit supprimer le champ avec "mutate" dans le pipeline d'ingestion, soit l'ajouter au mapping.
Réinjecter : Logstash a un plugin d'entrée dead_letter_queue, qui lit les événements de la DLQ. On l'utilise dans un pipeline 
séparé avec la même sortie vers offres, et la correction dans le filter si on a choisi de supprimer le champ + commit_offsets => true 
pour que logstash reconnait les documents relus et traités/re-injectés. On déclare l'input path: /usr/share/logstash/data/dead_letter_queue/offres. 
Et on déclare le nouveau pipeline dans pipelines.yml.

2.3
Questions : si ce fichier n'était pas monté, combien de pipelines Logstash chargerait-il ? 
Sans pipelines.yml, Logstash revient à son comportement par défaut et prend tout les fishiers .conf dans le dossier pipelines 
et les concatene dans un seul pipeline appelé main.
Dans ce cas, que deviendrait une offre lue dans offres.ndjson : dans quelle(s) destination(s) serait-elle envoyée ? 
Il serait envoyés aux deux destinations: les web logs et offres. 
Et une ligne de log d'accès ? -> Aussi aux deux destinations cités. 

Deux autres avantages à isoler les pipelines: (1) Filtre dédié à chaque pipeline. (2) Un pipeline cassé n'a pas d'effet sur les autres. 
(3) Chque pipeline peut avoir ses propre configuration (nombre de workers, batch size, type de queue) et monitoring, avec ses propres stats. 
(4) Peut changer des pipelines séparéments sans arreter le flux des autres.

2.4
Questions : Logstash est arrêté brutalement (docker kill) pendant la lecture d'un gros fichier. 
Avec la file en mémoire, que deviennent les événements lus mais pas encore envoyés ? Quel réglage change ce comportement, et quelle garantie obtient-on ? 
Par défaut -> queue.type: memory donc les événement pas encore envoyés sont perdus. Avec QUEUE_TYPE=persisted, la queue est écrit sur disk et un événement est seulement envlevé de cette queue après l'output a confirmé que ES l'a réçu. Àprès un arrêt, Logstash relance puis renvoit tout ce qui est encore dans la queue. On obtient alors "at-least-once delivery"

Pourquoi le document_id de la partie 1 devient-il alors indispensable ? Car at-least-once delivery signifie qu'il pourrait avoir des doublons. Par exemple si des documents sont envoyés mais ES n'a pas eu le temps de fournir la confirmation, ces docs restent dans la queue. Sans le gaurantee fournit par l'id, ces doncuments seraient encore envoyés et stockés dans ES. Avec l'id, ces docs sont simplements écrasés dans ES avec la nouvelle copie.

3.2 
Questions : quels champs sont extraits ? 

  "request": 
  "agent": 
  "auth": 
  "ident": 
  "verb": 
  "referrer":
  "response": 
  "bytes": 
  "clientip": 
  "httpversion": 
  "timestamp": 

Sous quel type apparaît http.response.status_code ? 
"response"

Pourquoi timestamp doit-il encore être traité ? 
Parce qu'il n'est pas pour l'instant un vrai objet timestamp de Logstash, mais un string.

Écrivez et testez un motif qui extrait OFF-01468 de l'URL /offres/OFF-01468/postuler.
Sample data: /offres/OFF-02113/postuler
Grok pattern: ^/offres/%{OFFRE_ID:offre_id}
Custommpattern tested in Grok debugger: OFFRE_ID OFF-[0-9]{5}
Si on enleve des chiffres du sample data, le grok pattern ne match plus.

3.4 
Questions : combien de documents (attendu : 20 700) et combien d'échecs de grok (attendu : 0) ? 20700 et zero.
Quel est le nom de l'index caché (backing index) qui contient les données, et que signifie chaque partie de ce nom ? 
logs-web-default = datastream <type>-<dataset>-<namespace>
Le premier événement est-il daté du 23/09/2026 à 00:00:39 (+02:00), soit 22:00:39 UTC la veille ? Oui. 
Quel type a reçu http.response.status_code, et pourquoi est-ce important pour la suite ? Long. Important pour filtrer dans Kibana et des recherches de type group by ex. 2xx (success), 3xx (redirect), 4xx (client error), 5xx (server error) .
Quel index.mode est utilisé ? logsdb, qui fait que un datastream est crée automatiquement. 

3.5
Questions : que constatez-vous, et pourquoi le problème ne se posait-il pas pour offres ? 
Nombre de documents a doublé. sincedb_path => "/dev/null" donc logstash relis tout des le début de generate_access_logs.py. Pour offre l'id était défini pour chaque doc et pas crée à la voler par es, donc les docs étaient remplacés au lieu d'etre recrées. _id n'est pas déterminé pour les logs, donc des logs relu sont de-nouveau crée.
Peut-on mettre à jour ou remplacer un document dans un data stream ? Non, Data streams sont "append-only". 
Proposez deux solutions pour pouvoir rejouer ce fichier sans doublon (indice : sincedb, et un _id calculé à partir du contenu de la ligne avec le filtre fingerprint).

Soit (1) on donne sincedb_path un vrai file path, dans le  data volume de Logstash, au lieu de /dev/null, pour que Logstash sait sur restart où il était dans le read et il saute ce qui a été lu déjà, soit (2) on donne un _id a chaque ligne de log calculé sur lui même (fingerprint filter hash). Une ligne relu produit le meme id et datastreams refuse des _ids qui existent déjà. Cela rends le pipeline idempotent.

The difference between the two is that sincedb avoids reading again, but doesn't protect against the bookmark being lost (deleted volume, crash, file renamed), wheras fingerprint protects the index itself, even if the file is read again.
