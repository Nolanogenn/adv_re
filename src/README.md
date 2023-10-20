The src/create_adv_dataset.py file is used to generated aversarial dataset. To reproduce you need:

- tacred test file in data/test.json
- a json file of all the entities together with their types named entities_complete.json
  - this file follows the structure:\
    { entity_id :\
    { surface_form : entity surface form,\
    type: type of the entity,\
    subj_of: a list of relations in which this entity appears as subject,\
    obj_of : a list of relations in which this entity appears as an object}\
    ..}\

The script is invoked as follows:
```
python create_adv_dataset.py {N} {M}
```
where {N} identifies the substitution strategy implemented (1: same-role, 2: same-type, 3:diff-type, 4:masked), and {M} identifies the entity to substitute (1: subject, 2: object, 3: both).


**NB**: this code is not optimized, and should only be used for experimental purposes.
