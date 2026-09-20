"""CPU prompt construction only; no model, server, voice, or real-data writes."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,sys,tempfile,time,unittest
from unittest.mock import patch
H=Path(__file__).resolve().parent;ROOT=H.parent
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT))
def no_runtime(event,args):
    if event in {'socket.connect','socket.bind','subprocess.Popen'}:
        raise RuntimeError('No network/process calls in CPU grounding test')
    if event=='import' and str(args[0]).split('.')[0] in {'torch','diffusers','transformers','onnxruntime'}:
        raise RuntimeError('No model imports in grounding test')
sys.addaudithook(no_runtime)
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
g=load('Core.dialogue_grounding',ROOT/'Core/dialogue_grounding.py')
chat=load('twin_grounding_live_chat_candidate',ROOT/'tools/temporary_ai_live_chat.py')
MEMORY='Data/identity/robert_mcmurrer/robert_source_memory_20260715.json'
ROBERT='robert_mcmurrer_presence_ai'
def pin(p):return {'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def record(key,title,summary):
    return {'id':key,'title':title,'source_ref':'sources/raw-private-never-read.txt','source_kind':'owner_direct_chat_first_person_account',
            'reported_on':'2026-09-20','privacy':'private_robert_only','event_date':None,'summary':summary,
            'anchors':['A supplied remembered scene.'],'uncertainties':['The exact date remains unknown.'],
            'recall_guidance':['Attribute this to the owner account; never invent confirmation.']}
def fixture():
    mira=record('mira_fern_meeting','Mira Fern at Greenhouse','MIRA_SUMMARY')
    clock=record('clockwork_lantern','Clockwork car and Lantern figure','CLOCK_SUMMARY')
    clock['source_kind']='owner_supplied_screenshot_of_first_person_post';clock['enriches_existing']={'record':'earlier_timeline'}
    return {'canonical_identity':{'private':'UNRELATED_IDENTITY'},'hard_false_memory_firewall':['UNRELATED_FIREWALL'],
            'timeline':[{'era':'unrelated','anchors':['UNRELATED_TRAUMA','LATER_ANCHOR']}],
            'autobiographical_memories':[mira,clock]}
class Grounding(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='twin-grounding-cpu-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.file=self.root/MEMORY;self.file.parent.mkdir(parents=True);self.data=fixture();self.save()
        self.candidate={'candidate_id':ROBERT,'profile':{'display_name':'Synthetic Robert','ai_type':'synthetic_variant'}}
    def save(self):self.file.write_text(json.dumps(self.data),encoding='utf-8')
    def prompt(self,query,candidate=None):
        # These existing generic project-document helpers are irrelevant to this
        # route and can refresh external graphs; no such action is permitted here.
        with patch.object(chat,'PROJECT_ROOT',self.root),patch.object(chat,'candidate_reference_context',return_value=''),patch.object(chat,'topic_project_doc_context',return_value=''):
            return chat.build_system_prompt(candidate or self.candidate,user_message=query)
    def test_actual_prompt_selects_mira_with_provenance_uncertainty_and_no_unrelated_history(self):
        text=self.prompt('Tell me about Mira Fern at Greenhouse.')
        for item in ('MIRA_SUMMARY','owner_direct_chat_first_person_account','The exact date remains unknown.','2026-09-20','"event_date": null'):
            self.assertIn(item,text)
        for item in ('CLOCK_SUMMARY','UNRELATED_TRAUMA','UNRELATED_IDENTITY','UNRELATED_FIREWALL'):
            self.assertNotIn(item,text)
        self.assertIn("not the synthetic Robert's own lived history",text)
    def test_clockwork_keeps_enrichment_and_distinct_source_kind(self):
        text=self.prompt('Tell me about the Clockwork car and Lantern figure.')
        self.assertIn('CLOCK_SUMMARY',text);self.assertIn('owner_supplied_screenshot_of_first_person_post',text)
        self.assertIn('"enriches_existing_record": true',text);self.assertNotIn('MIRA_SUMMARY',text)
    def test_greeting_uses_current_owner_message_not_shell_scaffolding(self):
        text=self.prompt('Context mentions Mira Fern and Clockwork.\n\nRobert says: Hello, how are you?')
        for item in ('MIRA_SUMMARY','CLOCK_SUMMARY','UNRELATED_TRAUMA'):self.assertNotIn(item,text)
    def test_reads_fresh_source_on_next_prompt(self):
        first=self.prompt('Mira Fern');_,before=g.load_robert_private_grounding(self.root,query='Mira Fern')
        self.data['autobiographical_memories'][0]['summary']='UPDATED_MIRA_SUMMARY';self.save()
        second=self.prompt('Mira Fern');_,after=g.load_robert_private_grounding(self.root,query='Mira Fern')
        self.assertNotIn('UPDATED_MIRA_SUMMARY',first);self.assertIn('UPDATED_MIRA_SUMMARY',second)
        self.assertNotEqual(before['sha256'],after['sha256'])
    def test_exact_candidate_only(self):
        for candidate_id in ('kira','lisa','other','Robert','robert_mcmurrer_presence_ai_extra'):
            with self.subTest(candidate=candidate_id),patch.object(g,'load_robert_private_grounding',side_effect=AssertionError('Cross-role read')):
                text=self.prompt('Mira Fern',{'candidate_id':candidate_id,'profile':{'display_name':'Other'}})
                self.assertNotIn('MIRA_SUMMARY',text)
    def test_source_ref_is_only_provenance_not_a_file_read(self):
        raw=self.root/'never-read.txt';raw.write_text('RAW_NARRATIVE_SENTINEL',encoding='utf-8')
        self.data['autobiographical_memories'][0]['source_ref']=str(raw);self.save()
        original=Path.read_bytes;reads=[]
        def tracked(path):
            reads.append(path);self.assertNotEqual(path,raw);return original(path)
        with patch.object(Path,'read_bytes',tracked):text,audit=g.load_robert_private_grounding(self.root,query='Mira Fern')
        self.assertEqual(reads,[self.file]);self.assertNotIn('RAW_NARRATIVE_SENTINEL',text);self.assertFalse(audit['raw_source_files_read'])
    def test_public_marketing_request_does_not_receive_private_memories(self):
        for query in ('Write public marketing copy about Mira Fern.','Publish my Clockwork story online.'):
            with self.subTest(query=query):
                text=self.prompt(query);self.assertNotIn('MIRA_SUMMARY',text);self.assertNotIn('CLOCK_SUMMARY',text)
    def test_invalid_privacy_source_and_qualifications_are_not_admitted(self):
        for field,value in (('privacy','public'),('source_kind','assistant_guess'),('uncertainties','missing list')):
            with self.subTest(field=field):
                self.data=fixture();self.data['autobiographical_memories'][0][field]=value;self.save()
                text,audit=g.load_robert_private_grounding(self.root,query='Mira Fern')
                self.assertEqual(audit['autobiographical_selected_ids'],[]);self.assertNotIn('MIRA_SUMMARY',text)
    def test_legacy_no_query_api_keeps_existing_fields_and_adds_bounded_records(self):
        text,audit=g.load_robert_private_grounding(self.root)
        for item in ('UNRELATED_IDENTITY','UNRELATED_FIREWALL','UNRELATED_TRAUMA','MIRA_SUMMARY','CLOCK_SUMMARY'):self.assertIn(item,text)
        self.assertNotIn('LATER_ANCHOR',text);self.assertFalse(audit['query_scoped'])
    def test_record_budget_never_drops_qualifications_to_fit(self):
        self.data['autobiographical_memories'][0]['summary']='x'*3001;self.save()
        text,audit=g.load_robert_private_grounding(self.root,query='Mira Fern')
        self.assertEqual(audit['autobiographical_selected_ids'],[])
        self.assertNotIn('"id": "mira_fern_meeting"',text)
    def authorize(self, item):
        item['privacy']='owner_authorized_public'
        item['publication_authorization']={'status':'approved','granted_by':'owner','scope':'public_repository'}
    def test_owner_authorized_record_available_for_public_repository_request(self):
        self.authorize(self.data['autobiographical_memories'][0]);self.save()
        text=self.prompt('Use the Mira Fern recollection in the public repository.')
        self.assertIn('MIRA_SUMMARY',text);self.assertIn('"privacy": "owner_authorized_public"',text)
        self.assertIn('"publication_authorization":',text)
        self.assertNotIn('This is private Robert-source grounding',text)
    def test_public_label_requires_each_explicit_authorization_field(self):
        for field,value in (('status','pending'),('granted_by','assistant'),('scope','private_review')):
            with self.subTest(field=field):
                self.data=fixture();self.authorize(self.data['autobiographical_memories'][0])
                self.data['autobiographical_memories'][0]['publication_authorization'][field]=value;self.save()
                text,audit=g.load_robert_private_grounding(self.root,query='Mira Fern')
                self.assertNotIn('MIRA_SUMMARY',text);self.assertEqual(audit['autobiographical_selected_ids'],[])
        self.data['autobiographical_memories'][0].pop('publication_authorization');self.save()
        self.assertNotIn('MIRA_SUMMARY',self.prompt('Mira Fern'))
    def test_mixed_records_keep_private_filter_without_hiding_approved_public_record(self):
        self.authorize(self.data['autobiographical_memories'][0]);self.save()
        text=self.prompt('For the public repository discuss Mira Fern and Clockwork.')
        self.assertIn('MIRA_SUMMARY',text);self.assertNotIn('CLOCK_SUMMARY',text)
        self.assertIn('CLOCK_SUMMARY',self.prompt('Clockwork'))
    def test_public_permission_is_per_record_not_inherited_from_top_level(self):
        self.data['publication_authorization']={'status':'approved','granted_by':'owner','scope':'public_repository'}
        self.data['autobiographical_memories'][0]['privacy']='owner_authorized_public';self.save()
        self.assertNotIn('MIRA_SUMMARY',self.prompt('Public Mira Fern recollection'))
    def test_private_label_cannot_be_overridden_by_attached_public_permission(self):
        self.data['autobiographical_memories'][0]['publication_authorization']={'status':'approved','granted_by':'owner','scope':'public_repository'};self.save()
        self.assertNotIn('MIRA_SUMMARY',self.prompt('Public Mira Fern recollection'))
        self.assertIn('MIRA_SUMMARY',self.prompt('Mira Fern'))
    def test_authorized_public_records_still_default_to_exact_robert_role(self):
        self.authorize(self.data['autobiographical_memories'][0]);self.save()
        with patch.object(g,'load_robert_private_grounding',side_effect=AssertionError('Cross-role read')):
            text=self.prompt('Public Mira Fern recollection',{'candidate_id':'other','profile':{'display_name':'Other'}})
        self.assertNotIn('MIRA_SUMMARY',text)
if __name__=='__main__':
    unittest.main(verbosity=2)
