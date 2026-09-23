"""CPU contact sheet from embedded authored GLB PNGs, never from screenshots."""
from pathlib import Path
import hashlib,io,json,math,struct,textwrap
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
PACKAGE=HERE/'actual-mars-005'
raw=(PACKAGE/'scene.glb').read_bytes();jlen=struct.unpack_from('<I',raw,12)[0]
g=json.loads(raw[20:20+jlen]);bin_start=20+jlen+8
nodes=g['nodes'];parents={c:i for i,n in enumerate(nodes) for c in n.get('children',[])}
semantic={n['id']:n for n in json.loads((PACKAGE/'scene.json').read_bytes())['nodes']}
def ancestors(i):
    found=[]
    while True:
        found.append(nodes[i]);i=parents.get(i)
        if i is None:return found
def image_row(i):
    node=nodes[i]
    if 'mesh' not in node:return None
    mat=g['materials'][g['meshes'][node['mesh']]['primitives'][0]['material']]
    tex=mat.get('pbrMetallicRoughness',{}).get('baseColorTexture')
    if not tex:return None
    image_index=g['textures'][tex['index']]['source'];image=g['images'][image_index];view=g['bufferViews'][image['bufferView']]
    offset=bin_start+view.get('byteOffset',0);png=raw[offset:offset+view['byteLength']]
    return {'node_index':i,'object_id':node.get('extras',{}).get('export_id'),'image_index':image_index,'png_sha256':hashlib.sha256(png).hexdigest(),'png':png}
selected=[];seen=set()
for i,n in enumerate(nodes):
    row=image_row(i)
    if not row:continue
    chain=ancestors(i);owner=next((x.get('extras',{}).get('metadata_node_id') for x in chain if x.get('extras',{}).get('metadata_node_id')),None)
    name=n.get('name','');role=None
    if owner and owner.startswith('node:plaque_'):role=owner
    elif name=='equipment_vestibule_floor_mesh':role='floor/equipment_vestibule'
    elif name=='airlock_floor_mesh':role='grate/airlock'
    elif owner and semantic[owner]['kind']=='operations_console':role='screen/operations_console'
    elif not owner and 'map' not in seen and len(selected)>1:role='wall_panel'
    if role and role not in seen:
        seen.add(role);row['label']=role;row['owner_node_id']=owner;selected.append(row)
        if role=='wall_panel':seen.add('map')
assert sum(r['label'].startswith('node:plaque_') for r in selected)==7
assert any(r['label'].startswith('screen/') for r in selected)
cols=3;cell_w=440;cell_h=340
sheet=Image.new('RGB',(cols*cell_w,80+math.ceil(len(selected)/cols)*cell_h),'#172126');draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',17);title=ImageFont.truetype('C:/Windows/Fonts/seguisb.ttf',24)
draw.text((18,10),'036: authored embedded textures and signs',font=title,fill='white')
draw.text((18,44),'CPU extraction; UV-upright display (vertical flip only). No visual realism approval.',font=font,fill='#aec4c8')
for idx,row in enumerate(selected):
    x=(idx%cols)*cell_w;y=80+(idx//cols)*cell_h
    # GLB's PNG has Canvas flipY baked in by Three. Flip only for readable cards.
    image=Image.open(io.BytesIO(row['png'])).convert('RGB').transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    image.thumbnail((cell_w-30,235));sheet.paste(image,(x+(cell_w-image.width)//2,y+8))
    label='\n'.join(textwrap.wrap(row['label'],39));draw.multiline_text((x+12,y+249),label,font=font,fill='white',spacing=3)
    draw.text((x+12,y+299),f"image {row['image_index']} | {row['object_id']}",font=font,fill='#aec4c8')
dest=HERE/'TEXTURE-CONTACT-SHEET.png';sheet.save(dest)
receipt={'status':'CPU_EMBEDDED_TEXTURE_CONTACT_SHEET','source_glb_sha256':hashlib.sha256(raw).hexdigest(),'contact_sheet_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'display_transform':'vertical flip to display Canvas-authored UV orientation; no color edit','textures':[{k:v for k,v in row.items() if k!='png'} for row in selected]}
(HERE/'TEXTURE-CONTACT-SHEET.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'cards':len(selected),'path':str(dest),'sha256':receipt['contact_sheet_sha256']}))
