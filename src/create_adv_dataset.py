import random
import tqdm
import re
import json
import numpy as np
import argparse
import os
import glob
import ast
from tqdm import tqdm 

pattern = r'Q[0-9A-Z]*'

parser=argparse.ArgumentParser(description='Create a controlled vocabulary for Relation Extraction')

parser.add_argument('sub_strategy', type=int, default=1, help='which strategy to use for the substitution, 1: the new entity will be chosen from the entire set of entities that are of a different type than the original entity, 2:  the new entity will be chosen from those of the same type as the former entity, 3: the new entity will be chosen from those appearing in the same relation, 4: the original entity will be masked')
parser.add_argument('ents_to_substitute', default=1, type=int, help='which entity to subsitute, 1: subj, 2: obj, 3: both')


args=parser.parse_args()

sub_strategy=args.sub_strategy
ents_to_sub=args.ents_to_substitute

all_entities=json.load(open('entities_complete.json'))
all_entities['QBLANK'] = {
        'surface_form' : '[MASK]'
        }

if sub_strategy == 1:
    list_ents_all = list(all_entities.keys())
    type2ents = json.load(open('types2ents.json'))
    all_types = list(type2ents.keys())
elif sub_strategy == 2:
    type2ents = json.load(open('types2ents.json'))
elif sub_strategy == 3:
    rel2ents = json.load(open('relations2ents.json'))

input_files = {
        'test' : './data/test.json'
        }

strategies_paper = {
        1 : 'sub3',
        2 : 'sub2',
        3 : 'sub1',
        4 : 'sub4'
        }
entities_sub_paper = {
        1 : 'subj',
        2 : 'obj',
        3 : 'subj+obj'
        }
