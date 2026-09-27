// Deliberately artificial component input, not a source package or loader proof.
// Dimensions and names here do not describe an owner's saved world.
export function artificialPlan(axis='x',normalSign=1){
 const W=1.2,H=2.2,portalId='demonstration_portal',origin=[0,0,2];
 const hingeLocal=[-W/2-.075,0,.12],n=axis==='x'?0:2,t=n===0?2:0;
 const hinge=[...origin];hinge[t]+=hingeLocal[0];hinge[n]+=normalSign*hingeLocal[2];
 const center=.035+(W+.08)/2,fixed=[],moving=[];
 const box=(list,name,center,size)=>list.push({id:'hatch_'+portalId+'_'+name,shape:'box',center,size});
 fixed.push({id:'hatch_'+portalId+'_continuous_gasket',shape:'ring',center:[0,0,.08375],size:[W+.046,H+.039,.0075],
  outer:{width:W+.046,bottom:-.016,top:H+.023,radius:.203},inner:{width:W+.018,bottom:0,top:H+.009,radius:.189}});
 moving.push({id:'hatch_'+portalId+'_reinforced_leaf',shape:'solid',center:[center,(H+.04)/2,0],size:[W+.08,H+.04,.065]});
 for(const y of [H*.25,H*.50,H*.75]){
  const suffix='1_'+Math.round(y*1000),edge=center+W/2+.014;
  box(moving,'retracted_dog_'+suffix,[edge,y,.072],[.020,.039,.021]);
  box(moving,'dog_housing_'+suffix,[edge-.018,y,.071],[.047,.088,.043]);
  box(fixed,'keeper_'+suffix,[W/2+.080,y,.192],[.042,.084,.040]);
  box(fixed,'keeper_support_'+suffix,[W/2+.080,y,.132],[.043,.102,.122]);
 }
 for(const face of [-1,1])moving.push({id:'hatch_'+portalId+'_control_wheel_'+face,shape:'wheel',center:[center,H*.53,face*.079],radius:.103,tube:.009});
 return {contract:'authored_pressure_hatch_geometry_v1',portalId,axis,normalSign,origin,hinge,hingeLocal,
  openAngle:normalSign*(axis==='x'?1:-1)*Math.PI/2,fixed,moving,
  capabilities:{latchState:'static_retracted',latchSimulation:false}};
}
