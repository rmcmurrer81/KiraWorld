"""Small explicit command grammar for the World Builder chat front door.

Only direct new research/creation requests reach job submission. This is not a
general conversation model or an editor: unsupported requests remain explicit.
"""
from __future__ import annotations
import re

MESSAGES={
    'negative':'No new research or generation was started. Existing jobs and saved worlds were preserved. This message does not cancel a worker that is already running.',
    'deferred':'No job was started. Send a direct build or research request when you want work to begin.',
    'planning':'No job was started. Interactive planning is not implemented in this chat yet. A useful brief includes the setting, rooms, approximate size and purpose; send it with Build or Research when you are ready.',
    'edit_unsupported':'Changing existing rooms, doors or furniture through chat is not implemented yet. Your selected world was preserved and no replacement research job was created.',
    'help':'You can ask me to build an original world or research a place, resume research, show status, open the latest saved world, open the current preview, or export a 3D package. Existing-world edits and detailed conversational answers are not implemented yet.',
    'unrecognized':'No job was started. Use a direct request such as Build a Mars base, Research the Louvre courtyard, Show status, Open latest saved world, Open current preview, or Export this world. Existing-world edits are not implemented yet.',
}

def _unquoted(text: str) -> str:
    # A quote may contain a command as data. Preserve the surrounding unquoted
    # request, including a direct Build command with a quoted premise/title.
    return re.sub(r'"[^"\n]*"|“[^”\n]*”|(?<!\w)\'[^\'\n]*\'(?!\w)',lambda m:' '*len(m.group()),text)

def _post_command_delay(text: str) -> bool:
    # These are instructions about when work may begin, after quoted data has
    # been removed. Ordinary design constraints ("with no weapons" or "do not
    # build a laboratory") must not become execution delays by themselves.
    return any(re.search(pattern, text) for pattern in (
        r'(?:[,;.!?]\s*|\b(?:but|and|then)\s+)(?:please\s+)?(?:wait|hold off)\b',
        r'\b(?:do not|don\'t)\s+(?:build|create|make|research|generate)\b[^,;.!?]{0,120}\b(?:yet|now|until)\b',
        r'\b(?:after|once|when|until)\s+(?:i|we|you)\s+(?:(?:get|come|arrive)\s+(?:back\s+)?home|(?:get|come)\s+back|return)\b',
        r'\bnot\s+(?:right\s+)?now\s*$',
    ))

def classify_world_chat(message: str) -> dict:
    if not isinstance(message,str) or not message.strip():return {'action':'empty'}
    text=_unquoted(message.replace('’',"'")).strip().lower()
    text=re.sub(r'\s+',' ',text).rstrip('.!?').strip()
    # Polite requests are commands; questions about how to do something are not.
    text=re.sub(r'^(?:please\s+)?(?:can you|could you|would you|i want you to|i would like you to|i\'d like you to)\s+','',text)
    text=re.sub(r'^please\s+','',text)
    if not text:return {'action':'help','message':MESSAGES['help']}
    if re.match(r"^(?:do not|don't|never|not now|stop|cancel|hold off|wait)\b",text):
        return {'action':'negative','message':MESSAGES['negative']}
    if _post_command_delay(text) or re.search(r'\b(?:if|until|after|once|when)\s+(?:i|we|you)\b.{0,60}\b(?:approve|confirm|say|agree|ask|ready)\b',text) or re.search(r'\b(?:if|until|after|once|when)\s+(?:(?:my|our|your)\s+)?(?:approved|approval|confirmed|confirmation|ready)\b',text) or re.search(r'\b(?:later|tomorrow|next week)\s*$',text) or re.search(r"\b(?:do not|don't)\s+(?:start|begin)\b|\b(?:do not|don't)\s+(?:build|create|research|generate)\s+(?:it|this|that|anything|yet|now|until)\b",text):
        return {'action':'deferred','message':MESSAGES['deferred']}
    if re.match(r'^(?:plan|discuss|brainstorm|consider|think about|describe|outline|sketch out|before\s+(?:building|creating|researching))\b',text):
        return {'action':'planning','message':MESSAGES['planning']}
    if re.fullmatch(r'(?:show\s+(?:me\s+)?(?:the\s+)?)?(?:status|progress)(?:\s+(?:of|for)\s+(?:my|the|this|current|selected)\s+(?:world|layout|project|research))?',text) or re.fullmatch(r"(?:what(?:'s| is)\s+(?:the\s+)?(?:status|progress)|how is (?:my |the |this |current |selected )?(?:world|layout|project|research)(?: coming| going)?)",text):
        return {'action':'status'}
    if re.fullmatch(r'(?:open|reopen|load)\s+(?:(?:my|the)\s+)?(?:latest|last|most recent)\s+(?:saved\s+)?(?:world|layout|project|research)',text):
        return {'action':'open_latest'}
    if re.fullmatch(r'(?:open|show|view)\s+(?:(?:me|my|the|this|current|selected)\s+){0,2}(?:(?:world|layout)\s+)?preview',text):
        return {'action':'preview'}
    if re.fullmatch(r'export\s+(?:(?:my|the|this|current|selected)\s+){0,2}(?:world|layout|project)(?:\s+(?:as|to)\s+(?:a\s+)?3d\s+package)?|export\s+(?:(?:a|the)\s+)?3d\s+package',text):
        return {'action':'export'}
    if re.fullmatch(r'(?:resume|retry|continue)(?:\s+(?:(?:my|the|this|current|selected)\s+)?(?:research|world|layout|project))?',text):
        return {'action':'resume','submit_prompt':'resume'}
    existing_target=re.match(r'^(?:build|create|make|design|invent)\b',text) and re.search(r'\b(?:in|inside|within|into|to|onto|for)\s+(?:(?:the|my|our|this|current|selected|existing|saved)\s+){1,3}(?:[a-z]+\s+){0,2}(?:world|habitat|base|layout|room|project)\b',text)
    if existing_target:
        return {'action':'edit_unsupported','message':MESSAGES['edit_unsupported']}
    if re.match(r'^(?:change|edit|modify|widen|narrow|move|remove|delete|replace|add|resize|turn)\b',text) or (re.match(r'make\s+(?:the|my|this|current|selected|existing|our)\b',text) and re.search(r'\b(?:current|selected|existing|wider|narrower|bigger|smaller|larger|open|closed|into|taller|shorter|room|door|galley|laboratory|lab|airlock|bunk|corridor|sink|window)\b',text)):
        return {'action':'edit_unsupported','message':MESSAGES['edit_unsupported']}
    if re.match(r'^(?:how|what|why|where|when|which|who|is|are|does|do|can|could|would|tell me|help)\b',text):
        return {'action':'help','message':MESSAGES['help']}
    if re.search(r'(?:[;.!?]\s*|\b(?:and then|then|and|or)\s+)(?:open|export|load|reopen|resume|delete|change|modify)\b',text):
        return {'action':'unrecognized','message':'No job was started. Send one action at a time so the selected world and requested action are clear.'}
    quoted_target=re.fullmatch(r'(?:build|create|make|design|invent|research)',text) and re.search(r'["“][^"”\n]*\S[^"”\n]*["”]',message)
    if re.match(r'^(?:build|create|make|design|invent|research)\s+\S',text) or quoted_target:
        # The existing parser remains responsible for original vs real-place
        # eligibility. Preserve the owner's full prompt and quoted data.
        return {'action':'research','submit_prompt':message}
    return {'action':'unrecognized','message':MESSAGES['unrecognized']}
