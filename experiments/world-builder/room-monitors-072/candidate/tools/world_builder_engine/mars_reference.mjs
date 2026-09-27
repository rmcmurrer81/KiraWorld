// Small sourced reference dataset. No network calls or claim of current telemetry.
const deepFreeze=o=>{if(o&&typeof o==='object'){Object.values(o).forEach(deepFreeze);Object.freeze(o);}return o;};
export const MARS_REFERENCE=deepFreeze({
 contract:'sourced_mars_reference_v1', checked_local_date:'2026-09-26', live:false,
 sources:{
  nasa_facts:{title:'NASA Mars Facts',url:'https://science.nasa.gov/mars/facts/'},
  nasa_sheet:{title:'NASA Mars Fact Sheet',url:'https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html'},
  meda_2021:{title:'NASA/JPL First Weather Report from Jezero',published:'2021-04-06',url:'https://www.jpl.nasa.gov/news/nasas-first-weather-report-from-jezero-crater-on-mars/'}
 },
 facts:[
  {id:'gravity',label:'Mean surface gravity',value:3.73,unit:'m/s²',source:'nasa_sheet'},
  {id:'solar_day',label:'Solar day',value:24.6597,unit:'Earth hours',source:'nasa_sheet'},
  {id:'year',label:'Year',value:687,unit:'Earth days',source:'nasa_facts',approximate:true},
  {id:'co2',label:'Atmosphere CO₂',value:95.1,unit:'% by volume',source:'nasa_sheet',approximate:true},
  {id:'pressure_reference',label:'Pressure at mean radius',value:636,unit:'Pa',source:'nasa_sheet',note:'Reference value; varies by season and elevation. Converted from6.36mbar.'}
 ],
 historical_observations:[
  {id:'meda_first_pressure',place:'Jezero crater',instrument:'Perseverance / MEDA',observed_date:'2021-02-19',source:'meda_2021',values:[{label:'Pressure',value:718,unit:'Pa'}]},
  {id:'meda_sols_43_44',place:'Jezero crater',instrument:'Perseverance / MEDA',observed_date:'2021-04-03 to2021-04-04',sols:'43–44',source:'meda_2021',values:[{label:'High',value:-22,unit:'°C'},{label:'Low',value:-83,unit:'°C'},{label:'Wind gust',value:10,unit:'m/s',approximate:true}]}
 ]
});

export function referencePanel(kind){
 if(kind==='planet')return deepFreeze({title:'MARS / PLANET REFERENCE',badge:'NASA REFERENCE · NOT LOCAL WEATHER',
  rows:MARS_REFERENCE.facts.filter(x=>['gravity','solar_day','year','co2'].includes(x.id)),sourceIds:['nasa_facts','nasa_sheet'],live:false});
 if(kind==='weather'){
  const observation=MARS_REFERENCE.historical_observations.find(x=>x.id==='meda_sols_43_44');
  return deepFreeze({title:'JEZERO / ARCHIVED WEATHER',badge:'MEASURED 03–04 APR2021 · NOT LIVE',
   subtitle:'Perseverance / MEDA · Sols43–44',rows:observation.values,sourceIds:['meda_2021'],observation,live:false});
 }
 throw new TypeError('Unknown sourced Mars panel');
}
