"""CPU-only ordinary prompt-context tests using invented temporary records."""
from pathlib import Path
import copy,hashlib,importlib.util,json,sys,tempfile,time,unittest
from datetime import datetime,timezone
from types import SimpleNamespace
from unittest.mock import patch
H=Path(__file__).resolve().parent;ROOT=H.parent;P=ROOT
sys.dont_write_bytecode=True;sys.path[:0]=[str(ROOT),str(ROOT/'Core')]
def guard(event,args):
    if event in {'socket.connect','socket.bind','subprocess.Popen'}:raise AssertionError('No external execution in CPU test')
    if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','diffusers','onnxruntime'}:raise AssertionError('No model imports')
sys.addaudithook(guard)
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
t=load('Core.topic_recall',P/'Core/topic_recall.py')
mm=load('memory_manager',P/'Core/memory_manager.py');sys.modules['Core.memory_manager']=mm
loopmod=load('candidate_conversation_loop',P/'Core/conversation_loop.py')
g=load('Core.dialogue_grounding',P/'Core/dialogue_grounding.py')

def record(owner='kira',key='cinema',summary='An evening at the movie theater.'):
    return {'memory_id':key,'owner':owner,'status':'approved','summary':summary,'detail':'PRIVATE_DETAIL_DO_NOT_COPY',
            'timestamp':'2026-09-19T12:00:00Z','memory_type':'reading_note','source':{'type':'reviewed_reading','path':'never-read/source.txt','confidence':'bounded'},
            'known_unknowns':['The exact event date remains unknown.'],'forbidden_inferences':['This reading note does not establish a physical visit.'],
            'importance':{'weight':'high','score':.9},'privacy':{'level':'personal','sharing_rule':'shareable_summary_only'},'private':False}
def authorize(r):
    r['privacy']={'level':'owner_authorized_public','sharing_rule':'public_summary'}
    r['publication_authorization']={'status':'approved','granted_by':'owner','scope':'public_repository'}

