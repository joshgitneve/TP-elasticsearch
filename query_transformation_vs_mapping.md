IMPORTANT: le type de requete décide de ce que devient la recherche. Le mapping décide les tokens qui apparaissent dans l'index inversé.

# Questions to ask yourself: Does the query transform what I typed? match does, term doesn't.

- term : valeur est prise telle quelle, quel que soit le champ. term ne regarde jamais le mapping pour transformer ta recherche.
- match : valeur passe par l'analyseur du champ. match s'adapte au mapping.

Les quatre combinaisons
	Champ keyword	                                                                Champ text (french)
term	✅ Égalité exacte, majuscules comprises.                ❌ Presque toujours 0 résultat : ta valeur brute ne correspond pas 
        C'est l'usage prévu.	                                   aux termes découpés et normalisés. C'est ton cas « Data Engineer Senior ».
match	⚠️ Se comporte comme term : l'analyseur                 ✅ Ta recherche est découpée et normalisée
        d'un keyword ne transforme rien.	                       comme les documents. C'est l'usage prévu.

Donc, avec term, on cherche une valeur exacte, sans aucune transformation, dans le champ indiqué. Le mapping a décidé à l'indexation quels termes 
existent dans ce champ. Le type de requête décide à la recherche si ma valeur est transformée (match) ou non (term). Il y a un résultat seulement
 si les deux côtés produisent le même terme.