for filetype in input_files:
    output_filename =f"{strategies_paper[args.sub_strategy]}_{entities_sub_paper[args.ents_to_substitute]}"
    output_file=f"data_probing/controlled_tacred_{filetype}_{output_filename}"
    output_file_json = output_file+'.json'
    if os.path.exists(output_file):
        os.remove(output_file)

    dict_file = json.load(open(input_files[filetype]))
    fewrel_dict = {}
    for rel in tqdm(dict_file):
        fewrel_dict[rel] = []
        sent_to_substitute = [x for x in dict_file[rel] if 'Q' in x['h'][1] and 'Q' in x['t'][1]]
        for sentence in sent_to_substitute:
            sentence_dict = {
                    "tokens": [],
                    "h" : [],
                    "t" : []
                    }
            tokens = sentence['tokens']
            relation_uri=rel

            sentence_boundary = "[]"
            subj=sentence['h']
            subj_str, subj_uri, subj_index = subj
            subj_index = [subj_index]
            subj_str = subj_str.replace('\n', '')
            subj_uri = f"http://www.wikidata.org/entity/{subj_uri}"

            if not 'type-label' in all_entities[subj_uri]:
                continue
            
            obj=sentence['t']
            obj_str, obj_uri, obj_index = obj
            obj_index = [obj_index]
            obj_str = obj_str.replace('\n', '')
            obj_uri = f"http://www.wikidata.org/entity/{obj_uri}"
            if not 'type-label' in all_entities[obj_uri]:
                continue

            ent_surface = {
                    subj_uri:subj_str,
                    obj_uri:obj_str
                    }

            boundaries={
                    'subj':subj_index[0],
                    'obj':obj_index[0],
                    }
            
            if ents_to_sub == 1:
                other_ent = obj_str
                other_ent_uri = obj_uri
                other_ent_boundaries = boundaries['obj']
                entities_to_substitute = [subj_uri]

            elif ents_to_sub == 2:
                other_ent = subj_str
                other_ent_uri = subj_uri
                other_ent_boundaries = boundaries['subj']
                entities_to_substitute = [obj_uri]
            else:
                entities_to_substitute = [subj_uri, obj_uri]
                other_ent_uri = []

            ents_role_dict = {
                subj_uri:'subj',
                obj_uri:'obj'
            }
            new_entities=[]
            tags = ["E1", "E2"]
            to_pass = False
            to_avoid = entities_to_substitute + [other_ent_uri]
            for uri in entities_to_substitute:
                if sub_strategy==1:
                    entity_type = all_entities[uri]['type']
                    possible_types = [t for t in all_types if t != entity_type]
                    random_type_number = np.random.randint(len(possible_types), size=1)[0]
                    list_ents=[x for x in type2ents[possible_types[random_type_number]] if x not in to_avoid]
                elif sub_strategy == 2:
                    entity_type = all_entities[uri]['type']
                    if entity_type != '' and '^^' not in entity_type:
                        if len(list(type2ents[entity_type])) > 1:
                            list_ents = [x for x in type2ents[entity_type] if x not in to_avoid]
                        else:
                            list_ents = [x for x in type2ents[entity_type]]
                    else:
                        to_pass = True
                        pass

                elif sub_strategy == 3:
                    if ents_to_sub==1:
                        list_ents=[x for x in rel2ents[relation_uri]['subjs'] if x not in to_avoid]
                    elif ents_to_sub==2:
                        list_ents=[x for x in rel2ents[relation_uri]['objs'] if x not in to_avoid]
                    else:
                        if ents_role_dict[uri] == 'subj':
                            list_ents=[x for x in rel2ents[relation_uri]['subjs'] if x not in to_avoid]
                        elif ents_role_dict[uri] == 'obj':
                            list_ents=[x for x in rel2ents[relation_uri]['objs'] if x not in to_avoid]
                elif sub_strategy == 4:
                    list_ents = ['MASK']

                if not to_pass:
                    try:
                        number = np.random.randint(len(list_ents), size=1)[0]
                        new_entity=all_entities[list_ents[number]]['surface_form'].replace('\n', '')
                        new_entity_uri = list_ents[number]
                        new_entities.append([new_entity, new_entity_uri])
                    except ValueError:
                        to_pass = True
            if not to_pass:
                if len(entities_to_substitute) > 1:
                    first_entity_index = np.argmin([boundaries[x][-1]+1 for x in boundaries])
                    second_entity_index = np.argmax([boundaries[x][-1]+1 for x in boundaries])

                    first_entity=list(boundaries.keys())[first_entity_index]
                    second_entity=list(boundaries.keys())[second_entity_index]

                    first_tag = tags[first_entity_index]
                    second_tag = tags[second_entity_index]

                    #print(' '.join(sentence['tokens']), entities_to_substitute, new_entities, boundaries)
                    sentence_no_tags = [
                            ' '.join(tokens[:boundaries[first_entity][0]]),
                            f"{new_entities[first_entity_index][0]}",
                            ' '.join(tokens[boundaries[first_entity][-1]+1:boundaries[second_entity][0]]),
                            f"{new_entities[second_entity_index][0]}",
                            ' '.join(tokens[boundaries[second_entity][-1]+1:])
                            ]
                    sentence_list = tokens[:boundaries[first_entity][0]] + new_entities[first_entity_index][0].split() + tokens[boundaries[first_entity][-1]+1:boundaries[second_entity][0]] +  new_entities[second_entity_index][0].split() + tokens[boundaries[second_entity][-1]+1:]

                    sentence_with_tags = [
                            ' '.join(tokens[:boundaries[first_entity][0]]),
                            f"[{first_tag}]",
                            f"{new_entities[first_entity_index][0]}",
                            f"[\{first_tag}]",
                            ' '.join(tokens[boundaries[first_entity][-1]+1:boundaries[second_entity][0]]),
                            f"[{second_tag}]",
                            f"{new_entities[second_entity_index][0]}",
                            f"[\{second_tag}]",
                            ' '.join(tokens[boundaries[second_entity][-1]+1:])
                            ]
                    if first_tag == 'E1':
                        head,head_uri = new_entities[first_entity_index]
                        tail,tail_uri = new_entities[second_entity_index]

                        len_original = len(boundaries['subj']) 
                        len_new = len(new_entities[first_entity_index][0].split())

                        difference_subj = len_original-len_new
                        difference_obj = len(boundaries['obj']) - len(new_entities[second_entity_index][0].split())

                        new_indices_head = [x for i, x in enumerate(boundaries['subj']) if i < len_new]
                        if difference_subj < 0:
                            last_num = new_indices_head[-1]
                            for num_iter in range(abs(difference_obj)):
                                to_append = last_num + num_iter + 1
                                new_indices_head.append(to_append)

                        new_indices_tail = [x-difference_subj for x in boundaries[second_entity]]
                        if difference_obj < 0:
                            last_num = new_indices_tail[-1]
                            for num_iter in range(abs(difference_obj)):
                                to_append = num_iter + last_num + 1
                                new_indices_tail.append(to_append)
                    else:
                        tail,tail_uri = new_entities[first_entity_index]
                        head,head_uri = new_entities[second_entity_index]

                        len_original = len(boundaries['obj']) 
                        len_new = len(new_entities[first_entity_index][0].split())

                        difference_obj = len_original-len_new
                        difference_subj = len(boundaries['subj']) - len(new_entities[second_entity_index][0].split())

                        new_indices_tail = [x for i, x in enumerate(boundaries['obj']) if i < len_new]
                        if difference_obj < 0:
                            last_num = new_indices_tail[-1]
                            for num_iter in range(abs(difference_obj)):
                                to_append = last_num + num_iter + 1
                                new_indices_tail.append(to_append)

                        new_indices_head = [x-difference_obj for x in boundaries[second_entity]]
                        if difference_subj < 0:
                            last_num = new_indices_head[-1]
                            for num_iter in range(abs(difference_subj)):
                                to_append = last_num + num_iter + 1
                                new_indices_head.append(to_append)


                    sentence_no_tags = ' '.join(sentence_no_tags)
                    sentence_no_tags = sentence_no_tags.replace('\n', '')
                    sentence_with_tags = ' '.join(sentence_with_tags)
                    sentence_with_tags = sentence_with_tags.replace('\n', '')
                    new_line = '\t'.join([
                        sentence_no_tags,
                        sentence_with_tags,
                        str(sentence_boundary),
                        relation_uri])

                    sentence_dict['tokens'] = sentence_list
                    sentence_dict['h'] = [head, re.findall(pattern,head_uri)[0], [new_indices_head]]
                    sentence_dict['t'] = [tail, re.findall(pattern,tail_uri)[0], [new_indices_tail]]
                    
                    fewrel_dict[rel].append(sentence_dict)
                else:
                    tag= "E1" if ents_to_sub == 1 else "E2"
                    if tag == 'E1':
                        head, head_uri = new_entities[0]
                        tail, tail_uri = other_ent, other_ent_uri
                        boundaries_idx = 'subj'
                        other_ent_idx = 'obj'
                    else:
                        tail, tail_uri = new_entities[0]
                        head, head_uri = other_ent, other_ent_uri
                        boundaries_idx = 'obj'
                        other_ent_idx = 'subj'

                    other_tag=[x for x in tags if x != tag][0]

                    sentence_no_tags = [
                            ' '.join(tokens[:boundaries[boundaries_idx][0]]),
                            f"{new_entities[0][0]}",
                            ' '.join(tokens[boundaries[boundaries_idx][-1]+1:])
                            ]

            
                    sentence_list = tokens[:boundaries[boundaries_idx][0]] + new_entities[0][0].split() + tokens[boundaries[boundaries_idx][-1]+1:]


                    bounds_new_entity = boundaries[boundaries_idx]
                    bounds_other_entity = boundaries[other_ent_idx]

                    if bounds_new_entity[0] < bounds_other_entity[0]:
                        if tag == 'E1':
                            boundaries_changed = boundaries['subj']
                            original_len = len(boundaries_changed)
                            new_len = len(new_entities[0][0].split())
                            difference = original_len - new_len
                            new_indices_head = [x for i, x in enumerate(boundaries_changed) if i < new_len]
                            new_indices_tail = [x-difference for x in bounds_other_entity]
                            if difference < 0:
                                last_num = new_indices_head[-1]
                                for i in range(abs(difference)):
                                    to_add = last_num + i + 1
                                    new_indices_head.append(to_add)
                        elif tag == 'E2':
                            boundaries_changed = boundaries['obj']
                            original_len = len(boundaries_changed)
                            new_len = len(new_entities[0][0].split())
                            difference = original_len - new_len
                            new_indices_tail = [x for i, x in enumerate(boundaries_changed) if i < new_len]
                            new_indices_head = [x-difference for x in bounds_other_entity]
                            if difference < 0:
                                last_num = new_indices_tail[-1]
                                for i in range(abs(difference)):
                                    to_add = last_num + i + 1
                                    new_indices_tail.append(to_add)
                        sentence_with_tags = [
                                ' '.join(tokens[:bounds_new_entity[0]]),
                                f"[{tag}] ",
                                f"{new_entities[0][0]}",
                                f"[\{tag}]",
                                ' '.join(tokens[bounds_new_entity[-1]+1:bounds_other_entity[0]]),
                                f"[{other_tag}]",
                                f"{other_ent}",
                                f"[\{other_tag}]",
                                ' '.join(tokens[bounds_other_entity[-1]+1:])
                                ]

                    else:
                        if tag == 'E1':
                            boundaries_changed = boundaries['subj']
                            new_len = len(new_entities[0][0].split())
                            new_indices_head = [x for i, x in enumerate(boundaries_changed) if i < new_len]
                            new_indices_tail = bounds_other_entity
                            original_len = len(boundaries_changed)
                            difference = original_len - new_len
                            if difference < 0:
                                last_num = new_indices_head[-1]
                                for i in range(abs(difference)):
                                    to_add = last_num + i +1
                                    new_indices_head.append(to_add)
                                    
                        elif tag == 'E2':
                            boundaries_changed = boundaries['obj']
                            new_len = len(new_entities[0][0].split())
                            new_indices_tail = [x for i, x in enumerate(boundaries_changed) if i < new_len]
                            new_indices_head = bounds_other_entity
                            original_len = len(boundaries_changed)
                            difference = original_len - new_len
                            if difference < 0:
                                last_num = new_indices_tail[-1]
                                for i in range(abs(difference)):
                                    to_add = last_num + i+1
                                    new_indices_tail.append(to_add)

                        sentence_with_tags = [
                                ' '.join(tokens[:bounds_other_entity[0]]),
                                f"[{other_tag}]",
                                f"{other_ent}",
                                f"[\{other_tag}]",
                                ' '.join(tokens[bounds_other_entity[-1]+1:bounds_new_entity[0]]),
                                f"[{tag}]",
                                f"{new_entities[0][0]}",
                                f"[\{tag}]",
                                ' '.join(tokens[bounds_new_entity[-1]+1:])
                                ]

                    sentence_with_tags = ' '.join(sentence_with_tags)
                    sentence_with_tags = sentence_with_tags.replace('\n','')

                    sentence_str = ' '.join(sentence_no_tags)
                    sentence_str = sentence_str.replace('\n', '')

                    new_line = '\t'.join([
                        sentence_str,
                        sentence_with_tags,
                        str(sentence_boundary),
                        relation_uri]
                        )     
                    sentence_dict['tokens'] = sentence_list
                    if len(head.split()) != len(new_indices_head):
                        if '-' in head:
                            head = ' '.join(re.split('([- ]+)', head))
                    if len(tail.split()) != len(new_indices_tail):
                        if '-' in tail:
                            tail = ' '.join(re.split('([- ]+)', tail))
                    sentence_dict['h'] = [head, re.findall(pattern,head_uri)[0], [new_indices_head]]
                    sentence_dict['t'] = [tail, re.findall(pattern,tail_uri)[0], [new_indices_tail]]
                    
                    fewrel_dict[rel].append(sentence_dict)
                with open(output_file, 'a') as f:
                    f.write(new_line+'\n')
    with open(output_file_json, 'w+') as g:
        json.dump(fewrel_dict, g)