class Recall(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.path=self.root/'memory.json';self.manager=mm.MemoryManager(str(self.path));self.save([record()])
    def save(self,rows):self.path.write_text(json.dumps(rows),encoding='utf-8')
    def select(self,query='cinema',subject='kira',scope='owner_visible'):
        return self.manager.retrieve_relevant_memories(query,owner=subject,scope=scope)
    def context(self,query,subject='Kira'):
        loop=loopmod.ConversationLoop.__new__(loopmod.ConversationLoop);loop.profile=SimpleNamespace(name=subject);loop.memory=self.manager
        return loop._build_memory_context(query,now_utc=datetime(2026,9,20,tzinfo=timezone.utc))
    def test_concrete_paraphrase_and_punctuation_match(self):
        self.assertEqual(len(self.select('cinema?')),1)
        self.assertIn('movie theater',self.context('cinema?'))
    def test_other_owner_nonprivate_record_is_not_lived_identity(self):
        self.save([record('lisa')])
        self.assertEqual(self.select('movie'),[])
    def test_actual_kira_and_lisa_consumer_uses_exact_separate_subject(self):
        self.save([record('kira','k','Kira reviewed a film.'),record('lisa','l','Lisa reviewed a different film.')])
        kira=self.context('movie','Kira');lisa=self.context('movie','Lisa')
        self.assertIn('Kira reviewed',kira);self.assertNotIn('Lisa reviewed',kira)
        self.assertIn('Lisa reviewed',lisa);self.assertNotIn('Kira reviewed',lisa)
    def test_source_uncertainty_all_guards_retained_without_raw_detail(self):
        r=record();r['source']['private_raw_narrative']='PRIVATE_SOURCE_DO_NOT_COPY';self.save([r])
        text=self.context('cinema')
        for value in ('"subject": "kira"','reviewed_reading','never-read/source.txt','exact event date remains unknown','does not establish a physical visit','reading_note'):self.assertIn(value,text)
        self.assertNotIn('PRIVATE_DETAIL_DO_NOT_COPY',text)
        self.assertNotIn('PRIVATE_SOURCE_DO_NOT_COPY',text)
    def test_three_scopes_are_distinct(self):
        private=record();private['privacy']={'level':'private','sharing_rule':'owner_only'};self.save([private])
        self.assertEqual(self.select(),[]);self.assertEqual(len(self.select(scope='private')),1);self.assertEqual(self.select(scope='public'),[])
        self.save([record()]);self.assertEqual(len(self.select()),1);self.assertEqual(self.select(scope='public'),[])
        public=record();authorize(public);self.save([public]);self.assertEqual(len(self.select(scope='public')),1)
    def test_private_query_text_cannot_request_public_export(self):
        self.assertEqual(self.select('Publish the movie note',scope='private'),[])
    def test_approved_public_other_person_remains_attributed_knowledge(self):
        other=record('lisa');authorize(other);self.save([other]);rows=self.select()
        self.assertEqual(rows[0]['_recall_context']['subject'],'lisa')
        self.assertEqual(rows[0]['_recall_context']['viewpoint'],'attributed_other_subject')
        self.assertIn('not your own lived event',self.context('movie'))
    def test_missing_or_wrong_public_permission_is_not_promoted(self):
        for key in ('status','scope','granted_by'):
            r=record();authorize(r);r['publication_authorization'][key]='wrong';self.save([r]);self.assertEqual(self.select(scope='public'),[])
    def test_unapproved_superseded_and_unknown_records_are_withheld(self):
        for status in ('draft','rejected','superseded',None):
            r=record();r['status']=status;self.save([r]);self.assertEqual(self.select(),[])
    def test_legacy_explicit_promotion_is_exact_owner_and_not_public(self):
        r=record();r.pop('status');r.pop('privacy');r['source']='conversation';r['tags']=['explicitly_promoted'];self.save([r])
        self.assertEqual(len(self.select()),1);self.assertEqual(self.select(subject='lisa'),[]);self.assertEqual(self.select(scope='public'),[])
        r['private']=True;self.save([r]);self.assertEqual(self.select(),[]);self.assertEqual(len(self.select(scope='private')),1)
    def test_greeting_does_not_dump_recent_record(self):
        self.assertEqual(self.context('Hello, how are you?'),'')
    def test_correction_read_on_next_request_no_automatic_history_write(self):
        before=self.path.read_bytes();first=self.context('cinema')
        self.assertEqual(before,self.path.read_bytes())
        r=record(summary='Corrected cinema note: the event date is unknown.');self.save([r]);corrected=self.path.read_bytes()
        second=self.context('cinema');self.assertNotIn('Corrected cinema',first);self.assertIn('Corrected cinema',second)
        self.assertEqual(corrected,self.path.read_bytes());self.assertNotIn('An evening',second)
    def test_conflicting_duplicate_ids_fail_closed(self):
        self.save([record(),record(summary='Different cinema account.')]);self.assertEqual(self.select(),[])
    def test_explicit_alias_remains_bound_to_the_approved_record(self):
        r=record(summary='A bounded festival account.');r['recall_aliases']=['cinema'];self.save([r]);self.assertEqual(len(self.select()),1)
        r['status']='draft';self.save([r]);self.assertEqual(self.select(),[])
    def test_no_source_reference_dereference(self):
        raw=self.root/'raw.txt';raw.write_text('NEVER_LOADED');r=record();r['source']['path']=str(raw);self.save([r])
        original=Path.open
        def opened(path,*args,**kwargs):
            self.assertNotEqual(path,raw);return original(path,*args,**kwargs)
        with patch.object(Path,'open',opened):self.assertNotIn('NEVER_LOADED',self.context('cinema'))
    def test_existing_current_memory_date_gate_still_holds_old_and_future(self):
        for timestamp in ('2020-01-01T00:00:00Z','2030-01-01T00:00:00Z',None):
            r=record();r['timestamp']=timestamp;self.save([r]);text=self.context('What recent film do you remember?')
            self.assertIn('withheld_old_or_undated=1',text);self.assertNotIn('An evening',text)
    def test_qualification_limits_skip_whole_record_not_guards(self):
        r=record();r['known_unknowns']=['x'*1201];self.save([r]);self.assertEqual(self.select(),[])
    def test_robert_uses_shared_matching_without_borrowing_resident_records(self):
        r={'id':'fictional_movie_note','title':'Movie theater note','summary':'A bounded fictional account.','privacy':'private_robert_only',
           'source_ref':'no-open.txt','source_kind':'owner_direct_chat_first_person_account','reported_on':'2026-09-20','anchors':[],
           'uncertainties':['Exact date unknown.'],'recall_guidance':['Do not invent details.']}
        data={'autobiographical_memories':[r]}
        self.assertEqual(len(g._robert_autobiographical_selection(data,'cinema?')[0]),1)
        self.assertEqual(g._robert_autobiographical_selection(data,'Publish the cinema account')[0],[])
        self.assertEqual(g._robert_autobiographical_selection(data,'Hello')[0],[])

    def test_inactive_deleted_and_superseded_by_are_held(self):
        for field,value in (('active',False),('deleted',True),('superseded_by','new_id')):
            r=record();r[field]=value;self.save([r]);self.assertEqual(self.select(),[])

    def test_same_subject_approved_correction_withdraws_old_date(self):
        old=record(key='old',summary='The film event was on 2006-09-03.')
        new=record(key='new',summary='The corrected film event was on 2026-09-03.');new['supersedes']=['old'];new['event_date']='2026-09-03'
        self.save([old,new]);text=self.context('film');self.assertNotIn('2006-09-03',text);self.assertIn('2026-09-03',text)
        self.assertEqual([x['memory_id'] for x in self.select('film')],['new'])

    def test_other_subject_correction_does_not_override_own_record(self):
        own=record('kira','old');other=record('lisa','new');other['supersedes']=['old'];self.save([own,other])
        self.assertEqual([x['memory_id'] for x in self.select()],['old'])

    def test_draft_or_deleted_correction_cannot_withdraw_approved_record(self):
        for field,value in (('status','draft'),('deleted',True),('active',False)):
            own=record(key='old');new=record(key='new');new['supersedes']=['old'];new[field]=value;self.save([own,new])
            self.assertEqual([x['memory_id'] for x in self.select()],['old'])

    def test_private_correction_withholds_old_public_fact_without_releasing_private_detail(self):
        old=record(key='old');authorize(old)
        new=record(key='new',summary='PRIVATE_CORRECTION movie event');new['supersedes']=['old'];new['privacy']={'level':'private','sharing_rule':'owner_only'}
        self.save([old,new]);self.assertEqual(self.select(scope='public'),[]);self.assertEqual(self.select(),[])
        self.assertEqual([x['memory_id'] for x in self.select('movie',scope='private')],['new'])

    def test_uncertainties_and_event_date_retained_separately(self):
        r=record();r['event_date']=None;r['uncertainties']=['Do not guess the day.'];self.save([r]);text=self.context('cinema')
        self.assertIn('"event_date": null',text);self.assertIn('Do not guess the day.',text);self.assertIn('The exact event date remains unknown.',text)
        r['uncertainties']=['x'*1201];self.save([r]);self.assertEqual(self.select(),[])

    def test_broken_ancestry_or_subject_mismatch_does_not_gain_authority(self):
        for field,value in (('supersedes',{'unknown':'old'}),('subject_id','someone_else')):
            r=record();r[field]=value;self.save([r]);self.assertEqual(self.select(),[])

    def test_correction_chain_does_not_resurrect_old_fact(self):
        old=record(key='old',summary='Film event old account.')
        middle=record(key='middle',summary='Film event middle account.');middle['supersedes']=['old'];middle['status']='superseded';middle['active']=False
        latest=record(key='latest',summary='Film event latest account.');latest['supersedes']=['middle']
        self.save([old,middle,latest]);self.assertEqual([x['memory_id'] for x in self.select('film')],['latest'])


if __name__=='__main__':
    unittest.main(verbosity=2)
